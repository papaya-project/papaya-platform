# -*- encoding: utf-8 -*-

from setuptools import setup, find_packages

setup(
    name='papaya_server',
    version='0.0.1',
    packages=find_packages(),  # tells Python what package directories (and the Python files they contain) to include
    include_package_data=True,  # to include other files such as templates and static
    install_requires=[
        'flask',
    ],
)
