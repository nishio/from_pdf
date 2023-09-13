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

parser = argparse.ArgumentParser(description="from PDF to Scrapbox")
parser.add_argument("--in-file", "--in", "-i", type=str, help="input PDF file", required=False)
parser.add_argument("--resolution", "-r", type=int, default=200, help="Resolution for the output. Default is 200.")
parser.add_argument("--format", "-f", type=str, default='jpeg', choices=['jpeg', 'png'], help="Output format. Default is 'jpeg'.")
parser.add_argument("--in-dir", type=str, default="in", help="input PDF directory")
parser.add_argument("--out-dir", type=str, default="out", help="output directory")
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
    url = 'https://upload.gyazo.com/api/upload'
    headers = {
        'Authorization': f'Bearer {GYAZO_TOKEN}'
    }
    image_path = os.path.join(directory, image_name)
    files = {
        'imagedata': (
            image_name, 
            open(image_path, 'rb')
        )
    }
    response = requests.post(url, headers=headers, files=files)

    if response.status_code == 200:
        return response.json()

    raise Exception(f"Failed to upload image({response.status_code}): {response.text}")


def run_pdftocairo(input_pdf, output_directory, resolution=200, format='jpeg'):
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

    # Extract the base name from the input PDF path
    base_name = os.path.basename(input_pdf)
    file_name_without_ext = os.path.splitext(base_name)[0]

    # Ensure the output directory exists
    os.makedirs(output_directory, exist_ok=True)

    # Construct the pdftocairo command
    cmd = [
        'pdftocairo',
        '-r', str(resolution),
        '-' + format,
        input_pdf,
        os.path.join(output_directory, file_name_without_ext)
    ]

    # Execute the command
    subprocess.run(cmd, check=True)


def upload_images_to_gyazo(directory, ext="jpg"):
    """
    Uploads all images in the given directory to Gyazo.
    
    Args:
    - directory (str): The directory containing the images to upload.
    
    Returns:
    None
    """
    # Get all image files in the directory
    image_files = [f for f in os.listdir(directory) if f.endswith(f".{ext}")]
    print(f"In {directory}, Num images: {len(image_files)}")

    # 1: Sort the image files by index
    # Images may be `page-99.jpg` and `page-100.jpg`, so we need to sort by the page number.
    # Page number is continuous number before the last period.

    # Extract numbers to sort the images by index
    image_files = sorted(image_files, key=lambda x: int(re.findall(r'(\d+)', x)[-1]))


    # 2: Upload each image to Gyazo
    # Each upload returns a JSON object with the URL to the uploaded image.
    # We want to store them in a local JSON file for later use.
    # Save after each API call so that we don't lose data if the script crashes.

    # Local storage for Gyazo URLs
    gyazo_info = []
    json_path = os.path.join(directory, "gyazo_info.json")
    for image_file in image_files:
        res = upload_one_image_to_gyazo(image_file, directory)
        res["local_filename"] = image_file

        # Append the returned JSON to the gyazo_info list
        gyazo_info.append(res)

        # Save URLs to local JSON after each upload
        with open(json_path, 'w') as f:
            json.dump(gyazo_info, f, indent=2)


def get_gyazo_info(image_id):
    GYAZO_API_ROOT = "https://api.gyazo.com/api"
    res = requests.get(
        f"{GYAZO_API_ROOT}/images/{image_id}",
        headers={
            "Authorization": f"Bearer {GYAZO_TOKEN}"
        }
    )
    return res.json()


def get_ocr_texts(directory):
    """
    Read `gyazo_info.json` and get OCR text from Gyazo API.
    """
    print(f"Getting OCR texts for {directory}...")
    json_path = os.path.join(directory, "gyazo_info.json")
    with open(json_path) as f:
        gyazo_info = json.load(f)

    for info in tqdm(gyazo_info):
        image_id = info["image_id"]
        res = get_gyazo_info(image_id)
        if "ocr" in res:
            info["ocr_text"] = res["ocr"]["description"]
            with open(json_path, 'w') as f:
                json.dump(gyazo_info, f, indent=2)
        else:
            print(f"OCR not available for image_id={image_id}")


def get_out_dir(in_file):
    # Split the file path to get only the file name without extension
    base_name = os.path.basename(in_file)      # gets "foo.pdf"
    file_name_without_ext = os.path.splitext(base_name)[0]  # gets "foo"
    
    # Create the new directory path
    out_dir = os.path.join("out", file_name_without_ext)
    return out_dir


def process_one_pdf(in_file):
    out_dir = get_out_dir(in_file)
    # if skip_existing and os.path.exists(out_dir):
    #     print(f"Output directory `{out_dir}` already exists. Exiting...")
    #     return

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
    print(f"Making Scrapbox JSON for {directory}...")
    title = os.path.split(directory)[-1]

    json_path = os.path.join(directory, "gyazo_info.json")
    with open(json_path) as f:
        gyazo_info = json.load(f)

    page_lines = [title, f"local_path: {directory}", ""]

    for page in gyazo_info:
        # "permalink_url"
        page_lines.append(f"[{page['permalink_url']}]")
        page_lines.extend(page["ocr_text"].split("\n"))
        page_lines.append("")

    # Make the JSON
    scrapbox_json = {"pages": [{
        "title": title,
        "lines": page_lines
    }]}

    # Save the JSON
    out_path = os.path.join(directory, "scrapbox.json")
    with open(out_path, 'w') as f:
        json.dump(scrapbox_json, f, indent=2)


def main():
    if args.in_file:
        process_one_pdf(args.in_file)
    else:
        # Get all PDF files in the input directory
        INDIR = args.in_dir
        pdf_files = [os.path.join(INDIR, f) for f in os.listdir(INDIR) if f.endswith(".pdf")]
        pdf_files.sort()

        # Process each PDF file
        # for pdf_file in pdf_files:
        #     print(f"Processing `{pdf_file}`...")
        #     # process_one_pdf(pdf_file, skip_ocr=True)
        for pdf_file in pdf_files:
            # upload_images_to_gyazo(get_out_dir(pdf_file))
            # get_ocr_texts(get_out_dir(pdf_file))
            make_scrapbox_json(get_out_dir(pdf_file))
        print("Make Total Scrapbox JSON")
        total_pages = []
        data = {"pages": total_pages}
        for pdf_file in pdf_files:
            out_dir = get_out_dir(pdf_file)
            json_path = os.path.join(out_dir, "scrapbox.json")
            with open(json_path) as f:
                pages = json.load(f)["pages"]
                total_pages.extend(pages)
        with open("total_scrapbox.json", 'w') as f:
            json.dump(data, f, indent=2)


if __name__ == "__main__":
    main()
