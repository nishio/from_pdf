"""
from PDF to Scrapbox

"""
import os
import argparse
import subprocess

parser = argparse.ArgumentParser(description="from PDF to Scrapbox")
parser.add_argument("--in-file", "--in", "-i", type=str, help="input PDF file", required=False)
parser.add_argument("--resolution", "-r", type=int, default=200, help="Resolution for the output. Default is 200.")
parser.add_argument("--format", "-f", type=str, default='jpeg', choices=['jpeg', 'png'], help="Output format. Default is 'jpeg'.")
parser.add_argument("--in-dir", type=str, default="in", help="input PDF directory")
parser.add_argument("--out-dir", type=str, default="out", help="output directory")
args = parser.parse_args()


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


def process_one_pdf(in_file, skip_existing=True):
    # Split the file path to get only the file name without extension
    base_name = os.path.basename(in_file)      # gets "foo.pdf"
    file_name_without_ext = os.path.splitext(base_name)[0]  # gets "foo"
    
    # Create the new directory path
    out_dir = os.path.join("out", file_name_without_ext)

    if skip_existing and os.path.exists(out_dir):
        print(f"Output directory `{out_dir}` already exists. Exiting...")
        return
    # Make the directory. The exist_ok=True ensures that the function doesn't
    # raise an error if the directory already exists.
    os.makedirs(out_dir, exist_ok=True)
    # rest of your processing code...

    # pdftocairo -r 200 -jpeg in/LLM_day1.pdf out/LLM_day1
    run_pdftocairo(in_file, out_dir, args.resolution, args.format)


def main():
    if args.in_file:
        process_one_pdf(args.in_file)
    else:
        # Get all PDF files in the input directory
        INDIR = args.in_dir
        pdf_files = [os.path.join(INDIR, f) for f in os.listdir(INDIR) if f.endswith(".pdf")]

        # Process each PDF file
        for pdf_file in pdf_files:
            print(f"Processing `{pdf_file}`...")
            process_one_pdf(pdf_file)

if __name__ == "__main__":
    main()
