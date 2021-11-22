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

import os
import uuid

import stringcase
from flask import (Blueprint, current_app, flash, g, redirect, render_template, request, send_from_directory, url_for)
from werkzeug.exceptions import abort
from werkzeug.utils import secure_filename

import papaya_server.services as service
from papaya_server import db
from papaya_server.config import Config
from papaya_server.exceptions import K8sError
from papaya_server.k8s_client import K8s
from papaya_server.models import Application, User
from papaya_server.validator import StrValidator
from papaya_server.auth import login_required
from papaya_server.constants import AppStatus as AppStatus


bp = Blueprint('application', __name__, url_prefix='/applications')


if os.getenv('NOT_BUILDING', False):
    kubernetes = K8s(os.getenv('INCLUSTER_K8S_CONFIG', False), ports_range=Config.k8s['open_ports_range'])


@bp.route('/', methods=('GET',))
@login_required
def index():
    node_ports = []
    all_apps = Application.query.all()
    # retrieve all used ports
    for a in all_apps:
        if a.node_port:
            node_ports.append(a.node_port)

    kubernetes.open_ports.init(node_ports)
    apps = Application.query.filter_by(user_id=g.user['id']).order_by(Application.creation_date).all()
    return render_template('application/index.html', applications=apps)


@bp.route('/<int:id>/create', methods=('GET', 'POST'))
@login_required
def create(id):
    s = service.get_service(id)
    service_id = s.id

    if request.method == 'POST':
        if s is not None:
            name = request.form['name'].strip()
            if not StrValidator.validate_max_length(name):
                flash('Invalid application\'s name')

            else:
                username = g.user['username']
                server_cfg_filename = None

                if len(request.files) > 0:
                    f = request.files['file']
                    server_cfg_filename, cfg_path = upload_file(f, username, name)

                iam = True if 'iam' in request.form else False
                app = Application(name=name, user_id=g.user['id'], service_id=service_id,
                                  server_cfg_filename=server_cfg_filename, iam=iam, status=AppStatus.CREATED.value)
                db.session.add(app)
                db.session.commit()
                current_app.logger.info('{} was created'.format(app))

                response = redirect(url_for('application.index'))
                response.autocorrect_location_header = False
                return response

    return render_template('application/create.html', service=s)


@bp.route('/<int:id>/update', methods=('GET', 'POST'))
@login_required
def update(id):
    # get application by id and user id
    a = get_application(id, g.user['id'])

    if a is None:
        flash('Application not found')
    elif a.status == AppStatus.ACTIVE.value:
        flash('Can not edit Active application')

    elif request.method == 'POST':
        name = request.form['name'].strip()

        if not StrValidator.validate_max_length(name):
            flash('Invalid application\'s name')

        else:
            # check if there need to update the config file
            if len(request.files) > 0:

                if a.server_cfg_filename is not None:
                    # delete the prev config file
                    path = build_path(a.name, g.user['username'])
                    server_cfg_file = os.path.join(path, a.server_cfg_filename)
                    os.remove(server_cfg_file)

                # update the config file
                fname = request.files['file']
                upload_file(fname, g.user['username'], name)

        a.name = name
        a.server_cfg_file = server_cfg_file
        db.session.commit()

        current_app.logger.info('{} was updated'.format(a))

        response = redirect(url_for('application.index'))
        response.autocorrect_location_header = False
        return response

    return render_template('application/update.html', application=a)


@bp.route('/<int:id>/delete', methods=('POST',))
@login_required
def delete(id):

    a = get_app_by_user(id, g.user['id'])

    if a.status == AppStatus.ACTIVE.value:
        flash("Can not delete ACTIVE application. The application should be terminated")

    else:

        try:
            if a.server_cfg_filename is not None:
                path = build_path(a.name, g.user['username'])
                server_cfg_file = os.path.join(path, a.server_cfg_filename)
                os.remove(server_cfg_file)

            if a.agent_cfg_filename is not None:
                path = build_path(a.name, g.user['username'])
                agent_cfg_file = os.path.join(path, a.agent_cfg_filename)
                os.remove(agent_cfg_file)

            db.session.delete(a)

        except Exception as e:

            current_app.logger.error(e)
            response = redirect(url_for('application.index'))
            response.autocorrect_location_header = False
            return response

        current_app.logger.info('Application {0} were successfully deleted'.format(a.id))
        db.session.commit()

    response = redirect(url_for('application.index'))
    response.autocorrect_location_header = False
    return response


@bp.route('/<int:id>/activate', methods=('POST',))
@login_required
def activate(id):

    try:
        cfg = Config.k8s
        namespace = cfg['namespace']

        a = get_application(id, g.user['id'])
        # allow running only for created or terminated applications
        if a.status != AppStatus.ACTIVE.value:

            url = '-'
            service_id = a.service_id
            s = service.get_service(service_id)

            user = User.query.filter_by(id=g.user['id']).first()
            env_dict = dict()

            # generate app name
            app_name = get_app_name(a.name, user.username)
            app_unique = uuid.uuid4().hex[:6]
            n_port = None

            # it won't be used if it's not an http service
            ports = {
                'tcp': {'source': s.server_tcp_port, 'target': None},
                'http': {'source': s.server_http_port, 'target': None}
            }

            if s.server_http_port:

                url = "https://" + app_unique + "." + cfg['host']
                if s.server_tcp_port:
                    n_port = kubernetes.deploy_dual_port_application(app_name=app_name, uuid=app_unique,
                                                                     image=s.server_container, namespace=namespace,
                                                                     ports=ports, host=cfg['host'], iam=a.iam, url=url)
                    env_dict['SERVER_URL'] = url
                    env_dict['SERVER_IP'] = cfg['cluster_ip']
                    env_dict['SERVER_TCP_PORT'] = n_port

                else:
                    kubernetes.deploy_http_application(app_name=app_name, uuid=app_unique, image=s.server_container,
                                                       namespace=namespace, ports=ports, host=cfg['host'],
                                                       iam=a.iam, url=url)
                    env_dict['SERVER_URL'] = url

            elif s.server_tcp_port:
                if a.iam:
                    raise AttributeError("Can't deploy socket application with IAM")

                n_port = kubernetes.deploy_tcp_application(app_name=app_name, uuid=app_unique, image=s.server_container,
                                                           namespace=namespace, ports=ports, host=cfg['host'])
                env_dict['SERVER_IP'] = cfg['cluster_ip']
                env_dict['SERVER_TCP_PORT'] = n_port

            else:
                msg = "Unknown application type"
                current_app.logger.error(msg)
                current_app.logger.error("Error occurred in application.activate function")
                raise K8sError(msg)

            # save env list file
            create_agent_cfg_file(app_name=a.name, usr=user.username, env_dict=env_dict)
            a.agent_cfg_filename = cfg['agent']['cfg_file']

            # update application's data in the DB
            a.node_port = n_port
            a.status = AppStatus.ACTIVE.value
            a.server_url = url

            db.session.commit()

        else:
            flash('The application is already active')

    except K8sError as e:
        current_app.logger.error("Error occurred in application.activate K8s side")
        current_app.logger.exception(e)
        flash('Error occurred in application activation')

    except Exception as e:
        current_app.logger.error("Error occurred in application.activate function")
        current_app.logger.exception(e)

    finally:
        response = redirect(url_for('application.index'))
        response.autocorrect_location_header = False
        return response


@bp.route('/<int:id>/terminate', methods=('POST',))
@login_required
def terminate(id):

    try:
        cfg = Config.k8s
        namespace = cfg['namespace']
        a = get_application(id, g.user['id'])

        if a.status != AppStatus.ACTIVE.value:
            flash("Can not terminate not ACTIVE application {0}".format(a.name))

        else:
            app_name = get_app_name(a.name, g.user['username'])

            if a.server_url and a.node_port:
                kubernetes.terminate_service(name=app_name, namespace=namespace, type='dual', node_port=a.node_port,
                                             iam=a.iam)

            elif a.server_url:
                kubernetes.terminate_service(name=app_name, namespace=namespace, type='http', iam=a.iam)

            elif a.node_port:
                kubernetes.terminate_service(name=app_name, namespace=namespace, type='tcp', node_port=a.node_port)

            else:
                msg = "Unknown application type"
                current_app.logger.error(msg)
                current_app.logger.error("Error occurred in application.activate function")
                raise K8sError(msg)

    except K8sError:
        current_app.logger.info("Wasn't able to terminate the application")
        flash("Wasn't able to terminate the application")

    except Exception as e:
        current_app.logger.error('Error occurred in terminate application [{}]'.format(a.id))
        current_app.logger.exception(e)

    else:
        # update application's data in the DB
        a.status = AppStatus.TERMINATED.value
        a.server_url = None
        a.node_port = None
        a.agent_cfg_filename = None
        db.session.commit()

    finally:
        response = redirect(url_for('application.index'))
        response.autocorrect_location_header = False
        return response


@bp.route('/<int:id>/<string:cfg_filename>/download_cfg/', methods=('GET', 'POST'))
@login_required
def download_cfg(id, cfg_filename):

    app = get_application(id, g.user['id'])

    if app.server_cfg_filename == cfg_filename or app.agent_cfg_filename == cfg_filename:

        uploads = build_path(app.name, g.user['username'])
        return send_from_directory(directory=uploads, filename=cfg_filename)
    else:
        flash('Invalid file name')
        response = redirect(url_for('application.index'))
        response.autocorrect_location_header = False
        return response


def upload_file(file, username, name):
    """
    store file in predefined path

    :param file: filename
    :param username: username
    :param name: application name
    :return:
    """
    cfg_filename = secure_filename(file.filename)

    path = build_path(name, username)

    if not os.path.exists(path):
        os.makedirs(path)

    config_path = os.path.join(path, cfg_filename)
    file.save(config_path)

    return cfg_filename, config_path


def get_application(id: int, user_id: int):
    """
    Retrieve application by application id
    if user_id is provided it will filter also by user id
    :param id: application id
    :param user_id: user id
    :return: application:
    """
    app = get_app(id) if user_id is None else get_app_by_user(id, g.user['id'])

    if app is None:
        abort(404, "Application id {0} doesn't exist.".format(id))

    return app


def get_app_by_user(id: int, user_id: int):
    """
    Retrieve application by application id and user id
    :return:
    :param id: application id
    :param user_id: user id
    :return: application object
    """

    return Application.query.filter_by(id=id, user_id=user_id).first()


def get_app(id: int):
    """
    Retrieve application by application id
    :return:
    :param id: application id
    :return: application object
    """
    return Application.query.filter_by(id=id).first()


def build_path(app_name, username):
    """
    builds path by the following format
    <UPLOAD FOLDER>/<USERNAME>/<APPLICATION NAME>
    :param app_name: application name
    :param username:  username
    :return: path
    """

    return os.path.join(current_app.config['UPLOAD_FOLDER'], username, app_name)


def get_app_name(app_name, username):
    """
    performs manipulation on the application name, removes spaces/tabs etc.
    :param app_name: application name
    :param username: user name of an application owner
    :return: development name
    """
    return stringcase.spinalcase(app_name.lower() + " " + username.lower())


def delete_app(name, namespace):
    """
    :param name: application name
    :param namespace:  namespace
    :return:

    error if error occurred otherwise None
    """
    api_response, error = kubernetes.delete_deployment(name, namespace)

    if error is None:

        current_app.logger.info("Deployment for application {0} were successfully deleted".format(name))

        api_response, error = kubernetes.delete_service(name, namespace)

        if error is None:
            current_app.logger.info("Service for application {0} were successfully deleted".format(name))

    return error


def create_agent_cfg_file(app_name, usr, env_dict):

    path = build_path(app_name, usr)

    if not os.path.exists(path):
        os.makedirs(path)

    config_path = os.path.join(path, Config.k8s['agent']['cfg_file'])
    with open(config_path, "w+") as f:
        for key, value in env_dict.items():
            line = key.upper() + "=" + (str(value)).strip() + "\n"
            f.write(line)
        f.write("\n")
        return config_path
