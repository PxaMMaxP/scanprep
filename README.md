# scanprep – Prepare scanned PDF documents

> Small utility to prepare scanned documents. Supports separating PDF files by removing blank pages.

<!-- TODO: GIF showing how to use scanprep -->

Scanprep can be used to prepare scanned documents for further processing with existing tools (like the great [OCRmyPDF](https://github.com/jbarlow83/OCRmyPDF)) or directly for archival. It can remove blank pages from the output (this is especially helpful if using a duplex scanner).

## Installation

### From source

To install scanprep from source, clone this repository and install the dependencies:

```sh
git clone https://github.com/baltpeter/scanprep.git
cd scanprep
pip3 install -r requirements.txt # You may want to do this in a venv.
# You may also need to install the zbar shared library. See: https://pypi.org/project/pyzbar/

python3 scanprep/scanprep.py -h
```

### Docker

You can also use the provided Dockerfile to build a Docker image:

```sh
docker build -t scanprep .
```

You can then run scanprep via Docker:

```sh
docker run --rm -i scanprep - - <input.pdf >output.pdf
```

## Usage

Most simply, you can run scanprep via `scanprep.py - - <input.pdf >output.pdf`. This will process the input file on stdin and write the output to stdout.

Use `scanprep -h` to show the help:

```
usage: scanprep [-h] [--page-separation] [--blank-removal] input_pdf [output_dir]

positional arguments:
  input_pdf             The PDF document to process.
  output_dir            The directory where the output documents will be saved. (defaults to the
                        current directory)

optional arguments:
  -h, --help            show this help message and exit
  --blank-removal, --no-blank-removal
                        Do (or do not) remove empty pages from the output. (default yes)
```

## License

Scanprep is licensed under the MIT license, see the [`LICENSE`](/LICENSE) file for details. Issues and pull requests are welcome!