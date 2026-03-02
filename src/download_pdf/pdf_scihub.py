import json
import logging
import os
import shutil
import sys
import time
from tqdm import tqdm
from scidownl.api.scihub import scihub_download


# Configure logger
def configure_logger():
    logger = logging.getLogger("pdf_ieee")
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger


# Update JSON file with metadata
def update_json_file(json_file, metadata):
    with open(json_file, 'w') as file:
        json.dump(metadata, file, indent=4)


# Create temporary download folder
def create_temp_folder(main_temp_folder, bibtex):
    timestamp = int(time.time() * 1000)
    temp_folder = os.path.join(main_temp_folder, f"{bibtex}_{timestamp}")
    os.makedirs(temp_folder, exist_ok=True)
    return temp_folder


# Download a paper using SciHub
def download_paper(logger, details, bibtex, temp_folder):
    try:
        # Determine if DOI or title should be used
        try:
            url = details["doi"]
            paper_type = "doi"
        except KeyError:
            url = details["title"]
            paper_type = "title"

        pdf_path = os.path.join(temp_folder, f"{bibtex}.pdf")
        scihub_download(keyword=url, paper_type=paper_type, out=pdf_path)
        return "success", pdf_path, url

    except Exception as e:
        logger.error(f"Error downloading {details.get('title', 'Unknown')}: {e}")
        return "fail", None, url


# Save metadata and move files
def save_and_move_files(logger, metadata, temp_folder, download_folder, bibtex, pdf_path):
    json_filename = os.path.join(temp_folder, f"{bibtex}.json")
    update_json_file(json_filename, metadata)
    logger.info(f"Saved JSON metadata: {json_filename}")

    try:
        # Move files to final folder

        final_pdf_path = os.path.join(download_folder, f"{bibtex}.pdf")
        final_json_path = os.path.join(download_folder, f"{bibtex}.json")

        if metadata["status"] == "success" and pdf_path:
            shutil.move(pdf_path, final_pdf_path)

        shutil.move(json_filename, final_json_path)
        logger.info(f"Moved files to {download_folder}")
    except Exception as e:
        logger.error(f"Error moving files: {e}")


# Main download handler function
def do_download_scihub(scihub_dict,pdf_folder):
    # Configurations
    # pdf_folder = r"C:\Users\balan\OneDrive - ums.edu.my\research_related\0 eeg_trend_till24\eeg_review"
    main_temp_folder = os.path.join(pdf_folder, "temp_downloads")

    logger = configure_logger()
    logger.info("Starting SciHub download script")

    total_urls = len(scihub_dict)

    with tqdm(total=total_urls, desc="Processing SciHub Downloads") as pbar:
        for bibtex, details in scihub_dict.items():

            output_path = os.path.join(pdf_folder, bibtex + ".pdf")
            json_path = os.path.join(pdf_folder, bibtex + ".json")

            if os.path.exists(output_path) or os.path.exists(json_path):
                pbar.update(1)
                logger.info(f"PDF already exists: {output_path}")
                continue
            else:
                temp_folder = create_temp_folder(main_temp_folder, bibtex)
                status, pdf_path, url = download_paper(logger, details, bibtex, temp_folder)

            if status=='success' and os.path.exists(pdf_path):
                status='success'
            else:
                status='Scihub fail'
                # os.rmdir(temp_folder)

            metadata = {
                "bibtex": bibtex,
                "expected_pdf_name": f"{bibtex}.pdf",
                "actual_pdf_name": details.get("title", "Unknown"),
                "status": status,
                "url": url,
            }

            save_and_move_files(logger, metadata, temp_folder, pdf_folder, bibtex, pdf_path)

            pbar.update(1)  # Increment the progress bar

    logger.info("SciHub download process completed.")




if __name__ == "__main__":
    # Example SciHub dictionary for testing
    scihub_dict = {
        "example_bibtex_1": {"doi": "10.1109/5.771073", "title": "Example Title 1"},
        "example_bibtex_2": {"title": "Another Example Title"},
    }

    do_download_scihub(scihub_dict)
