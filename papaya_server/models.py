# -*- encoding: utf-8 -*-
"""
MIT License

Copyright (C)  PAPAYA EU Project 2021

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated
documentation files (the "Software"), to deal in the Software without restriction, including without limitation the
rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit
persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the
Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE
WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

from papaya_server import db

MAX_STR_LENGTH = 255


# Define Role data-model
class Role(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(MAX_STR_LENGTH), unique=True)


# Define Application data-model
class Application(db.Model):
    __tablename__ = 'applications'
    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(MAX_STR_LENGTH), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    service_id = db.Column(db.Integer, db.ForeignKey('services.id',  ondelete='NO ACTION'), nullable=False)
    creation_date = db.Column(db.DateTime(), nullable=False, default=datetime.utcnow)
    server_cfg_filename = db.Column(db.Text, nullable=True)
    agent_cfg_filename = db.Column(db.Text, nullable=True)
    server_url = db.Column(db.Text, nullable=True)
    node_port = db.Column(db.Integer, nullable=True)
    status = db.Column(db.Integer, nullable=False)
    iam = db.Column(db.BOOLEAN, nullable=False, server_default='0')

    db.UniqueConstraint('name', 'user_id', name='app_unq')

    def __repr__(self):
        return '<Application {0} with id {1}>'.format(self.name, self.id)


# Define User data-model
class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    # User authentication information. The collation='NOCASE' is required
    # to search case insensitively when USER_IFIND_MODE is 'nocase_collation'.
    username = db.Column(db.String(MAX_STR_LENGTH, collation='NOCASE'), nullable=False, unique=True)
    password = db.Column(db.String(MAX_STR_LENGTH), nullable=False, server_default='')
    admin = db.Column(db.BOOLEAN, nullable=False, default=False)
    # Define the relationship to Role via UserRoles
    # roles = db.relationship('roles', secondary='user_roles')
    applications = db.relationship('Application', backref='user_apps', lazy='dynamic')
    services = db.relationship('Service', backref='user_services', lazy='dynamic')


    def __repr__(self):
        return '<User {}>'.format(self.username)

    def set_password(self, password: str):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)


# Define Service data-model
class Service(db.Model):
    __tablename__ = 'services'
    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(MAX_STR_LENGTH), nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='NO ACTION'), nullable=False)
    creation_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    description = db.Column(db.Text)
    server_container = db.Column(db.String(MAX_STR_LENGTH), nullable=False)
    server_tcp_port = db.Column(db.Integer)
    server_http_port = db.Column(db.Integer)
    agent_container = db.Column(db.String(MAX_STR_LENGTH), nullable=False)
    agent_tcp_port = db.Column(db.Integer)
    agent_http_port = db.Column(db.Integer)

    db.UniqueConstraint('name', 'author_id', name='service_unq')
    applications = db.relationship('Application', backref='service_apps', lazy='dynamic')

    def __repr__(self):
        return '<Service {0} with id {1}>'.format(self.name, self.id)
