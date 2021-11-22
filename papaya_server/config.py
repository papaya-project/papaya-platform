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

"""
License: MIT
Copyright (c) 2019 - present AppSeed.us
"""

import os
from pathlib import Path


class Config(object):

    #set the base dir
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    ROOT_PATH = Path(__file__).parent.parent
    instance_dir = os.path.join(str(ROOT_PATH), 'instance')

    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///' + os.path.join(instance_dir, 'venv.sqlite')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    print("SQLALCHEMY_DATABASE_URI {0}".format(SQLALCHEMY_DATABASE_URI))

    LOG_FOLDER = os.path.join(instance_dir, 'log')
    print("LOG_FOLDER {0}".format(LOG_FOLDER))

    UPLOAD_FOLDER = os.path.join(instance_dir, 'configs')
    print("UPLOAD_FOLDER {0}".format(UPLOAD_FOLDER))
    # set initial admin password and username
    ADMIN_USERNAME = os.getenv('ADMIN_USERNAME')
    ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD')
    SECRET_KEY = os.getenv('ADMIN_PASSWORD') or 'need-to-change-before-deploy'

    k8s = {
        'agent': {
            'cfg_file': 'env.list',
        },

        'namespace': 'papaya',
        'cluster_ip': '<Cluster IP>',
        'host': '<Ingress Subdomain>',
        # range of open ports, which are used for TCP communication
        'open_ports_range': {
            'start': 32000,
            'end': 32050
        }
    }

    logging = {
        'kibana': {
            'host': 'kibana.kube-logging.svc',
            'port': 5601
        },
        'es': {
            'host': 'elasticsearch.kube-logging.svc',
            'port': 9200,
            'index': "filebeat*"
        }
    }
