DROP TABLE IF EXISTS user;
DROP TABLE IF EXISTS service;
DROP TABLE IF EXISTS application;

CREATE TABLE user (

  username TEXT PRIMARY KEY NOT NULL,
  password TEXT NOT NULL

);

CREATE TABLE service (

    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    author_id TEXT NOT NULL,
    creation_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    description TEXT,
    server_container TEXT NOT NULL,
    server_port INTEGER NOT NULL,
    agent_container TEXT NOT NULL,
    agent_port INTEGER NOT NULL,
    status SMALLINT NOT NULL DEFAULT 1,

    CONSTRAINT ser_usr_fk FOREIGN KEY (author_id) REFERENCES user (username)
    CONSTRAINT ser_unq UNIQUE (name, author_id)

);

CREATE TABLE application (

    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    username TEXT NOT NULL,
    service_id INTEGER NOT NULL,
    creation_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    server_cfg_filename TEXT,
    agent_cfg_filename TEXT,
    server_url URL,
    status SMALLINT NOT NULL DEFAULT 0,

    CONSTRAINT app_unq UNIQUE (name, username)
    CONSTRAINT app_usr_fk FOREIGN KEY (username) REFERENCES user (username),
    CONSTRAINT app_cat_fk FOREIGN KEY (service_id) REFERENCES service (id)
);