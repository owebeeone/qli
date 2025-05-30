#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Converts a qli program generated by qli.py (a subset of Galil DMC) to an SVG file.

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

import cmath
import math
import numpy
import svg.path as svg
from qli import qli_parser

import sys
from qli import value_type

from dataclasses import dataclass

# @dataclass
# class Hack:
#     path: str
# svg = Hack(svg_path)

def merge_dicts(*dict_args):
    """""Given any number of dicts, shallow copy and merge into a new dict,
    precedence goes to key value pairs in latter dicts.
    """
    result = {}
    for dictionary in dict_args:
        result.update(dictionary)
    return result

EPLSILON = 1.e-6

def condition_floats(epsilon=EPLSILON, **kwds):
    """Returns a dict equivalent to the parameters where values less significant
    than epsilon are replaced with 0. This avoids cluttering the output file with 
    insignificant jibberish.
    """
    max_abs = 0
    for k, v in kwds.items():
        max_abs = max(max_abs, abs(v))
    
    result = {}
    for k, v in kwds.items():
        if abs(v) / epsilon < max_abs:
            result[k] = 0
        else:
            result[k] = v
    return result


SVG_HEADER = """
<svg width="{width:0.8g}" height="{height:0.8g}" xmlns="http://www.w3.org/2000/svg">

  <g transform="matrix({m00:0.8g},{m01:0.8g},{m10:0.8g},{m11:0.8g},{translatex:0.8g},{translatey:0.8g})">
"""

SVG_FOOTER = """
  </g>
</svg>
"""

def mat_rot(rotation):
    """Converts a rotation complex number (a complex number with unit size) to an
    equivalent 3x3 homogenous matrix."""
    return numpy.array([
                         [rotation.real, -rotation.imag, 0],
                         [rotation.imag,  rotation.real, 0],
                         [0, 0, 1]])

def mat_scale(scale):
    """Converts a scale complex number (real is x scale, imag is y scale) to an
    equivalent 3x3 homogenous matrix."""
    return numpy.array([
                         [scale.real, 0, 0],
                         [0, scale.imag, 0],
                         [0, 0, 1]])
    
def mat_trans(translation):
    """Converts a translation complex number (real is x translation, imag is y translation) 
    to an equivalent 3x3 homogenous matrix."""
    return numpy.array([
                         [1, 0, translation.real],
                         [0, 1, translation.imag],
                         [0, 0, 1]])

def svg_header(size, scale=1+1j, rotation=1+0j, extents=(0+0j,1+1j)):
    
    centre = extents[0] + (extents[1] - extents[0]) / 2
    
    # Operations - translate center to origin, scale, flip x axis, rotate, translate to new centre
    result_mat = (mat_trans(size / 2) @ mat_rot(rotation) @ mat_scale(-1+1j)
                  @ mat_scale(scale) @ mat_trans(-centre))
    
    return SVG_HEADER.format(
        **merge_dicts(
                {'width':size.real, 'height':size.imag},
                condition_floats(
                         m00=result_mat[0, 0], m10=result_mat[0, 1],
                         m01=result_mat[1, 0], m11=result_mat[1, 1]),
                condition_floats(
                        translatex=result_mat[0, 2], translatey=result_mat[1, 2])))
    
class BorderSpec(value_type.ValueSpec):
    VALUE_DELIMITER = ':'
    FIELDS = (value_type.ValueField('color', str, 'black', 'Color for objects'),
              value_type.ValueField('border_margin', float, 1., 'Border margin size factor'))
    
class BorderSpecList(value_type.ListSpec):
    LIST_SEPARATOR = ','
    LIST_TYPE = BorderSpec
    
class MarginSpec(value_type.ValueSpec):
    VALUE_DELIMITER = 'x'
    FIELDS = (value_type.ValueField('margin_width', float, 100., 'Margin width'),
              value_type.ValueField('margin_height', float, 100., 'Margin height'))
    
    def get(self):
        return complex(self.margin_width, self.margin_height)

class SvgOutputParams(value_type.ValueSpec):
    VALUE_DELIMITER = '|'
    FIELDS = (value_type.ValueField('oncolor', str, 'black', 'The color of the "on" path'),
              value_type.ValueField('offcolor', str, 'red', 'The color of the "off" path'),
              value_type.ValueField('line_width', float, 1., 'Bigger numbers means thicker lines'),
              value_type.ValueField('margin', MarginSpec, '50x50', 'Margin around image'),
              value_type.ValueField('width', float, 700.,
                                    'The image width (inside margin). Aspect ratio is maintained.'),
              value_type.ValueField('borders', BorderSpecList, 'blue:1',
                                    'Comma separated list of borders'))
        

SVG_PATH = """
    <path d="{path}" stroke="{color}" stroke-width="{stroke_width}" fill="none"/>
"""

def svg_path(path, color, stroke_width=5):
    return SVG_PATH.format(path=path, color=color, stroke_width=stroke_width)


class SvgOutContext(object):
    def __init__(self, pattern, params):
        self.pattern = pattern
        self.params = params
        
        extents = pattern.extents
        size = extents[1] - extents[0]
        self.bounding_box_delta = math.ceil((size.real + size.imag) * 0.02) * (1+1j)
        
        self.line_width = math.ceil((size.real + size.imag) * 0.001) * params.line_width

class SvgPath(object):
    def __init__(self, needle_state, path, alternate_color=None):
        self.needle_state = needle_state
        self.path = path
        self.alternate_color = alternate_color
        
        first = self.path[0]
        if not isinstance(first, svg.path.Move):
            self.path.insert(0, svg.path.Move(first.start))
        
        
    def svg(self, context):
        params = context.params
        color = params.oncolor if self.needle_state else params.offcolor
        if self.alternate_color:
            color = self.alternate_color
        return svg_path(self.path.d(), color, context.line_width)

        
class SvgPattern(object):
    def __init__(self, program, extents):
        self.program = program
        self.extents = extents
        self.svg_elements = []
        
    def add_bounding_box(self, color, offset=0j):
        box = svg.path.Path()
        extents = (self.extents[0] - offset, self.extents[1] + offset)
        box.append(svg.path.Line(extents[0], extents[0].real+1j*extents[1].imag))
        box.append(svg.path.Line(extents[0].real+1j*extents[1].imag, extents[1]))
        box.append(svg.path.Line(extents[1], extents[1].real+1j*extents[0].imag))
        box.append(svg.path.Line(extents[1].real+1j*extents[0].imag, extents[0]))
        self.append(SvgPath(False, box, color))
    
    def append(self, path):
        self.svg_elements.append(path)
        
    def write(self, f, context):
        pattern_size = self.extents[1] - self.extents[0]
        sizex = context.params.width
        scale = sizex / pattern_size.real
        sizey = scale * pattern_size.imag
        
        overall_size = complex(sizex, sizey) + 2 * context.params.margin.get()
        
        f.write(svg_header(overall_size,
                           complex(scale, scale),
                           rotation=cmath.rect(1, math.pi), extents=self.extents))
        
        for element in self.svg_elements:
            elem_str = element.svg(context)
            f.write(elem_str)
            
        f.write(SVG_FOOTER)
        

    def write_svg(self, f, params):
        pattern = self
        context = SvgOutContext(self, params)
        
        for border in params.borders:
            pattern.add_bounding_box(
                    border.color, context.bounding_box_delta * border.border_margin)
        
        pattern.write(f, context)        


class QliSvgExtentsExecutor(qli_parser.QliExecutor):
    """Computes the entents of a pattern.
    """
    def __init__(self, program):
        qli_parser.QliExecutor.__init__(self, program)
        self.axes = (0, 1)
        self.cur_loc = 0j
        self.min_extent = 0j
        self.max_extent = 0j
        self.relative = 0
        
    def coord(self, d1, d2):
        args = (d1, d2)
        return args[self.axes[0]] + 1j * args[self.axes[1]]
    
    def new_extent(self, loc):
        self.min_extent = complex(
                min(loc.real, self.min_extent.real), 
                min(loc.imag, self.min_extent.imag))
        self.max_extent = complex(
                max(loc.real, self.max_extent.real), 
                max(loc.imag, self.max_extent.imag))
    
    def doVectorMotion(self, index, command):
        self.axes = command.axes
            
    def doCircle(self, index, command):
        r = command.radius
        sa = command.start_angle * math.pi / 180.0
        ea = sa + command.angle_range * math.pi / 180.0
        sp = cmath.rect(r, sa)
        ep = cmath.rect(r, ea)
        delta = ep - sp
        next_loc = self.cur_loc + delta
        self.new_extent(next_loc)
        
        # Compute extents for rest of circle.
        saf = 2 * sa / math.pi
        eaf = 2 * ea / math.pi
        
        if eaf < saf:
            eaf, saf = saf, eaf
        
        saf = math.floor(saf)
        i = 1
        while i < 4 and saf + i < eaf:
            ex = cmath.rect(r, math.pi * 0.5 * (saf + i))
            self.new_extent(ex - sp + self.cur_loc)
            i += 1
            
        self.cur_loc = next_loc
    
    def doVectorPosition(self, index, command):
        next_loc = self.coord(command.d1, command.d2) + self.relative
        self.new_extent(next_loc)
        self.cur_loc = next_loc

    def doClearSequence(self, index, command):
        self.cur_loc = 0j

    def doVectorSequenceEnd(self, index, command):
        self.relative = self.cur_loc
        
    def get_extents(self):
        return (self.min_extent, self.max_extent)
    

class QliSvgExecutor(qli_parser.QliExecutor):
    
    def __init__(self, program):
        qli_parser.QliExecutor.__init__(self, program)
        self.axes = (0, 1)
        self.needle_on = True
        self.svg_current_path = svg.path.Path()
        self.program = program
        self.extents = QliSvgExtentsExecutor(program)
        program.execute(self.extents)
        
        self.start_loc = 0j
        self.cur_loc = self.start_loc
        self.pattern = SvgPattern(program, self.extents.get_extents())
        self.relative = 0
        
    def run(self):
        self.program.execute(self)
        self.end_path()
        
    def coord(self, d1, d2):
        args = (d1, d2)
        return args[self.axes[0]] + 1j * args[self.axes[1]]
        
    def doVectorMotion(self, index, command):
        self.axes = command.axes
        
        if False:
            sys.stderr.write("vector motion %s\n" % repr(command.groups))
            sys.stderr.write("axes = " + repr(command.axes) + "\n")
            
    def doCircle(self, index, command):
        r = command.radius
        sa = math.pi * (command.start_angle) / 180.0
        ea = sa + command.angle_range * math.pi / 180.0
        sp = cmath.rect(r, sa)
        ep = cmath.rect(r, ea)
        delta = ep - sp
        next_loc = self.cur_loc + delta
        mod_angle = (abs(command.angle_range) % 360)
        large_arc = mod_angle > 180
        
        sweep = command.angle_range > 0
        if True:
            arc = svg.path.Arc(self.cur_loc, complex(r, r), 0, large_arc, sweep, next_loc)
            self.svg_current_path.append(arc)
        else:
            self.add_debug_path(self.cur_loc, next_loc)
        self.cur_loc = next_loc
        
    def add_debug_path(self, cur_loc, next_loc):
        line = svg.path.Line(cur_loc, next_loc)
        self.svg_current_path.append(line)
    
    def doVectorPosition(self, index, command):
        next_loc = self.coord(command.d1, command.d2) + self.relative
        line = svg.path.Line(self.cur_loc, next_loc)
        self.svg_current_path.append(line)
        self.cur_loc = next_loc
    
    def doVectorSequenceEnd(self, index, command):
        self.end_path()
        self.relative = self.cur_loc
            
    def doClearSequence(self, index, command):
        self.cur_loc = self.start_loc
    
    def doNeedleOff(self, index, command):
        self.set_needle(False)
        
    def doNeedleOn(self, index, command):
        self.set_needle(True)
            
    def set_needle(self, state):
        # Previous motion should be generated.
        if self.needle_on != state:
            self.end_path()
        self.needle_on = state
        
    def end_path(self):
        if len(self.svg_current_path):
            self.pattern.append(SvgPath(self.needle_on, self.svg_current_path))
        self.svg_current_path = svg.path.Path()

    def doEnd(self, index, command):
        self.end_path()
        
    def get_svg_patttern(self):
        self.end_path()
        return self.pattern
    
        
        
        