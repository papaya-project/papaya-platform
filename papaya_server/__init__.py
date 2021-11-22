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
from flask import Flask, jsonify
from papaya_server.config import Config
from papaya_server.exceptions import BaseException
import click
from flask.cli import with_appcontext
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate, MigrateCommand, Manager

db = SQLAlchemy()
migrate = Migrate()


def create_app(test_config=None):
    """
    :param test_config: configuration map for test environment
    :return:
    """
    # create and configure the app
    app = Flask(__name__, instance_relative_config=False)

    configure_app(app, test_config)
    configure_db(app)
    # Import and register the blueprint from the factory using
    configure_blueprints(app)
    # set error handler
    configure_http_error_handler(app)

    return app


def configure_db(app):
    """
    :param app: flask app context
    :return:
    """
    db.init_app(app)

    app.cli.add_command(create_db)
    app.cli.add_command(reset_db)

    migrate.init_app(app=app, db=db)
    manager = Manager(app=app)
    manager.add_command('db', MigrateCommand)


@click.command('init-db')
@with_appcontext
def create_db():
    """Initiate a new SQL Lite instance"""
    db.create_all()

    from papaya_server.auth import add_default_admin
    add_default_admin()

    click.echo('Initialized the database.')


@click.command('reset-db')
@with_appcontext
def reset_db():
    """Clear the existing data and create new tables."""
    db.drop_all()
    db.create_all()
    from papaya_server.auth import add_default_admin
    add_default_admin()
    click.echo('Reset the database.')


def configure_app(app, test_config=None):
    """
    Setting configuration os flask app
    :param app: flask app context
    :param test_config: configuration map for test environment
    :return:
    """
    if test_config is None:
        # load the instance config, if it exists, when not testing
        app.logger.info("Loading config from object object")
        app.config.from_object(Config)
    else:
        # load the test config if passed in
        app.config.from_mapping(test_config)

    # ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    configure_logging(app)


def configure_http_error_handler(app):
    """
    :param app: flask app context
    :return: error response handler
    """
    @app.errorhandler(BaseException)
    def handle_invalid_usage(error):
        response = jsonify(error.to_dict())
        response.status_code = error.status_code
        return response


def configure_blueprints(app):
    """
    :param app: flask app context
    :return:
    """
    from . import error
    app.register_blueprint(error.bp)

    from . import auth
    app.register_blueprint(auth.bp)

    from . import services
    app.register_blueprint(services.bp)

    from . import applications
    app.register_blueprint(applications.bp)

    from . import k8s_logging
    app.register_blueprint(k8s_logging.bp)

    # print(url_for('auth.index'))
    app.add_url_rule('/', view_func=services.index)


def configure_logging(app):
    """Configure file(info) and email(error) logging.
    :param app: flask app context
    :return:
    """
    import logging

    if app.debug or app.testing:
        # Skip debug and test mode. Just check standard output.
        return

    import os
    from logging.handlers import SMTPHandler

    # Set info level on logger, which might be overwritten by handers.
    # Suppress DEBUG messages.
    app.logger.setLevel(logging.DEBUG)

    if not os.path.exists(app.config['LOG_FOLDER']):
        os.makedirs(app.config['LOG_FOLDER'])

    info_log = os.path.join(app.config['LOG_FOLDER'], 'info.log')

    info_file_handler = logging.handlers.RotatingFileHandler(info_log, maxBytes=100000, backupCount=10)
    info_file_handler.setLevel(logging.INFO)
    info_file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s '
        '[in %(pathname)s:%(lineno)d]')
    )
    app.logger.addHandler(info_file_handler)
