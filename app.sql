-- Tabela de usuários
CREATE TABLE users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  email VARCHAR(255) UNIQUE NOT NULL,
  passwordhash VARCHAR(255) NOT NULL,
  firstname VARCHAR(100) NOT NULL,
  lastname VARCHAR(100) NOT NULL,
  role VARCHAR(20) NOT NULL CHECK(role IN ('admin', 'editor', 'reviewer', 'author', 'reader')),
  affiliation TEXT,
  orcid VARCHAR(50),
  bio TEXT,
  phone VARCHAR(20),
  country VARCHAR(100),
  status VARCHAR(20) DEFAULT 'active' CHECK(status IN ('active', 'inactive', 'suspended')),
  emailverified BOOLEAN DEFAULT FALSE,
  verificationtoken VARCHAR(255),
  resettoken VARCHAR(255),
  resettokenexpires DATETIME,
  createdat DATETIME DEFAULT CURRENT_TIMESTAMP,
  updatedat DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Tabela de configurações do periódico
CREATE TABLE journalsettings (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  settingkey VARCHAR(100) UNIQUE NOT NULL,
  settingvalue TEXT,
  settingtype VARCHAR(20) DEFAULT 'text',
  createdat DATETIME DEFAULT CURRENT_TIMESTAMP,
  updatedat DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Tabela de volumes
CREATE TABLE volumes (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  year VARCHAR(20),
  volume VARCHAR(50),
  description TEXT,
  published BOOLEAN DEFAULT 0,
  createdat DATETIME DEFAULT CURRENT_TIMESTAMP,
  updatedat DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Tabela de issues (edições)
CREATE TABLE issues (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  volumeid INTEGER,
  number VARCHAR(50),
  year VARCHAR(20),
  publisheddate DATETIME,
  description TEXT,
  status VARCHAR(20),  -- ex: 'published', 'in_preparation'
  iscurrent INTEGER DEFAULT 0,
  FOREIGN KEY(volumeid) REFERENCES volumes(id)
);

-- Tabela de seções
CREATE TABLE sections (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  title VARCHAR(255),
  description TEXT,
  isactive BOOLEAN DEFAULT 1,
  sortorder INTEGER DEFAULT 0
);

-- Tabela de submissões (artigos)
CREATE TABLE submissions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  title TEXT,
  abstract TEXT,
  keywords TEXT,
  language VARCHAR(20),
  sectionid INTEGER,
  authorid INTEGER,
  issueid INTEGER,
  status VARCHAR(20),  -- ex: submitted, under_review, published
  submissionstage VARCHAR(50),
  doi VARCHAR(255),
  pages VARCHAR(50),
  fileid INTEGER,
  submissiondate DATETIME DEFAULT CURRENT_TIMESTAMP,
  publisheddate DATETIME,
  updatedat DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY(sectionid) REFERENCES sections(id),
  FOREIGN KEY(authorid) REFERENCES users(id),
  FOREIGN KEY(issueid) REFERENCES issues(id),
  FOREIGN KEY(fileid) REFERENCES files(id)
);

-- Tabela de coautores
CREATE TABLE coauthors (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  submissionid INTEGER,
  userid INTEGER,  -- Pode ser NULL se o coautor não estiver no sistema
  email VARCHAR(255),
  FOREIGN KEY(submissionid) REFERENCES submissions(id),
  FOREIGN KEY(userid) REFERENCES users(id)
);

-- Tabela de arquivos (upload)
CREATE TABLE files (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  filename VARCHAR(255),
  filepath TEXT,
  mimetype VARCHAR(100),
  uploaderid INTEGER,
  createdat DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY(uploaderid) REFERENCES users(id)
);

-- Inserir usuários de teste
INSERT INTO users (email, passwordhash, firstname, lastname, role, affiliation, country, status, emailverified, createdat, updatedat)
VALUES ('autor@example.com', 'scrypt:32768:8:1$FmwyHVWyB6M1ispd$8e0d853714869fc352f788ca8844183d5f8df21e1fcfa7a5be963ae839fee650a2d9edbc9136985fb016d7412d1887ec8cefe2d0685bfb22bdb401c3806fcbed', 'João', 'Silva', 'author', 'Universidade X', 'Brasil', 'active', 1, datetime('now'), datetime('now'));

INSERT INTO users (email, passwordhash, firstname, lastname, role, affiliation, country, status, emailverified, createdat, updatedat)
VALUES ('editor@example.com', 'scrypt:32768:8:1$FmwyHVWyB6M1ispd$8e0d853714869fc352f788ca8844183d5f8df21e1fcfa7a5be963ae839fee650a2d9edbc9136985fb016d7412d1887ec8cefe2d0685bfb22bdb401c3806fcbed', 'Maria', 'Oliveira', 'editor', 'Universidade Y', 'Brasil', 'active', 1, datetime('now'), datetime('now'));

-- Inserir volumes
INSERT INTO volumes (year, volume, description, published, createdat, updatedat)
VALUES ('2025', '10', 'Volume 10 do periódico', 1, datetime('now'), datetime('now'));

-- Inserir issues (edições)
INSERT INTO issues (volumeid, number, year, publisheddate, description, status, iscurrent)
VALUES (1, '1', '2025', datetime('now'), 'Edição de janeiro', 'published', 1);

-- Inserir seções
INSERT INTO sections (title, description, isactive, sortorder)
VALUES ('Ciência da Computação', 'Seção para artigos de ciência da computação', 1, 1);

-- Inserir arquivo de teste
INSERT INTO files (filename, filepath, mimetype, uploaderid, createdat)
VALUES ('artigo_teste.pdf', 'uploads/artigo_teste.pdf', 'application/pdf', 1, datetime('now'));

-- Inserir submissão
INSERT INTO submissions (title, abstract, keywords, language, sectionid, authorid, issueid, status, submissionstage, doi, pages, fileid, submissiondate, publisheddate, updatedat)
VALUES ('Estudo sobre algoritmos', 'Resumo do estudo...', 'algoritmos, computação', 'Português', 1, 1, 1, 'published', 'published', '10.1234/teste.doi', '1-10', 1, datetime('now'), datetime('now'), datetime('now'));

-- Inserir coautores
INSERT INTO coauthors (submissionid, userid, email)
VALUES (1, NULL, 'coautor@example.com');