#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Converts a .qli format file in a Qli program.

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
import sys
import traceback

def log(st, **kwds):
    sys.stderr.write(st + ": " + repr(kwds) + "\n")
    pass
#
# Error Exceptions

class InternalError(Exception):
    """An intenal parser consistency error was found.
    """
    pass

class QliSyntaxError(Exception):
    """A syntax error in parsed input was found.
    """
    def __init__(self, inputstr, pos, lineno=None, formaterr=None):
        self.inputstr = inputstr
        self.pos = pos
        self.lineno = lineno
        super(Exception, self).__init__(
            "Syntax error %s pos=%d line:%s%s" % (
                '' if not lineno else 'lineno=%s' % lineno,
                pos,
                inputstr,
                ' err=%s' % str(formaterr) if formaterr else ''))
        
class FormatError(Exception):
    pass

TERMINATOR = "(?:\\s*[;\n]|\r\n)"
NON_TERM_STR = "[^;\n]*"
NUMBER_RE = "\\s*([0-9.*/+\\-@\\[\\(\\]\\)A-Z]*)\\s*"
COMMA_NUMBER_RE = "," + NUMBER_RE
OPTIONAL_LT_NUMBER_RE = "(?:\\s*<" + NUMBER_RE + ")?"
OPTIONAL_GT_NUMBER_RE = "(?:\\s*>" + NUMBER_RE + ")?"
LABEL_RE = "\\s*([A-Za-z0-9]+)\\s*"

class Arg(object):
    """Defines components of a "Command".
    """
    def init(self, name, regex, group_count, required=True):
        self.name = name
        self.regex = regex
        self.group_count = group_count
        self.required = required
        
    def parse(self, groups):
        if len(groups) == 1:
            return groups[0]
        return ''.join(groups)
        
CRAXY1 = "(?:@RND\\[([+\\-]?[0-9]*\\.?[0-9]+)\\*S.\\])"
CRAXY2 = "(?:\\(([+\\-]?[0-9]*\\.?[0-9]+)\\*S.\\))"
class NumberArg(Arg):
    RE = re.compile('([+\\-]?[0-9]*\\.?[0-9]+)|%s' % '|'.join((CRAXY1, CRAXY2)))

    def __init__(self, name, required=True):
        self.init(name, NUMBER_RE, 1, required)
        
    def parse(self, groups):
        if len(groups) != 1:
            raise InternalError('Number parsing expecting 1 group for %s\n' % self.name)
        st = groups[0]
        if not st:
            if self.required:
                raise FormatError('Missing required arg %s\n' % self.name)
            return None
        match = self.__class__.RE.match(st)
        if not match:
            raise FormatError('Number format error for %s "%s"\n' % (self.name, st))
        for i in match.groups():
            if i:
                return float(i)
        raise FormatError('Number match failed for %s "%s"\n' % (self.name, st))

class CommaNumberArg(NumberArg):
    def __init__(self, name, required=True):
        self.init(name, COMMA_NUMBER_RE, 1, required)
        
class OptionalGtArg(NumberArg):
    def __init__(self, name, required=False):
        self.init(name, OPTIONAL_GT_NUMBER_RE, 1, required)
        
class OptionalLtArg(NumberArg):
    def __init__(self, name, required=False):
        self.init(name, OPTIONAL_LT_NUMBER_RE, 1, required)
        
class MatchAllArg(Arg):
    def __init__(self):
        self.init('text', NON_TERM_STR, 0, False)
        
class LabelArg(Arg):
    def __init__(self, name, required=True):
        self.init(name, LABEL_RE, 1, required)
        
class AxiiArg(Arg):
    def __init__(self, name, required=True):
        self.init(name, "([A-Za-z,]+)", 1, required)
 
    def parse(self, groups):
        if len(groups) != 1:
            raise InternalError('Axes parsing expecting 1 group for ' + self.name)
        st = groups[0]
        if not st:
            if self.required:
                raise FormatError('Missing required arg ' + self.name)
            return None
        if st == 'XY' or st == 'X,Y':
            return (0, 1)
        if st == 'YX' or st == 'Y,X':
            return (1, 0)
        if st == 'S':
            return (2,)
        
        raise FormatError('Unsupported axes defined ' + self.name)
        
class QueryArg(Arg):
    def __init__(self):
        self.init('query', "(?:\\s*(\\??))?\\s*", 1, False)
        
class BitMaskArg(Arg):
    def __init__(self, name):
        self.init(name, "\\s*([01]+)?", 1, True)

class Syntax(object):
    """ Defines a syntax. In the DMC language some constructs (REM) must
    occur at the beginning of the line.
    regex : The regular expression that matches the beginning of the construct.
    bol_only : indicates that this can only be matched a the beginning of a line.
    name : Optional name if the regex can't be used.
    terminator : What must be found to end the construct, usually a \n or ';'
    """
    def __init__(self, command, *args, **kwds):
        self.name = kwds.pop('name', command)
        terminator = kwds.pop('terminator', TERMINATOR)
        self.args = args
        regex = command
        for arg in args:
            regex = regex + arg.regex
        regex = regex + terminator
        self.re = regex
        self.bol_only = kwds.pop('bol_only', False)
        if kwds:
            raise InternalError("Extra arguments to Syntax constructor %r" % kwds)
        self.group_count = -1
        
    def parse_args(self, command):
        group_index = 0
        for arg in self.args:
            if arg.group_count:
                value = None
                try:
                    value = arg.parse(
                            command.groups[group_index + 1:(group_index + arg.group_count + 1)])
                except FormatError as e:
                    command.raiseFormatError(arg, e)
                setattr(command, arg.name, value)
                group_index += arg.group_count

class Command(object):
    """Command is an instance of a DMC "command". These specify how to parse
    the command from the input.
    """
    def __init__(self, groups, input_str, pos, lineno):
        self.groups = groups
        self.input_str = input_str
        self.pos = pos
        self.lineno = lineno
        self.__class__.SYNTAX.parse_args(self)
        self.commandName = "do" + self.__class__.__name__
        
    def raiseFormatError(self, arg, ex):
        raise QliSyntaxError(self.input_str, self.pos, lineno=self.lineno, formaterr=ex)
    
class RemComment(Command):
    SYNTAX = Syntax("REM", MatchAllArg(), bol_only=True)
        
class QuoteComment(Command):
    SYNTAX = Syntax("'|\"", MatchAllArg(), name='quote')  # A single ' or " to the end of line.
        
class NeedleOn(Command):
    SYNTAX = Syntax("NO NEEDLE ON", MatchAllArg(), name='needle_on')
    
class NeedleOff(Command):
    SYNTAX = Syntax("NO NEEDLE OFF", MatchAllArg(), name='needle_off')
    
class NoOperation(Command):
    SYNTAX = Syntax("NO", MatchAllArg())
        
class Label(Command):
    SYNTAX = Syntax('#', LabelArg('label'), name='label')

class ClearSequence(Command):
    SYNTAX = Syntax("CS")

class VectorMotion(Command):
    SYNTAX = Syntax("VM", AxiiArg('axes'))

class Circle(Command):
    SYNTAX = Syntax("CR", NumberArg('radius'), CommaNumberArg('start_angle'),
                    CommaNumberArg('angle_range'), OptionalLtArg('speed'),
                    OptionalGtArg('o'))

class VectorPosition(Command):
    SYNTAX = Syntax("VP", NumberArg('d1'), CommaNumberArg('d2'),
                    OptionalLtArg('speed'), OptionalGtArg('o'))
        
class WW(Command):
    SYNTAX = Syntax("WW", NumberArg('unk1'), CommaNumberArg('unk2'),
                    CommaNumberArg('unk3'))
        
class AN(Command):
    SYNTAX = Syntax("AN", NumberArg('unk1', required=False), CommaNumberArg('unk2', required=False),
                    CommaNumberArg('unk3', required=False))

class VectorSequenceEnd(Command):
    SYNTAX = Syntax("VE", QueryArg())

class Begin(Command):
    SYNTAX = Syntax("BG", AxiiArg('axes'))
        
class End(Command):
    SYNTAX = Syntax("EN", BitMaskArg('mask'))
        
class AfterMove(Command):
    SYNTAX = Syntax("AM", AxiiArg('axes'))
        
class AssignVariable(Command):
    SYNTAX = Syntax("([A-Za-z0-9]+)=", MatchAllArg(), name='assign')
        
class EmptyLine(Command):
    SYNTAX = Syntax("", name='empty')
        
class UnicodeBom(Command):
    # Some files contain a UTF8 BOM character which technically is illegal but some unicode
    # conversions incorrectly insert them. Let's eat them and ignore them.
    SYNTAX = Syntax("\xEF\xBB\xBF", name='unicode_bom', terminator='')
        
# A list of all regognized DMC commands. Add more as needed.
# Note that the QliRunner class must have a do<Class Name>() function for each element
# in this list.  When run, the functions are called.
# Because of the way we parse, we need the most commonly used commands at the front
# to make the parsing most efficient.
COMMANDS = [
    Circle,
    VectorPosition,
    RemComment,
    QuoteComment,
    NeedleOn,
    NeedleOff,
    NoOperation,
    Label,
    ClearSequence,
    VectorMotion,
    VectorSequenceEnd,
    Begin,
    AfterMove,
    End,
    WW,
    AN,
    AssignVariable,
    EmptyLine,
    UnicodeBom]


class ScannerMapper:
    """ Maps commands from regular expressions.
    """
    def __init__(self):
        self.regex = ""
        self.group_map = []
        self.compiled_re = None
        
    def add_term(self, command):
        next_regex = self.regex + ('|' if self.regex else '') + '(' + command.SYNTAX.re + ')'
        self.compiled_re = re.compile(next_regex)
        if not self.compiled_re or not self.compiled_re.groups > len(self.group_map):
            raise InternalError("Bad regex definition for %s" % command.__name__)
        # Extend the map to contain the new commands
        group_count = (self.compiled_re.groups - len(self.group_map))
        command.SYNTAX.group_count = group_count
        self.group_map.extend([command] * group_count)
        self.regex = next_regex
        
class QliScanner:
    """Scanner for a QLI string.
    """
    def __init__(self, commands):
        self.bol_mapper = ScannerMapper()
        self.mapper = ScannerMapper()
        self.next_group = 0
        for command in commands:
            self.bol_mapper.add_term(command)
            if not command.SYNTAX.bol_only:
                self.mapper.add_term(command)

    def scan(self, input_str, lineno=None):
        """Performs scanning of a QLI string. This may be a single line in a file
        or the entire contents of the file returning a list of commands.
        input_str: The string to parse.
        lineno: Optional line number to report for this string.
        """
        pos = 0
        bol = True
        result = []
        while pos < len(input_str):
            mapper = self.bol_mapper if bol else self.mapper
            match = mapper.compiled_re.match(input_str, pos)
            if not match:
                raise QliSyntaxError(input_str, pos, lineno=lineno)
            for index, group in enumerate(match.groups()):
                if group:
                    command = mapper.group_map[index]
                    group_count = command.SYNTAX.group_count
                    groups = match.groups()[index : index + group_count]
                    result.append(command(groups, input_str, pos, lineno))
                    bol = groups[0][-1] == '\n'
                    if bol and lineno != None:
                        lineno += 1
                    pos += len(groups[0])
                    break
        return result

SCANNER = QliScanner(COMMANDS)

class Qli:
    """Represents the parsed contents of a QLI file.
    """
    def __init__(self, inputvalue=None):
        self.commands = []
        if inputvalue:
            self.parse(inputvalue)
 
    def parse(self, inputvalue):
        """Parses a file like object."""
        if isinstance(inputvalue, str):
            self.commands.extend(SCANNER.scan(input))
        else:
            for lineno, line in enumerate(inputvalue):
                if line[-1] != '\n':
                    line += '\n'
                self.commands.extend(SCANNER.scan(line, lineno=lineno))


class QliRunner(object):
    """A QliProgram will use methods in this class to "execute" the program. Override
    these methods for application specific behaviour.
    """
    
    def __init__(self, program):
        self.program = program
        self.program_index = 0
        
    def run(self):
        self.program.execute(self)
        
    def doCircle(self, index, command):
        pass
    
    def doVectorPosition(self, index, command):
        pass
    
    def doRemComment(self, index, command):
        pass
    
    def doQuoteComment(self, index, command):
        pass
    
    def doNoOperation(self, index, command):
        pass
    
    def doNeedleOn(self, index, command):
        pass
    
    def doNeedleOff(self, index, command):
        pass
    
    def doLabel(self, index, command):
        pass
    
    def doClearSequence(self, index, command):
        pass
    
    def doVectorMotion(self, index, command):
        pass
    
    def doVectorSequenceEnd(self, index, command):
        pass
    
    def doBegin(self, index, command):
        pass
    
    def doAfterMove(self, index, command):
        pass
    
    def doEnd(self, index, command):
        pass
    
    def doWW(self, index, command):
        pass
    
    def doAN(self, index, command):
        pass
    
    def doEmptyLine(self, index, command):
        pass
    
    def doAssignVariable(self, index, command):
        pass
    
    def doUnicodeBom(self, index, command):
        pass

class ExecutionException(Exception):
    def __init__(self, message, e, tb):
        self.message = message
        self.e = e
        self.tb = tb
        
    def get_e(self):
        return self.e
    
    def get_tb(self):
        return self.tb
    
    def __str__(self, *args, **kwargs):
        return (self.message + '\n' 
                + '-' * 60 + '\n' 
                + str(self.e) 
                + '\n' + self.tb)
        

class QliProgram(QliRunner):
    """A 'compiled' version of the Qli.
    """
    def __init__(self, filename, qli):
        QliRunner.__init__(self, self)
        self.filename = filename
        self.qli = qli
        self.labels = {}
        # Collect labels by executing.
        self.execute(self)
        
    def execute(self, executor):
        # Execute this runner.
        try:
            executor.program_index = 0
            while executor.program_index < len(self.qli.commands):
                command = self.qli.commands[executor.program_index]
                index = executor.program_index
                executor.program_index += 1
                func = getattr(executor, command.commandName)
                func(index, command)
        except Exception as e:
            raise ExecutionException('file: "' + self.filename + '"', e, traceback.format_exc())
    
    def doLabel(self, index, command):
        self.labels[command.label] = index
    

class QliExecutor(QliRunner):
    
    def __init__(self, program):
        QliRunner.__init__(self, program)
        
        