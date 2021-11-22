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

from typing import Callable

MAX_STR_LENGTH = 255


class Validator:

    @staticmethod
    def validate(t, arg):

        return not arg or isinstance(arg, t)


class IntValidator(Validator):

    @staticmethod
    def validate( arg: int):
        """
        Validate if arg is instance of integer
        :param arg:
        :return: boolean
        """
        return Validator.validate(int, arg)

    @staticmethod
    def validate_range(arg: int, min: int, max: int):
        """
        Validate if arg is an instance of integer
        and in range of [min, max]
        min <= arg <= max
        :param arg:
        :param min: minimum in a range
        :param max: maximum in a range
        :return: boolean
        """
        return IntValidator.validate(arg) and min <= arg <= max

    @staticmethod
    def validate_non_zero(arg: int):
        """
        Validate if arg is an instance of integer
        and not zero
        :param arg:
        :param min:
        :return:
        """
        return IntValidator.validate(arg) and arg

    @staticmethod
    def strip_and_cast(arg):

        if arg:
            return int(arg.strip())

        return arg


class StrValidator(Validator):

    @staticmethod
    def validate(arg: str):
        """
        Validate if arg is an instance of string
        :param arg:
        :return: boolean
        """
        return Validator.validate(str, arg)

    @staticmethod
    def validate_non_empty(arg: str):
        """
        Validate if arg is an instance of string
        and non empty
        :param arg:
        :return:  boolean
        """
        return StrValidator.validate(arg) and arg

    @staticmethod
    def validate_length(arg: str, l: int):
        """
        Validate if arg is an instance of str
        and non empty and the length less or equal to l
        :param arg:
        :param l: len
        :return:  boolean
        """
        return StrValidator.validate_non_empty(arg) and len(arg) <= l

    @staticmethod
    def validate_max_length(arg: str):
        """
        Validate if arg is an instance of str,
        non empty and the length less or equal to MAX_STR_LENGTH
        :param arg:
        :return:  boolean
        """

        return StrValidator.validate_length(arg, MAX_STR_LENGTH)

    @staticmethod
    def strip_and_cast(arg):

        return str(arg.strip())


def get_invalid_error(name: str):
    """
    compose the error reason string

    :param name: name of the invalid parameter
    :return:
    """
    return " Invalid " + name




class FormValidator:

    _attributes = None
    _name = None

    def __init__(self, name):
        self._attributes = []
        self._name = name

    def add(self, name: str, type: type, length: int = 0, cf: Callable[[], type] = None,
            vf: Callable[[], bool] = None) -> None:
        self._attributes.append({'name': name, 'type': type, 'length': length, 'cf': cf, 'vf': vf})

    def cast(self, form: dict) -> dict:
        tmp = {}
        for attr in self._attributes:
            # print("Validating attribute " + attr['name'])
            if form[attr['name']] is not None:
                try:
                    tmp[attr['name']] = attr['cf'](form[attr['name']])
                except Exception as e:
                    err = get_invalid_error(attr['name'])
                    return {}, err
        return tmp, None

    def validate(self, form) -> str:

        for attr in self._attributes:

            if not attr['vf'](form[attr['name']]):
                err = self._name + " " + attr['name']
                return get_invalid_error(err)

        return None

    def validate_at_least_one(self, form, l: list, vf: Callable[[], bool]) -> bool:

        return len(list(filter(lambda x: vf(form[x]), l))) != 0


ServiceValidator = FormValidator('service')

ServiceValidator.add(name='name', type=str, length=MAX_STR_LENGTH, cf=StrValidator.strip_and_cast,
                     vf=StrValidator.validate_max_length)
ServiceValidator.add(name='description', type=str, cf=StrValidator.strip_and_cast, vf=StrValidator.validate)
ServiceValidator.add(name='server_container', type=str, length=MAX_STR_LENGTH, cf=StrValidator.strip_and_cast,
                     vf=StrValidator.validate_max_length)
ServiceValidator.add(name='agent_container', type=str, length=MAX_STR_LENGTH, cf=StrValidator.strip_and_cast,
                     vf=StrValidator.validate_max_length)
ServiceValidator.add(name='server_http_port', type=int, cf=IntValidator.strip_and_cast, vf=IntValidator.validate)
ServiceValidator.add(name='server_tcp_port', type=int, cf=IntValidator.strip_and_cast, vf=IntValidator.validate)
ServiceValidator.add(name='agent_http_port', type=int, cf=IntValidator.strip_and_cast, vf=IntValidator.validate)
ServiceValidator.add(name='agent_tcp_port', type=int, cf=IntValidator.strip_and_cast, vf=IntValidator.validate)
