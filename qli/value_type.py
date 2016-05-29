#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Allows for easily defining simple value type classes.

e.g.
import value_type
import sys
import textwrap
import argparse   

# Define a value type
class SomeValueType(value_type.ValueSpec):
    VALUE_DELIMITER = ':'
    FIELDS = (ValueField('color', str, 'black', 'Color for objects'),
              ValueField('border_margin', float, 1., 'Border margin size factor'))
  
# Define a list container that convers to and from a string.
class SomeValueTypeList(value_type.ListSpec):
    LIST_SEPARATOR = ','
    LIST_TYPE = SomeValueClass
    
# Defines a value type that is a composite of ValueSpec, ListSpec and other types
class Composite(value_type.ValueSpec):
    VALUE_DELIMITER = '|'
    FIELDS = (value_type.ValueField('some_value', SomeValueType, 'black:1', 'A SomeValueType value'),
              value_type.ValueField('some_list', SomeValueTypeList, 'black:1,red:1.5', 'A list of values'),
              value_type.ValueField('an_int', int, 11, 'An integer', 'd', value_type.no_operation),
              value_type.ValueField('a_bool', bool, False, 'A boolean', 'd', value_type.no_operation))


# Example main that 
def main(argv):
    parser = argparse.ArgumentParser(
            formatter_class=argparse.RawDescriptionHelpFormatter,
            description='Example simple class type.')
    
    # Create a default value
    params = Composite(some_value=SomeValueType('green:33'))    
    # Prepare the ArgumentParser to parse for values in the params class.
    params.add_parser_args(parser)

    # Parse the args and put them in the params object
    args = parser.parse_args() 
    params.set_parsed_args(args)
    
    # Access the values.
    print(params.some_value)
    
    print(repr(params))


Copyriht Notice:
    This file is authored by Gianni Mariani <gianni@mariani.ws>. 27-May-2016.

    This file is part of qli_to_svg.

    qli_to_svg is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    qli_to_svg is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with qli_to_svg.  If not, see <http://www.gnu.org/licenses/>.
"""


import re

def no_operation(v):
    """Provided for types supported by a string format conversion."""
    return v

FALSE_REGEX = re.compile("^no|false|f|0+$", re.IGNORECASE)
def to_bool(v):
  return v.lower() in ("no", "false", "f", "0")

class ValueField(object):
    """Definition of a field.
    name: The field name. Must be a valid python identifier.
    type: The field type. Must accept a single string parameter for initialization.
    default_value: The default value for this field.
    description: Field description used for help in ArgumentParser.
    format_str: The format string to use for to string conversion.
    to_format: A value converter (or no_operation) for use with format_str.
    from_str_converter: If ommitted is the same as type, otherwise a convertsion function.
    """
    TYPE_CONV_MAP = {float: ('g', no_operation, float),
                     int: ('d', no_operation, int),
                     bool: ('d', no_operation, to_bool)}
    DEFAULT_CONVERION = ('s', str)
    def __init__(self, name, type, default_value, description, format_str=None, to_format=None,
                 from_str_converter=None):
        self.name = name
        self.type = type
        self.default_value = default_value
        self.description = description
        
        if format_str:
            self.format_str = format_str
        else:
            self.format_str = self.TYPE_CONV_MAP.get(type, self.DEFAULT_CONVERION)[0]
            
        if to_format:
            self.to_format = to_format
        else:
            self.to_format = self.TYPE_CONV_MAP.get(type, self.DEFAULT_CONVERION)[1]
            
        if from_str_converter:
            self.from_str_converter = from_str_converter
        else:
            self.from_str_converter = self.TYPE_CONV_MAP.get(type, (None, None, type))[2]


class ValueSpec(object):
    """A base class for value objects. The derived class muse define VALUE_DELIMITER 
    as the separator for field in a string and FIELDS containing an ordered list of 
    ValueField objects (order is important).
    """
    def __init__(self, value_str=None, **kwds):
        for field in self.__class__.FIELDS:
            setattr(self, field.name, kwds.get(field.name, field.default_value))
        
        self.set_as_str(value_str)
        
    def set_as_str(self, value_str):
        if not value_str:
            return
        for value, field in zip(
                value_str.split(self.__class__.VALUE_DELIMITER), self.__class__.FIELDS):
            setattr(self, field.name, field.from_str_converter(value))

    def __str__(self, *args, **kwargs):
        return self.__class__.VALUE_DELIMITER.join(
                    ('%' + field.format_str) % field.to_format(getattr(self, field.name))
                        for field in self.__class__.FIELDS)
        
    def __repr__(self, *args, **kwargs):
        return "%s(%r)" % (self.__class__.__name__, str(self))

        
    def add_parser_args(self, parser):
        for field in self.__class__.FIELDS:
            default_help = ''
            value = getattr(self, field.name)
            if value is not None:
                default_help = ' default: %s' % str(value)
            if field.type == bool:
                p = parser.add_mutually_exclusive_group(required=False)
                p.add_argument('--' + field.name, dest=field.name, action='store_true',
                               help=field.description + default_help)
                p.add_argument('--no-' + field.name, dest=field.name, action='store_false',
                               help='See --' + field.name)
                if not value is None:
                    p.set_defaults(**{field.name : value})
            else:
                parser.add_argument('--' + field.name, default=value, 
                        type=field.type, help=field.description + default_help)

    def set_parsed_args(self, args):
        for field in self.__class__.FIELDS:
            setattr(self, field.name, getattr(args, field.name))

class ListSpec(list):
    """Wrapper for a typed list that allows for conversion from a string to list
    with the delimiter LIST_SEPARATOR defined in derived classes.
    """
    def __init__(self, spec_str):
        if spec_str:
            self[:] = [self.__class__.LIST_TYPE(i)
                      for i in spec_str.split(self.__class__.LIST_SEPARATOR)]
        else:
            self[:] = []

    def __str__(self, *args, **kwargs):
        return self.__class__.LIST_SEPARATOR.join(str(i) for i in self)
        
    def __repr__(self, *args, **kwargs):
        return self.__class__.__name__ + '(%r)' % str(self)
    
