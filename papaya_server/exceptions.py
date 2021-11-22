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

class BaseException(Exception):

    def __init__(self, message, status_code=None, payload=None):

        self.message = message
        self.payload = payload

        if status_code is not None:
            self.status_code = status_code


    def to_dict(self):
        rv = dict(self.payload or ())
        rv['message'] = self.message
        return rv


class NotFound(BaseException):
    def __init__(self, message, status_code=404, payload=None):
        BaseException.__init__(self, message, status_code, payload)


class BadRequest(BaseException):
    def __init__(self, message, status_code=400, payload=None):
        BaseException.__init__(self, message, status_code, payload)


class Forbidden(BaseException):
    def __init__(self, message, status_code=403, payload=None):
        BaseException.__init__(self, message, status_code, payload)


class Conflict(BaseException):
    def __init__(self, message, status_code=409, payload=None):
        BaseException.__init__(self, message, status_code, payload)


class K8sError(BaseException):
    def __init__(self, message, status_code=400, payload=None):
        BaseException.__init__(self, message, status_code, payload)
