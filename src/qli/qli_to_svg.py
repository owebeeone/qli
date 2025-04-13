"""
Converts from Statler Stitcher Gammill® QLI files to SVG format.

Gammill QLI files are a subset of the Galil DMC language. This script decodes
a small subset of the language and "runs" these programs to generate SVG files.

This script is capable of converting a single file or a whole directory of 
files.

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

import argparse
import os
from qli import qli_parser
from qli import qli_svg
from qli import value_type
import re
import sys
import textwrap
import traceback
import subprocess

EXAMPLE_USAGE = """
To convert a single file from qli format to svg:
  {0} a-file.qli
  a-file.svg will be created.
  
To convert an entire directory hierarchy of qli files:
  {0} --recursive --continue_on_error a-directory
  All files named .qli will have a new file with the suffix replaced with .svg
  
To remove the border on the generated files:
  {0} --borders '' a-file.qli
  
To place the border on the shape extents:
  {0} --borders 'green:0' a-file.qli
  
To add two borders:
  {0} --borders 'blue:1,red:0' a-file.qli
  The second border will be drawn directly on the shape extents.
  
To additionally convert to to a jpeg image:
  {0} --raster_out png a-file.qli
  The raster out parameter is a comma separated list of a 4 tuple.
      type:<convert parameters>:<file format>:<out directory format>
  
Produce SVG with no margin or border and double wide lines:
  {0} --margin 0x0 --borders '' --line_width 2 a-file.qli
  The resulting file will have no border.
  
""".format(sys.argv[0])


DEFAULT_OUT_PATH_FORMAT='{path_name}'
DEFAULT_OUT_FORMAT='{base_name}.svg'
DEFAULT_FILE_EXTENSION='qli'

class RasterParams(value_type.ValueSpec):
    """Defines parameters for creating raster images using ImageMagick convert."""
    VALUE_DELIMITER = ':'
    FIELDS = (value_type.ValueField('raster_type', str, 'jpg', 'Raster output type'),
              value_type.ValueField('convert_args', str, '', 'Args to convert'),
              value_type.ValueField('file_name', str, '{base_name}.{raster_type}', 
                                    'Output file name pattern'),
              value_type.ValueField('out_dir', str, '{path_name}', 
                                    'The output directory for this type.'))

class RasterParamsList(value_type.ListSpec):
    LIST_SEPARATOR = ','
    LIST_TYPE = RasterParams

class ConvertParams(value_type.ValueSpec):
    """Conversion parameters class as a simple value type.
    """
    VALUE_DELIMITER = '|'
    FIELDS = (value_type.ValueField('recursive', bool, False, 
                                    'Perform recursive scan on directories.'),
              value_type.ValueField('continue_on_error', bool, False, 
                                    'Ignore parsing errors and omit the offending file.'),
              value_type.ValueField('out_dir', str, DEFAULT_OUT_PATH_FORMAT, 
                                    'Output directory format.'),
              value_type.ValueField('out_name', str, DEFAULT_OUT_FORMAT, 
                                    'Output file name format.'),
              value_type.ValueField('suffix', str, DEFAULT_FILE_EXTENSION, 
                                    'Suffix filter for recursive search.'),
              value_type.ValueField('print_progress', bool, False, 
                                    'Show progress of parsing.'),
              value_type.ValueField('raster_image', None, str, 
                                    'Add conversion to .'),
              value_type.ValueField('raster_out', RasterParamsList, '',
                                    'Comma separated list of raster types to generate')
              )

def readQliFile(filename):
    """Reads a QLI file and returns a tuple of (program, error).
    """
    f = None
    if filename == '-':
        f = sys.stdin
        sys.stderr.write("No file provided, reading from standard input:\n")
    else:
        f = open(filename, 'r')
        if not f:
            sys.stderr.write("failed to open %s" % filename)
            return None

    try:
        return qli_parser.QliProgram(filename, qli_parser.Qli(f)), None
    except qli_parser.QliSyntaxError as e:
        sys.stderr.write("File: %s %s" % (filename, e))
        return None, e

# group 1:path, 2:basename, 3:extension
FILE_NAME_RE = re.compile("(?:(.*[^/]|)/+)?([^/]*)(\\.[^\\./]*)")

def processQli(filename, prog, outname, svg_out_params=qli_svg.SvgOutputParams(), 
               convert_params=ConvertParams()):
    """Process a Qli program for generating SVG data.
    """
    try:
        converter = qli_svg.QliSvgExecutor(prog)
        if convert_params.print_progress:
            sys.stderr.write("%s: program extents %s\n" % (
                    filename, repr(converter.extents.get_extents())))
        converter.run()
        
        # Ensure the file is created.
        match = FILE_NAME_RE.match(outname)
        if not match:
            raise Exception("Unable to parse filename %s" % filename)
        
        dir, basename, extension = match.groups()
        if dir and not os.path.isdir(dir):
            os.makedirs(dir)
        if filename == "-":
            f = sys.stdout
        else:
            f = open(outname, 'w')
        converter.pattern.write_svg(f, svg_out_params)
        f.close()
        
        return True
    except:
        traceback.print_exception(*sys.exc_info())
        return False

def find_recursive(dir, suffix):
    """Returns a list of files matching the given filter."""
    suffix_matcher = re.compile(".*" + suffix + "$", re.IGNORECASE)
    result = []
    for (dirpath, dirnames, filenames) in os.walk(dir):
        for filename in filenames:
            if suffix_matcher.match(filename):
                result.append('/'.join((dirpath, filename)))
    return result

def error_exit(message):
    """Quick error exit."""
    sys.stderr.write(message)
    sys.stderr.write("\nEXIT\n")
    sys.exit(1)

def make_outfile_name(filename, dir_format, file_format, **kwds):
    """Creates an output filename from in input filename and format
    strings for directory and file and miscellaneous other parameters.
    """
    match = FILE_NAME_RE.match(filename)
    if not match:
        raise Exception("Unable to parse filename %s" % filename)
    
    local_params = {
        'path_name' : '.' if match.groups()[0] is None else match.groups()[0],
        'base_name' : match.groups()[1],
        'extension' : match.groups()[2]}
    
    params = qli_svg.merge_dicts(local_params, kwds)
    
    return '/'.join((dir_format.format(**params), file_format.format(**params)))


def generate_raster(outsvg_name, original_filename, convert_params):
    for raster_params in convert_params.raster_out:
        raster_name = make_outfile_name(original_filename, raster_params.out_dir,
                raster_params.file_name, raster_type=raster_params.raster_type)
        
        params = raster_params.convert_args.split(' ') if raster_params.convert_args else []
        
        command = [ "convert" ] + params + [ outsvg_name, raster_name]
        
        if subprocess.call(command):
            command_str = '"%s"' % '" "'.join(command)
            sys.stderr.write("Raster processing failed : %s\n" % command_str)

def main(argv):
    parser = argparse.ArgumentParser(
            formatter_class=argparse.RawDescriptionHelpFormatter,
            description='Convert QLI pattern files to SVG.',
            epilog=textwrap.dedent(EXAMPLE_USAGE))
    
    svg_out_params = qli_svg.SvgOutputParams()
    svg_out_params.add_parser_args(parser)
    
    convert_params = ConvertParams()
    convert_params.add_parser_args(parser)

    parser.add_argument('inputs', metavar='<file>', type=str, nargs='*',
                   help='input files')
               
    args = parser.parse_args() 
    svg_out_params.set_parsed_args(args)
    convert_params.set_parsed_args(args)
    
    filenames = args.inputs if args.inputs else ['-']
    # Make a reversed copy, better for large lists.
    stack = filenames[::-1]
    
    try:
        filename = ""
        errors = []
        while stack:
            filename = stack.pop()
            if os.path.isdir(filename):
                if args.recursive:
                    stack = find_recursive(filename, args.suffix)[::-1] + stack
                    continue
                else:
                    return error_exit('cannot convert directory: use --recursive to walk directories')
            prog, e = readQliFile(filename)
            if e and args.continue_on_error:
                errors.append((filename, e))
            elif e:
                sys.stderr.write(str(e))
                return 1
            else:
                outname = outname=make_outfile_name(filename, args.out_dir, args.out_name)
                if not processQli(
                        filename=filename,
                        prog=prog,
                        outname=outname,
                        svg_out_params=svg_out_params,
                        convert_params=convert_params):
                    return 1
                generate_raster(outname, filename, convert_params)

    except KeyboardInterrupt as e:
        sys.stderr.write('\n\n')
        traceback.print_exc()
        # If the code gets stuck, it's good to know which file it was stuck on.
        sys.stderr.write('\nInterrupted at file: %s\n\n' % filename)
        return 1
    if errors:
        return error_exit('Some files failed conversion.')
    return 0


if __name__ == "__main__":
    exit(main(sys.argv))
