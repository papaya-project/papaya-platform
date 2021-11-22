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

import functools
import os

from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for, current_app
)

from papaya_server.models import User
from papaya_server import db

bp = Blueprint('auth', __name__, url_prefix='/auth')


def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            response = redirect(url_for('auth.login'))
            response.autocorrect_location_header = False
            return response

        return view(**kwargs)

    return wrapped_view


@bp.route('/register', methods=('GET', 'POST'))
@login_required
def register():
    if request.method == 'POST':

        u = User.query.filter_by(id=g.user['id']).first()

        if u.admin:
            username = request.form['username'] if 'username' in request.form else None
            password = request.form['password'] if 'password' in request.form else None
            repassword = request.form['repassword'] if 'repassword' in request.form else None

            admin = True if 'admin' in request.form else False

            err = None

            if not username:
                err = 'Username is required.'
            elif not password:
                err = 'Password is required.'
            elif password != repassword:
                err = 'Uncorrected re-entered password'
            if err is None:
                u = User(username=username, admin=admin)
                u.set_password(password)
                db.session.add(u)
                _ = db.session.commit()
                current_app.logger.info('User {0} has been successfully registered'.format(u.username))
                response = redirect(url_for('service.index'))
                response.autocorrect_location_header = False
                return response

            flash(err)
        else:
            flash("Only admin user can register new users")

    return render_template('auth/register.html')


@bp.route('/', methods=('GET', 'POST'))
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        error = None
        user = User.query.filter_by(username=username).first()

        if user is None:
            error = 'Incorrect username.'
        elif not user.check_password(password):
            error = 'Incorrect password.'

        if error is None:
            session['id'] = str(user.id)
            current_app.logger.info('User {0} logged in'.format(user.id))
            response = redirect(url_for('service.index'))
            response.autocorrect_location_header = False
            return response

        flash(error)

    return render_template('auth/login.html')


@bp.route('/logout')
def logout():
    session.clear()
    response = redirect(url_for('auth.login'))
    response.autocorrect_location_header = False
    return response


@bp.before_app_request
def load_logged_in_user():
    user_id = session.get('id')

    if user_id is None:
        g.user = None
    else:
        u = User.query.filter_by(id=user_id).first()

        if u is None:
            g.user = None
            session.clear()
        else:
            g.user = {'username': u.username, 'id': u.id, 'admin': u.admin}


def add_default_admin():

    u = User(username=os.getenv('ADMIN_USERNAME'), admin=True)
    u.set_password(os.getenv('ADMIN_PASSWORD'))
    db.session.add(u)
    db.session.commit()
    current_app.logger.info('Default admin user {0} has been successfully added'.format(u.username))
