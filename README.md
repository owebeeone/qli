# QLI SVG Converter

QLI provides a simple conversion of QLI format files to SVG files. 
QLI also supports conversion to raster file formats supported by
the ImageMagic "convert" tool.

QLI files are the predominant format for the Statler Stitcher by Gammill®. 
The QLI format defines a collection of stitching paths. The file format is 
a subset of the Galil DMC language, although, no official information
from Gammill has been made available.

This is provided in an open source format in the hope that someone else may
find this useful.

Feel welcome to raise issues at: https://github.com/owebeeone/qli/issues
  
I make no promise to look at them but I will, time permitting.  However raising
issues will likely get a response while emailing me directly will likely not.

## Installation

Install the package using pip:

```bash
pip install qli
```

You will need Python 3 and the `svg.path` Python package installed on 
your computer. `svg.path` will be installed automatically when you install `qli` via pip.

## Usage

To see the available options, run:

```bash
python -m qli.qli_to_svg --help
```

### Examples

**Convert a single file from QLI format to SVG:**

```bash
python -m qli.qli_to_svg a-file.qli
```
This will create `a-file.svg`.

**Convert an entire directory hierarchy of QLI files:**

```bash
python -m qli.qli_to_svg --recursive --continue_on_error a-directory
```
All files named `.qli` will have a new file with the suffix replaced with `.svg`.

**Remove the border on the generated files:**

```bash
python -m qli.qli_to_svg --borders '' a-file.qli
```

**Place the border on the shape extents:**

```bash
python -m qli.qli_to_svg --borders 'green:0' a-file.qli
```

**Add two borders:**

```bash
python -m qli.qli_to_svg --borders 'blue:1,red:0' a-file.qli
```
The second border will be drawn directly on the shape extents.

**Additionally convert to a PNG image:**

```bash
python -m qli.qli_to_svg --raster_out png a-file.qli
```
The `--raster_out` parameter is a comma-separated list. You can specify raster types like `png`, `jpeg`, etc., supported by ImageMagick's `convert` tool. For advanced usage involving `convert` parameters, refer to the `--help` output.

**Produce SVG with no margin or border and double wide lines:**

```bash
python -m qli.qli_to_svg --margin 0x0 --borders '' --line_width 2 a-file.qli
```
The resulting file will have no border.

### Command Line Options

```
usage: qli_to_svg.py [-h] [--oncolor ONCOLOR] [--offcolor OFFCOLOR] [--line_width LINE_WIDTH] [--margin MARGIN] [--width WIDTH] [--borders BORDERS]
                     [--recursive | --no-recursive] [--continue_on_error | --no-continue_on_error] [--out_dir OUT_DIR] [--out_name OUT_NAME]
                     [--suffix SUFFIX] [--print_progress | --no-print_progress] [--raster_image RASTER_IMAGE] [--raster_out RASTER_OUT]
                     [<file> ...]

Convert QLI pattern files to SVG.

positional arguments:
  <file>                input files

options:
  -h, --help            show this help message and exit
  --oncolor ONCOLOR     The color of the "on" path default: black
  --offcolor OFFCOLOR   The color of the "off" path default: red
  --line_width LINE_WIDTH
                        Bigger numbers means thicker lines default: 1.0
  --margin MARGIN       Margin around image default: 50x50
  --width WIDTH         The image width (inside margin). Aspect ratio is maintained. default: 700.0
  --borders BORDERS     Comma separated list of borders default: blue:1
  --recursive           Perform recursive scan on directories. default: False
  --no-recursive        See --recursive
  --continue_on_error   Ignore parsing errors and omit the offending file. default: False
  --no-continue_on_error
                        See --continue_on_error
  --out_dir OUT_DIR     Output directory format. default: {path_name}
  --out_name OUT_NAME   Output file name format. default: {base_name}.svg
  --suffix SUFFIX       Suffix filter for recursive search. default: qli
  --print_progress      Show progress of parsing. default: False
  --no-print_progress   See --print_progress
  --raster_image RASTER_IMAGE
                        Add conversion to . default: <class 'str'>
  --raster_out RASTER_OUT
                        Comma separated list of raster types to generate default: