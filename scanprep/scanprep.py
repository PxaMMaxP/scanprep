import argparse
import fitz
from PIL import Image, ImageFilter, ImageEnhance, ImageStat
import numpy as np
import os
import pathlib
from pyzbar.pyzbar import decode
import pytesseract
import sys
import tempfile
from io import BytesIO

# Enable/disable debug output.
debug = True

# Algorithm inspired by: https://dsp.stackexchange.com/a/48837
def page_is_empty_by_image(img, pagenumber=None, ratio_threshold=0.005):
    # Image should be in grayscale and binarized -> see `convert_img_to_grayscale_and_binarize`.
    # Staples, folds, punch holes et al. tend to be confined to the left and right margin, so we crop off 10% there.
    # Also, we crop off 5% at the top and bottom to get rid of the page borders.
    lr_margin = img.width * 0.10
    tb_margin = img.height * 0.05
    img = img.crop((lr_margin, tb_margin, img.width - lr_margin, img.height - tb_margin))

    # Use erosion and dilation to get rid of small specks but make actual text/content more significant.
    img = img.filter(ImageFilter.MaxFilter(1))
    img = img.filter(ImageFilter.MinFilter(3))

    white_pixels = np.count_nonzero(img)
    total_pixels = img.size[0] * img.size[1]
    ratio = (total_pixels - white_pixels) / total_pixels

    if debug:
        print(f"P. {pagenumber} Ratio: {ratio:.5f}", file=sys.stderr)

    return ratio < ratio_threshold

# Convert image to grayscale and binarize.
def convert_img_to_grayscale_and_binarize(img):
    threshold = np.mean(ImageStat.Stat(img).mean) - 50
    return img.convert('L').point(lambda x: 255 if x > threshold else 0)

# Brighten image up.
def brighten_image(img, factor=1.5):
    enhancer = ImageEnhance.Brightness(img)
    brightened_img = enhancer.enhance(factor)
    return brightened_img

# Summarizes the page detection by checking if it is empty or a separator.
def page_is_empty(img, page_text, pagenumber=None):
    img = brighten_image(img)
    img = convert_img_to_grayscale_and_binarize(img)

    if len(page_text) == 0:
        page_text = extract_text(img)

    if len(page_text) == 0:
        empty_by_image = page_is_empty_by_image(img, pagenumber, ratio_threshold=0.010)
    else:
        empty_by_image = page_is_empty_by_image(img, pagenumber)

    if debug:
        print(f"P. {pagenumber} Empty by image: {empty_by_image}", file=sys.stderr)
        print(f"P. {pagenumber} Text-Length: {len(page_text)}", file=sys.stderr)

    return empty_by_image or len(page_text.strip()) == 0

# Check if the page is a separator by looking for a barcode with the value 'SCANPREP_SEP'.
def page_is_separator(img, pagenumber=None):
    detected_barcodes = decode(img)
    for barcode in detected_barcodes:
        if barcode.data == b'SCANPREP_SEP':
            if debug:
                print(f"P. {pagenumber} Separator detected.", file=sys.stderr)
            return True
    if debug:
        print(f"P. {pagenumber} No separator detected.", file=sys.stderr)
    return False

# Extract text from the image using Tesseract OCR.
def extract_text(img):
    # Tesseract configuration for better results with scanned documents.
    custom_config = r'--oem 1 --psm 11 --dpi 300'
    text = pytesseract.image_to_string(img, lang="deu", config=custom_config)

    # Remove empty lines, all whitespace and non-alphanumeric characters.
    text = '\n'.join(filter(lambda l: len(l) > 0, text.split('\n')))
    text = ''.join(filter(lambda c: c.isalnum() or c.isspace(), text))

    return text

def get_new_docs_pages(doc, remove_blank=True):
    pages_to_keep = []

    for page in doc:
        pixmap = page.get_pixmap()
        img = Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)
        page_text = page.get_text("text")

        # if separate and page_is_separator(img, page.number + 1):
        #     docs.append([])
        #     continue
        if remove_blank and page_is_empty(img, page_text, page.number + 1):
            continue

        pages_to_keep.append(page.number)

    return pages_to_keep

def emit_new_document(doc, output_file=None, remove_blank=True):
    new_doc = fitz.open()  # Create a new, blank document.
    pages_to_keep = get_new_docs_pages(doc, remove_blank)

    for page_no in pages_to_keep:
        new_doc.insert_pdf(doc, from_page=page_no, to_page=page_no)

    if output_file:
        new_doc.save(output_file)
    else:
        pdf_bytes = new_doc.tobytes()
        sys.stdout.buffer.write(pdf_bytes)

# Taken from: https://stackoverflow.com/a/9236426
class ActionNoYes(argparse.Action):
    def __init__(self, opt_name, dest, default=True, required=False, help=None):
        super(ActionNoYes, self).__init__(['--' + opt_name, '--no-' + opt_name],
                                          dest, nargs=0, const=None, default=default, required=required, help=help)

    def __call__(self, p, namespace, values, option_string=None):
        if option_string.startswith('--no-'):
            setattr(namespace, self.dest, False)
        else:
            setattr(namespace, self.dest, True)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('input_pdf', nargs='?', type=argparse.FileType('rb'), default=sys.stdin.buffer, help='The PDF document to process. Use "-" or omit to read from stdin.')
    parser.add_argument('output_pdf', nargs='?', help='The output PDF file. If omitted or "-", output to stdout.')
    parser._add_action(ActionNoYes('blank-removal', 'remove_blank',
                                   help='Do (or do not) remove empty pages from the output. (default yes)'))
    args = parser.parse_args()

    # Read input PDF from stdin or file
    if args.input_pdf == sys.stdin.buffer:
        with tempfile.NamedTemporaryFile(delete=False) as tmp_pdf:
            tmp_pdf.write(sys.stdin.buffer.read())
            tmp_pdf_path = tmp_pdf.name
        input_doc = fitz.open(tmp_pdf_path)
        os.remove(tmp_pdf_path)  # Ensure the temporary file is deleted after use.
    else:
        input_doc = fitz.open(stream=args.input_pdf.read(), filetype="pdf")

    # Determine output destination
    if args.output_pdf in [None, '-']:
        emit_new_document(input_doc, None, args.remove_blank)
    else:
        emit_new_document(input_doc, args.output_pdf, args.remove_blank)

if __name__ == '__main__':
    main()
