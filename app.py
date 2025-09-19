import os
import uuid
import sqlite3
from flask import (
    Flask, g, render_template, request, redirect, url_for, session, flash, send_from_directory
)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from functools import wraps

app = Flask(__name__)

app.secret_key = os.environ.get('SECRET_KEY', 'change_this_secret_key')
DATABASE = os.environ.get('DATABASE_URL', 'journal.db')

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'txt'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Helpers

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def query_db(query, args=(), one=False):
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv

def execute_db(query, args=()):
    db = get_db()
    cur = db.cursor()
    cur.execute(query, args)
    db.commit()
    return cur.lastrowid

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Por favor, faça login para acessar esta página.')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Routes

@app.route('/')
def index():
    current_issue = query_db(
        "SELECT * FROM issues WHERE iscurrent = 1 AND status = 'published' LIMIT 1",
        one=True
    )
    recent_articles = query_db(
        """SELECT s.id, s.title, s.abstract, s.publisheddate, u.firstname, u.lastname, sec.title as section_title
           FROM submissions s
           JOIN users u ON s.authorid = u.id
           LEFT JOIN sections sec ON s.sectionid = sec.id
           WHERE s.status = 'published'
           ORDER BY s.publisheddate DESC
           LIMIT 10"""
    )
    return render_template('index.html', current_issue=current_issue, recent_articles=recent_articles)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = query_db('SELECT * FROM users WHERE email = ?', [email], one=True)
        if user and check_password_hash(user['passwordhash'], password):
            if user['status'] != 'active':
                flash('Conta inativa. Entre em contato com o administrador.')
                return render_template('login.html')
            session['user_id'] = user['id']
            session['user_role'] = user['role']
            session['user_name'] = f"{user['firstname']} {user['lastname']}"
            return redirect(url_for('dashboard'))
        flash('Email ou senha inválidos.')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        firstname = request.form['firstname']
        lastname = request.form['lastname']
        password = request.form['password']
        confirm_password = request.form['confirmpassword']
        affiliation = request.form.get('affiliation', '')
        country = request.form.get('country', '')

        if password != confirm_password:
            flash('As senhas não coincidem.')
            return render_template('register.html')

        if len(password) < 6:
            flash('A senha deve ter pelo menos 6 caracteres.')
            return render_template('register.html')

        existing_count = query_db('SELECT COUNT(*) as count FROM users WHERE email = ?', [email], one=True)['count']

        if existing_count > 0:
            flash('Este email já está cadastrado.')
            return render_template('register.html')

        password_hash = generate_password_hash(password)
        execute_db(
            'INSERT INTO users (email, passwordhash, firstname, lastname, role, affiliation, country, status, emailverified, createdat, updatedat) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, datetime("now"), datetime("now"))',
            (email, password_hash, firstname, lastname, 'author', affiliation, country, 'active', 1)
        )
        flash('Cadastro realizado com sucesso. Faça login.')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/dashboard')
@login_required
def dashboard():
    user_id = session['user_id']
    user_role = session.get('user_role', 'author')

    user = query_db('SELECT * FROM users WHERE id = ?', [user_id], one=True)

    if user_role == 'author':
        submissions = query_db(
            'SELECT s.*, sec.title AS section_title FROM submissions s LEFT JOIN sections sec ON s.sectionid = sec.id WHERE s.authorid = ? ORDER BY s.submissiondate DESC',
            [user_id]
        )
    else:
        submissions = query_db(
            'SELECT s.*, sec.title AS section_title FROM submissions s LEFT JOIN sections sec ON s.sectionid = sec.id ORDER BY s.submissiondate DESC LIMIT 20'
        )

    return render_template('dashboard.html', user=user, submissions=submissions)

@app.route('/submit', methods=['GET', 'POST'])
@login_required
def submit():
    if request.method == 'POST':
        title = request.form['title']
        abstract = request.form['abstract']
        keywords = request.form['keywords']
        language = request.form['language']
        section_id = request.form.get('sectionid')
        user_id = session['user_id']

        # Upload de arquivo
        file = request.files.get('file')
        file_id = None
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            unique_name = str(uuid.uuid4()) + "_" + filename
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_name)
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
            file.save(filepath)
            file_id = execute_db(
                "INSERT INTO files (filename, filepath, mimetype, uploaderid, createdat) VALUES (?, ?, ?, ?, datetime('now'))",
                (filename, filepath, file.mimetype, user_id)
            )

        submission_id = execute_db(
            "INSERT INTO submissions (title, abstract, keywords, language, sectionid, authorid, status, submissionstage, fileid, submissiondate) VALUES (?, ?, ?, ?, ?, ?, 'submitted', 'submission', ?, datetime('now'))",
            (title, abstract, keywords, language, section_id, user_id, file_id)
        )
        
        # Inserir coautores
        coauthors_raw = request.form.get('coauthors', '')
        coauthors_emails = [email.strip() for email in coauthors_raw.split(',') if email.strip()]
        execute_db('DELETE FROM coauthors WHERE submissionid = ?', (submission_id,))
        for email in coauthors_emails:
            user_coauthor = query_db('SELECT id FROM users WHERE email = ?', (email,), one=True)
            user_id_coauthor = user_coauthor['id'] if user_coauthor else None
            execute_db('INSERT INTO coauthors (submissionid, userid, email) VALUES (?, ?, ?)', (submission_id, user_id_coauthor, email))

        flash('Submissão realizada com sucesso.')
        return redirect(url_for('dashboard'))

    sections = query_db('SELECT id, title FROM sections WHERE isactive = 1 ORDER BY sortorder')
    return render_template('submit.html', sections=sections, submission=None)

@app.route('/edit_submission/<int:submission_id>', methods=['GET', 'POST'])
@login_required
def edit_submission(submission_id):
    user_id = session['user_id']
    submission = query_db('SELECT * FROM submissions WHERE id = ?', [submission_id], one=True)

    if not submission or submission['authorid'] != user_id:
        flash('Submissão não encontrada ou acesso não autorizado.')
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        title = request.form['title']
        abstract = request.form['abstract']
        keywords = request.form['keywords']
        language = request.form['language']
        section_id = request.form.get('sectionid')

        execute_db(
            """
            UPDATE submissions
            SET title=?, abstract=?, keywords=?, language=?, sectionid=?, updatedat=datetime('now')
            WHERE id=?
            """, (title, abstract, keywords, language, section_id, submission_id)
        )

        # Atualizar coautores
        coauthors_raw = request.form.get('coauthors', '')
        coauthors_emails = [email.strip() for email in coauthors_raw.split(',') if email.strip()]
        execute_db('DELETE FROM coauthors WHERE submissionid = ?', (submission_id,))
        for email in coauthors_emails:
            user_coauthor = query_db('SELECT id FROM users WHERE email = ?', (email,), one=True)
            user_id_coauthor = user_coauthor['id'] if user_coauthor else None
            execute_db('INSERT INTO coauthors (submissionid, userid, email) VALUES (?, ?, ?)', (submission_id, user_id_coauthor, email))

        flash('Submissão atualizada com sucesso.')
        return redirect(url_for('dashboard'))

    sections = query_db('SELECT id, title FROM sections WHERE isactive = 1 ORDER BY sortorder')
    coauthors = query_db('SELECT email FROM coauthors WHERE submissionid = ?', (submission_id,))
    coauthors_str = ', '.join([c['email'] for c in coauthors])
    return render_template('submit.html', sections=sections, submission=submission, coauthors=coauthors_str)

@app.route('/submissions')
@login_required
def submissions():
    user_id = session['user_id']
    user_role = session.get('user_role', 'author')

    if user_role == 'author':
        subs = query_db(
            'SELECT s.*, sec.title AS section_title FROM submissions s LEFT JOIN sections sec ON s.sectionid = sec.id WHERE s.authorid = ? ORDER BY s.submissiondate DESC',
            [user_id]
        )
    else:
        subs = query_db(
            'SELECT s.*, sec.title AS section_title FROM submissions s LEFT JOIN sections sec ON s.sectionid = sec.id ORDER BY s.submissiondate DESC LIMIT 50'
        )

    return render_template('submissions.html', submissions=subs)

@app.route('/article/<int:article_id>')
def article(article_id):
    article = query_db(
        """SELECT s.*, u.firstname, u.lastname, u.email, u.affiliation, u.orcid, sec.title AS section_title, i.volume, i.number, i.year
           FROM submissions s
           JOIN users u ON s.authorid = u.id
           LEFT JOIN sections sec ON s.sectionid = sec.id
           LEFT JOIN issues i ON s.issueid = i.id
           WHERE s.id = ? AND s.status = 'published'""",
        [article_id], one=True
    )
    if not article:
        return "Artigo não encontrado ou não publicado", 404
    return render_template('article.html', article=article)

@app.route('/uploads/<filename>')
@login_required
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    app.run(debug=True)
