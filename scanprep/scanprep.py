import argparse
import fitz
from PIL import Image, ImageFilter, ImageEnhance, ImageStat
import numpy as np
import os
import pathlib
from pyzbar.pyzbar import decode
import pytesseract

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
        print(f"P. {pagenumber} Ratio: {ratio:.5f}")

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
        print(f"P. {pagenumber} Empty by image: {empty_by_image}")
        print(f"P. {pagenumber} Text-Length: {len(page_text)}")

    return empty_by_image and len(page_text.strip()) == 0

# Check if the page is a separator by looking for a barcode with the value 'SCANPREP_SEP'.
def page_is_separator(img, pagenumber=None):
    detected_barcodes = decode(img)
    for barcode in detected_barcodes:
        if barcode.data == b'SCANPREP_SEP':
            if debug:
                print(f"P. {pagenumber} Separator detected.")
            return True
    if debug:
        print(f"P. {pagenumber} No separator detected.")
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

def get_new_docs_pages(doc, separate=True, remove_blank=True):
    docs = [[]]

    for page in doc:
        pixmap = page.get_pixmap()
        img = Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)
        page_text = page.get_text("text")

        if separate and page_is_separator(img, page.number +1):
            docs.append([])
            continue
        if remove_blank and page_is_empty(img, page_text, page.number +1):
            continue

        docs[-1].append(page.number)

    return list(filter(lambda d: len(d) > 0, docs))

def emit_new_documents(doc, filename, out_dir, separate=True, remove_blank=True):
    pathlib.Path(out_dir).mkdir(parents=True, exist_ok=True)

    new_docs = get_new_docs_pages(doc, separate, remove_blank)
    for i, pages in enumerate(new_docs):
        new_doc = fitz.open()  # Will create a new, blank document.
        for j, page_no in enumerate(pages):
            new_doc.insert_pdf(doc, from_page=page_no, to_page=page_no, final=(j == len(pages) - 1))
        new_doc.save(os.path.join(out_dir, f"{i}-{filename}"))

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
    parser.add_argument('input_pdf', help='The PDF document to process.')
    parser.add_argument(
        'output_dir', help='The directory where the output documents will be saved. (defaults to the current directory)', nargs='?', default=os.getcwd())
    parser._add_action(ActionNoYes('page-separation', 'separate',
                                   help='Do (or do not) split document into separate files by the included separator pages. (default yes)'))
    parser._add_action(ActionNoYes('blank-removal', 'remove_blank',
                                   help='Do (or do not) remove empty pages from the output. (default yes)'))
    args = parser.parse_args()

    emit_new_documents(fitz.open(os.path.abspath(args.input_pdf)), os.path.basename(
        args.input_pdf), os.path.abspath(args.output_dir), args.separate, args.remove_blank)

if __name__ == '__main__':
    main()
