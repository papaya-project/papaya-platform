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

import datetime
import time
import os
import logging

from flask import (
    Blueprint, g, render_template
)
from elasticsearch import Elasticsearch
from papaya_server.auth import login_required
from papaya_server.config import Config
from papaya_server.applications import get_app_by_user, get_app_name


bp = Blueprint('k8s_logging', __name__, url_prefix='/k8s_logging')
logger = logging.getLogger(__name__)


def _get_es_connection():

    logging_cfg = Config.logging

    if os.getenv('INCLUSTER_K8S_CONFIG', False):
        host = logging_cfg['es']['host']
        port = logging_cfg['es']['port']

    else:
        host = 'localhost'
        port = 9200

    return Elasticsearch([{'host': host, 'port': port}], timeout=30)


es = _get_es_connection()


@bp.route('<int:id>/<int:page>', methods=('GET',))
@login_required
def index(id, page, allow_prev=True):

    """returns logging information"""
    app = get_app_by_user(id, g.user['id'])
    size = 20
    start = page * size
    logs, total = retrieve_logs(start=start, size=size, app_name=app.name.lower(), username=g.user['username'])
    allow_prev = (page + 1) * size < total
    return render_template('logging/index.html', logs=logs, id=id, page=page, allow_prev=allow_prev)


@bp.route('/admin_view', methods=('GET',))
@login_required
def admin_view():
    # TODO: add check if admin
    logging_cfg = Config.logging

    if os.getenv('INCLUSTER_K8S_CONFIG', False):
        host = logging_cfg['kibana']['host']
        port = logging_cfg['kibana']['port']

    else:
        host = 'localhost'
        port = 5601

    iframe = "http://{}:{}/app/logs/stream".format(host, port)
    return render_template('logging/kibana_logging.html', iframe=iframe)


def flask_logger():
    """creates logging information"""
    for i in range(10):
        current_time = datetime.datetime.now().strftime('%H:%M:%S') + "\n"
        yield current_time.encode()
        time.sleep(0.1)


def retrieve_logs(start, size, app_name=None, username=None):

    logfile_name = get_app_name(app_name, username)
    logging.info("Looking for file {}".format(logfile_name))

    query = {
        ""
        "from": start,
        "size": size,
        "sort": [{"@timestamp": {"order": "desc"}}],
        "query": {
            "wildcard": {
                "log.file.path": {
                    "value": "/var/data/kubeletlogs/*/{}/*.log".format(logfile_name)
                }
            }
        }
    }
    data = es.search(index='filebeat*', body=query)
    print(len(data))

    if len(data) == 0:
        return [], data['hits']['total']['value']

    logs = [d['_source']['message'] for d in data['hits']['hits']]
    logs.reverse()
    return logs, data['hits']['total']['value']
