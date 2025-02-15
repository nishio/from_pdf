"""
from PDF to Scrapbox

"""

import os
import argparse
import subprocess
import requests
import re
import json
from tqdm import tqdm
from time import sleep, time

parser = argparse.ArgumentParser(description="from PDF to Scrapbox")
parser.add_argument(
    "--in-file", "--in", "-i", type=str, help="input PDF file", required=False
)
parser.add_argument(
    "--resolution",
    "-r",
    type=int,
    default=200,
    help="Resolution for the output. Default is 200.",
)
parser.add_argument(
    "--format",
    "-f",
    type=str,
    default="jpeg",
    choices=["jpeg", "png"],
    help="Output format. Default is 'jpeg'.",
)
parser.add_argument("--in-dir", type=str, default="in", help="input PDF directory")
parser.add_argument("--out-dir", type=str, default="out", help="output directory")
parser.add_argument("--retry", action="store_true", help="retry")
parser.add_argument(
    "--skip-gyazo", action="store_true", help="Skip Gyazo Upload and OCR"
)
parser.add_argument(
    "--skip-gyazo-upload", action="store_true", help="Skip Gyazo Upload"
)
parser.add_argument(
    "--skip-pdf-to-image", action="store_true", help="Skip PDF to Image process"
)
# Gyazo sometimes returns 429 error (Too many requests) for long time. In the case, we want to continue other processes first.
parser.add_argument(
    "--recovery", action="store_true", help="Recovery mode after 429 error"
)
parser.add_argument(
    "--filter", action="store_true", help="filter PDFs that are alreadt processed"
)

args = parser.parse_args()


import dotenv

dotenv.load_dotenv()
GYAZO_TOKEN = os.getenv("GYAZO_TOKEN")


def upload_one_image_to_gyazo(image_name, directory):
    """
    Uploads a single image to Gyazo.

    Args:
    - image_name (str): The name of the image file to upload.
    - directory (str): The directory containing the image file.

    Returns:
    - dict: The JSON object returned from the Gyazo API.
    """
    url = "https://upload.gyazo.com/api/upload"
    headers = {"Authorization": f"Bearer {GYAZO_TOKEN}"}
    image_path = os.path.join(directory, image_name)
    files = {"imagedata": (image_name, open(image_path, "rb"))}
    while True:
        try:
            res = requests.post(url, headers=headers, files=files)
        except Exception as e:
            if not args.retry:
                raise
            print(f"Unknown Exception on uploading images: {e}")
            print(f"Retry after 30 sec...")
            sleep(30)
            continue

        if res.status_code == 200:
            return res.json()
        if res.status_code == 502 and "Please try again in 30 seconds" in res.text:
            sleep(30)
            continue
        if not args.retry:
            raise Exception(f"Failed to upload image({res.status_code}): {res.text}")
        sleep_half_day_if_too_many_requests(res)
        if "Not an Image" in res.text:
            # Not sure why this happens
            # add this and tried again, but the error not happen again.
            # raise Exception(f"Not an Image: {image_path}")
            print(f"Not an Image: {image_path}")
            print(f"Retry after 30 sec...")
            sleep(30)
            continue

        print(f"Unknown error({res.status_code}): {res.text}")
        print(f"Retry after 30 sec...")
        sleep(30)


def get_images(directory):
    return [
        f for f in os.listdir(directory) if f.endswith(f".jpg") or f.endswith(f".png")
    ]


def run_pdftocairo(input_pdf, output_directory, resolution=200, format="jpeg"):
    """
    Runs pdftocairo on the given input PDF to convert it to specified format.

    Args:
    - input_pdf (str): The path to the input PDF.
    - output_directory (str): The directory where the output should be saved.
    - resolution (int, optional): The resolution for the output. Default is 200.
    - format (str, optional): The output format ('jpeg', 'png', etc.). Default is 'jpeg'.

    Returns:
    None
    """
    # If already have images, skip
    image_files = get_images(output_directory)
    if image_files:
        print(
            f"Skip run_pdftocairo for {input_pdf} because already have {len(image_files)} images."
        )
        return

    # Extract the base name from the input PDF path
    base_name = os.path.basename(input_pdf)
    file_name_without_ext = os.path.splitext(base_name)[0]

    # Ensure the output directory exists
    os.makedirs(output_directory, exist_ok=True)

    # Construct the pdftocairo command
    cmd = [
        "pdftocairo",
        "-r",
        str(resolution),
        "-" + format,
        input_pdf,
        os.path.join(output_directory, file_name_without_ext),
    ]

    # Execute the command
    subprocess.run(cmd, check=True)
    # If `Syntax Error: Document stream is empty` occured, possible reason is the PDF is on Dropbox and not offline mode


def upload_images_to_gyazo(directory, ext="jpg"):
    """
    Uploads all images in the given directory to Gyazo.

    Args:
    - directory (str): The directory containing the images to upload.

    Returns:
    None
    """
    # Get all image files in the directory
    image_files = get_images(directory)
    print(f"DIR: {directory}, \nNum images: {len(image_files)}")

    # Local storage for Gyazo URLs
    json_path = os.path.join(directory, "gyazo_info.json")
    gyazo_info = json.load(open(json_path)) if os.path.exists(json_path) else []
    if len(gyazo_info) == len(image_files):
        print(f"Skip it because already uploaded all images.")
        return

    # 1: Sort the image files by index
    # Images may be `page-99.jpg` and `page-100.jpg`, so we need to sort by the page number.
    # Page number is continuous number before the last period.

    # Extract numbers to sort the images by index
    image_files = sorted(image_files, key=lambda x: int(re.findall(r"(\d+)", x)[-1]))

    # 2: Upload each image to Gyazo
    # Each upload returns a JSON object with the URL to the uploaded image.
    # We want to store them in a local JSON file for later use.
    # Save after each API call so that we don't lose data if the script crashes.

    # Local storage for Gyazo URLs
    not_uploaded_images = image_files[len(gyazo_info) :]
    for image_file in tqdm(not_uploaded_images):
        res = upload_one_image_to_gyazo(image_file, directory)
        res["local_filename"] = image_file

        # Append the returned JSON to the gyazo_info list
        gyazo_info.append(res)

        # Save URLs to local JSON after each upload
        with open(json_path, "w") as f:
            json.dump(gyazo_info, f, indent=2)


# def quit_if_too_many_requests(res):
#     if res.status_code == 429:
#         # (429): {"message":"You have fired too many requests. Please wait for some time."}
#         # Gyazo API Quota: 12500 API calls per day
#         # Retrying won't help, so just quit.
#         raise Exception(f"Too many requests")


def sleep_half_day_if_too_many_requests(res):
    if res.status_code == 429:
        print("Too many requests. Sleep half day.")
        sleep(12 * 60 * 60)


def get_gyazo_info(image_id):
    GYAZO_API_ROOT = "https://api.gyazo.com/api"
    while True:
        res = requests.get(
            f"{GYAZO_API_ROOT}/images/{image_id}",
            headers={"Authorization": f"Bearer {GYAZO_TOKEN}"},
        )
        if res.status_code == 200:
            return res.json()
        if not args.retry:
            raise Exception(f"Failed to upload image({res.status_code}): {res.text}")
        sleep_half_day_if_too_many_requests(res)
        sleep(1)


def get_ocr_texts(directory):
    """
    Read `gyazo_info.json` and get OCR text from Gyazo API.
    """
    print(f"Getting OCR texts for {directory}...")
    json_path = os.path.join(directory, "gyazo_info.json")
    with open(json_path) as f:
        gyazo_info = json.load(f)

    image_files = get_images(directory)
    if len(gyazo_info) != len(image_files):
        print(f"Skip it because not uploaded all images.")
        return

    for info in tqdm(gyazo_info):
        if "ocr_text" in info:
            # already OCR-ed
            continue
        image_id = info["image_id"]
        res = get_gyazo_info(image_id)
        if "ocr" in res:
            info["ocr_text"] = res["ocr"]["description"]
            with open(json_path, "w") as f:
                json.dump(gyazo_info, f, indent=2, ensure_ascii=False)
        else:
            print(f"OCR not available for image_id={image_id}")
            # should wait and retry?
            # raise Exception("OCR not available")
            info["ocr_text"] = "OCR not available"
            with open(json_path, "w") as f:
                json.dump(gyazo_info, f, indent=2, ensure_ascii=False)


def filename_to_outdir(in_file):
    # Split the file path to get only the file name without extension
    base_name = os.path.basename(in_file)  # gets "foo.pdf"
    file_name_without_ext = os.path.splitext(base_name)[0]  # gets "foo"

    # Create the new directory path
    out_dir = os.path.join(args.out_dir, file_name_without_ext)
    return out_dir


def process_one_pdf(in_file):
    out_dir = filename_to_outdir(in_file)

    # Make the directory. The exist_ok=True ensures that the function doesn't
    # raise an error if the directory already exists.
    os.makedirs(out_dir, exist_ok=True)

    # Run pdftocairo to convert the PDF to images
    # (in future it may be option to use pdfimages)
    run_pdftocairo(in_file, out_dir, args.resolution, args.format)

    upload_images_to_gyazo(out_dir)

    get_ocr_texts(out_dir)  # may cause "no OCR" error

    make_scrapbox_json(out_dir)


def make_scrapbox_json(directory):
    """
    Read `gyazo_info.json` and make Scrapbox JSON.
    """
    json_path = os.path.join(directory, "gyazo_info.json")
    if not os.path.exists(json_path):
        print(f"Skip it because gyazo_info.json not exists.")
        return
    with open(json_path) as f:
        gyazo_info = json.load(f)

    print(f"Making Scrapbox JSON for {directory}...")
    title = os.path.split(directory)[-1]

    image_files = get_images(directory)
    if len(gyazo_info) != len(image_files):
        print(f"Skip it because not uploaded all images.")
        return

    # Concatenate images and the OCR texts into a scrapbox page.
    # Due to the Scrapbox accepts only 10000 lines per page,
    # we need to split the pages.
    scrapbox_pages = []
    page_count = 1

    def add_page(page_lines):
        nonlocal page_count
        new_title = title
        if page_count > 1:
            new_title += f" ({page_count})"
        page_lines[0] = new_title
        scrapbox_pages.append({"title": new_title, "lines": page_lines})
        page_count += 1

    page_lines = [title]
    image_lines = []

    for i, page in enumerate(gyazo_info):
        image_lines.append(f"[{page['permalink_url']}]")  # add image
        if "ocr_text" in page:
            page_lines.extend(page["ocr_text"].split("\n"))  # add text
        if (i + 1) % 50 == 0:
            add_page(page_lines + image_lines)
            page_lines = [title]
            image_lines = []

    if page_lines != [title]:
        add_page(page_lines + image_lines)
    # Make the JSON
    scrapbox_json = {"pages": scrapbox_pages}

    # Save the JSON
    out_path = os.path.join(directory, "scrapbox.json")
    with open(out_path, "w") as f:
        json.dump(scrapbox_json, f, indent=2, ensure_ascii=False)


def get_pdfs_in_dir():
    # Get all PDF files in the input directory
    INDIR = args.in_dir
    pdf_files = [
        os.path.join(INDIR, f) for f in os.listdir(INDIR) if f.endswith(".pdf")
    ]
    pdf_files.sort()
    return pdf_files


def process_pdfs():
    """
    This process is suitable when those PDFs will fit in quota.
    OCR takes time, so we upload all images first.

    We need better way to handle PDFs that exceed the quota.(TODO)
    Because uploading cunsume all quota and we can't get OCR texts.
    """
    # record start time
    start_time = time()
    # Get all PDF files in the input directory
    pdf_files = get_pdfs_in_dir()
    print(f"Num PDF files: {len(pdf_files)}")

    # Process each PDF file
    targets = []
    print("# Convert PDF to images and Upload to Gyazo")
    for in_file in tqdm(pdf_files):
        out_dir = filename_to_outdir(in_file)
        # Make the directory. The exist_ok=True ensures that the function doesn't
        # raise an error if the directory already exists.
        os.makedirs(out_dir, exist_ok=True)

        if not args.skip_pdf_to_image:
            print(f"From `{in_file}` to images...")
            run_pdftocairo(in_file, out_dir, args.resolution, args.format)
        targets.append(out_dir)
        if not (args.skip_gyazo or args.skip_gyazo_upload):
            upload_images_to_gyazo(out_dir)

    print("# Get OCR texts")
    if not args.skip_gyazo:
        for target in targets:
            get_ocr_texts(target)

    print("# Make Scrapbox JSON")
    for target in targets:
        make_scrapbox_json(target)

    print("# Make Total Scrapbox JSON")
    make_total_scrapbox_json(targets)

    # print elapsed time
    elapsed_time = time() - start_time
    print("time: {0}".format(elapsed_time) + "[sec]")


def recovery():
    """
    Recovery after "too many requests" error.
    Process "work in progress" PDFs only.
    """
    # Get all PDF files in the input directory
    pdf_files = get_pdfs_in_dir()

    # Process each PDF file
    targets = []
    for in_file in tqdm(pdf_files):
        target = filename_to_outdir(in_file)
        if not os.path.exists(target):
            # it is not processed yet, no WIP, so skip
            continue

        image_files = get_images(target)
        if not image_files:
            # no images, so no WIP API calls. skip
            continue

        # Local storage for Gyazo URLs
        json_path = os.path.join(target, "gyazo_info.json")
        gyazo_info = json.load(open(json_path)) if os.path.exists(json_path) else []
        if len(gyazo_info) != len(image_files):
            # some images are not uploaded
            print("Uploading", target)
            upload_images_to_gyazo(target)

        print("Get OCR", target)
        get_ocr_texts(target)
        make_scrapbox_json(target)

    make_total_scrapbox_json([filename_to_outdir(p) for p in pdf_files])


def make_total_scrapbox_json(targets):
    total_pages = []
    data = {"pages": total_pages}
    for target in targets:
        json_path = os.path.join(target, "scrapbox.json")
        if not os.path.exists(json_path):
            continue
        with open(json_path) as f:
            pages = json.load(f)["pages"]
            total_pages.extend(pages)
    with open(os.path.join(args.out_dir, "total_scrapbox.json"), "w") as f:
        json.dump(data, f, indent=2)


def filter():
    """
    filter PDFs that are alreadt processed
    """
    done_dir = args.in_dir + "_done"
    os.makedirs(done_dir, exist_ok=True)

    # Get all PDF files in the input directory
    pdf_files = get_pdfs_in_dir()

    # Process each PDF file
    targets = []
    for in_file in pdf_files:
        target = filename_to_outdir(in_file)
        scrapbox_json_path = os.path.join(target, "scrapbox.json")
        if os.path.exists(scrapbox_json_path):
            print("✅", target)
            targets.append(in_file)
        else:
            print("❌", target)

    for in_file in targets:
        out_file = done_dir + "/" + os.path.basename(in_file)
        os.rename(in_file, out_file)


def main():
    if args.in_file:
        process_one_pdf(args.in_file)
        return
    if args.filter:
        filter()
        return
    if args.recovery:
        recovery()
        return

    process_pdfs()


if __name__ == "__main__":
    main()
