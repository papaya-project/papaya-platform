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

from flask import (
    Blueprint, flash, g, redirect, render_template, request, url_for, current_app
)
from .auth import login_required
from papaya_server import db
from papaya_server.models import Service, User
from .validator import StrValidator, IntValidator, get_invalid_error, ServiceValidator

bp = Blueprint('service', __name__, url_prefix='/services')


@bp.route('/', methods=('GET',))
@login_required
def index():

    services = get_services()

    return render_template('service/index.html', services=services)


@bp.route('/create', methods=('GET', 'POST'))
@login_required
def create():

    if request.method == 'POST':

        form, err = cast_post_form(request.form)
        if err:
            current_app.logger.error(err)
            flash(err)

        else:
            err = validate_post_form(form)
            if err:
                current_app.logger.error(err)
                flash(err)

            else:
                s = Service(name=form['name'], author_id= g.user['id'], description=form['description'],
                            server_container=form['server_container'], server_http_port=form['server_http_port'],
                            server_tcp_port=form['server_tcp_port'], agent_container=form['agent_container'],
                            agent_http_port=form['agent_http_port'], agent_tcp_port=form['agent_tcp_port'])

                db.session.add(s)
                db.session.commit()

                current_app.logger.info('{0} was created'.format(s))

                response = redirect(url_for('service.index'))
                response.autocorrect_location_header = False
                return response

    return render_template('service/create.html')


@bp.route('/<int:id>/update', methods=('GET', 'POST'))
@login_required
def update(id):

    service = get_service(id, g.user['id'])
    if request.method == 'POST':

        form, err = cast_post_form(request.form)
        if err:
            current_app.logger.error(err)
            flash(err)
        else:
            err = validate_post_form(form)

            if err:
                current_app.logger.error(err)
                flash(err)

            else:
                service.name = form['name']
                service.description = form['description']
                service.server_container = form['server_container']
                service.server_tcp_port = form['server_tcp_port']
                service.server_http_port = form['server_http_port']
                service.agent_container = form['agent_container']
                service.agent_tcp_port = form['agent_tcp_port']
                service.agent_http_port = form['agent_http_port']

                db.session.commit()
                current_app.logger.info('{} was updated'.format(service))

                response = redirect(url_for('service.index'))
                response.autocorrect_location_header = False
                return response

    return render_template('service/update.html', service=service)


@bp.route('/<int:id>/delete', methods=('POST',))
@login_required
def delete(id):

    service = get_service(id, g.user['id'])
    db.session.delete(service)
    db.session.commit()

    current_app.logger.info("Service {} with id {} was deleted".format(service.name, id))

    response = redirect(url_for('service.index'))
    response.autocorrect_location_header = False
    return response


def get_services():
    """
    Retrieve all services
    :return: services-object
    """
    return Service.query.order_by(Service.creation_date).all()


def cast_post_form(form: dict) -> dict:
    """
        Casting the request form based on the definition in validator
    :param form: request form dictionary
    :return: casted dictionary
    """
    return ServiceValidator.cast(form)


def validate_post_form(form: dict) -> str:
    """
    Validate the service's parameters on post request
    :param form: request post form
    :return: error: str
    """
    err = ServiceValidator.validate(form)
    if err:
        return err

    if not ServiceValidator.validate_at_least_one(form, ['server_tcp_port', 'server_http_port'],
                                                  IntValidator.validate_non_zero):
        err = "At least one of the server's communication ports should be defined"
        return err

    if not ServiceValidator.validate_at_least_one(form, ['agent_tcp_port', 'agent_http_port'],
                                                  IntValidator.validate_non_zero):
        err = "At least one of the agent's communication ports should be defined"
        return err

    return err


def get_service_by_id(id):
    """
    Retrieve service by service id
    :param id: service id
    :return: service: object
    """
    return Service.query.filter_by(id=id).order_by(Service.creation_date).first()


def get_service_by_user(id, user_id):
    """
    Retrieve service by service id and user id
    :param id: service id
    :param user_id: service author id
    :return:  service: object
    """
    return Service.query.filter_by(id=id, author_id=user_id).order_by(Service.creation_date).first()


def get_service(id: int, user_id: int = None):

    return get_service_by_id(id) if user_id is None else get_service_by_user(id, user_id)
