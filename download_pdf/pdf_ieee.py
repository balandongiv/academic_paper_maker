import json
import logging
import os
import shutil
import sys
import time
import tkinter as tk
from tkinter import messagebox

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from tqdm import tqdm

# Configure logger
logger = logging.getLogger("pdf_ieee")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)


def setup_paths():
    """
    Sets up necessary paths for the webdriver, download folder, and triage folder.
    """
    geckodriver_path = r'D:\geckodrive\geckodriver.exe'
    firefox_binary_path = r'C:\Program Files\Mozilla Firefox\firefox.exe'
    download_folder = r"C:\Users\balan\OneDrive - ums.edu.my\research_related\0 eeg_trend_till24\eeg_review"
    main_temp_folder = os.path.join(download_folder, "temp_downloads")
    os.makedirs(main_temp_folder, exist_ok=True)
    triage_folder = os.path.join(download_folder, "triage")
    os.makedirs(triage_folder, exist_ok=True)

    return geckodriver_path, firefox_binary_path, download_folder, triage_folder, main_temp_folder


from selenium.webdriver.firefox.service import Service

def create_driver(geckodriver_path, firefox_binary_path, download_directory):
    """
    Creates a Firefox WebDriver with given download directory settings.
    """
    # Create a Firefox profile and configure preferences
    profile = webdriver.FirefoxProfile()
    profile.set_preference("browser.download.folderList", 2)
    profile.set_preference("browser.download.dir", download_directory)
    profile.set_preference("browser.download.useDownloadDir", True)
    profile.set_preference("pdfjs.disabled", True)
    profile.set_preference("plugin.scan.plid.all", False)
    profile.set_preference("plugin.scan.Acrobat", "99.0")
    profile.set_preference("browser.helperApps.neverAsk.saveToDisk", "application/pdf")
    profile.set_preference("browser.helperApps.alwaysAsk.force", False)
    profile.set_preference("browser.download.manager.showWhenStarting", False)
    profile.set_preference("browser.download.manager.focusWhenStarting", False)
    profile.set_preference("browser.download.manager.useWindow", False)
    profile.set_preference("browser.download.manager.showAlertOnComplete", False)
    profile.set_preference("browser.download.manager.closeWhenDone", True)

    # Configure options and attach the profile
    options = Options()
    options.binary_location = firefox_binary_path
    options.profile = profile

    # Initialize the Service object with the path to geckodriver
    service = Service(geckodriver_path)
    driver = webdriver.Firefox(service=service, options=options)
    driver.maximize_window()
    return driver




def wait_for_download_complete(download_folder, timeout=60):
    """
    Waits for a download to complete by monitoring the download folder for the absence of .part files.
    """
    end_time = time.time() + timeout
    start_time = time.time()

    while time.time() < end_time:
        elapsed_time = int(time.time() - start_time)
        remaining_time = int(timeout - elapsed_time)
        logger.debug(f"Waiting for download... Elapsed: {elapsed_time}s | Remaining: {remaining_time}s")

        # If no .part files found and at least one PDF exists, consider download done
        part_files = [f for f in os.listdir(download_folder) if f.endswith('.part')]
        if not part_files:
            # Check if there's any file at all
            files = os.listdir(download_folder)
            if files:
                return True
        time.sleep(1)

    logger.warning("Download timeout or no matching file found.")
    return False


def get_latest_file(download_folder):
    """
    Retrieves the most recently modified file in the download folder.
    """
    files = [os.path.join(download_folder, f) for f in os.listdir(download_folder)
             if os.path.isfile(os.path.join(download_folder, f))]
    if not files:
        return None
    latest_file = max(files, key=os.path.getmtime)
    return os.path.basename(latest_file)


def show_popup():
    """
    Creates a pop-up window asking the user for confirmation.
    """
    root = tk.Tk()
    root.withdraw()
    user_response = messagebox.askokcancel(
        "Confirmation",
        "I'm here so that you login via the institutional login page. Do you want to proceed?"
    )
    root.destroy()
    return user_response


def login(driver):
    """
    Performs login using the first URL.
    Ensures only a single login is done at the start.
    """
    urls = [
        "https://ieeexplore.ieee.org/document/10169941/",
    ]
    driver.get(urls[0])
    logger.info(f"Navigated to: {driver.title}")

    WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.CLASS_NAME, "inst-sign-in"))
    ).click()
    logger.info("Clicked Institutional Sign In")

    WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.CLASS_NAME, "heading"))
    ).click()
    logger.info("Clicked Access Through Your Institution")

    search_box = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located(
            (By.XPATH, '/html/body/ngb-modal-window/div/div/div/xpl-login-modal/div[1]/div[2]/div/div/xpl-login/div/section/div/div/div[2]/div[2]/xpl-inst-typeahead/div/div/input')
        )
    )
    search_box.send_keys("Universiti Malaysia Sabah")
    time.sleep(1)

    institution_link = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, "//a[@id='Universiti Malaysia Sabah']"))
    )
    institution_link.click()
    logger.info("Selected Universiti Malaysia Sabah")

    user_response = show_popup()
    if not user_response:
        logger.info("User cancelled the operation.")
        driver.quit()
        sys.exit(0)

    logger.info("User confirmed. Proceeding with the login...")
    # Wait a bit for the login redirect to occur
    time.sleep(10)
    logger.info("Logged in successfully.")


def normalize_urls(input_data):
    """
    Normalizes input URLs into a consistent dictionary format, including titles.
    """
    if isinstance(input_data, list):
        return {item[0]: {"url": item[1], "title": item[2]} for item in input_data}
    elif isinstance(input_data, dict):
        normalized = {}
        for key, value in input_data.items():
            normalized[key] = {
                "url": value["url"] if isinstance(value["url"], list) else [value["url"]],
                "title": value.get("title", None),
            }
        return normalized
    else:
        raise ValueError("Input URLs must be either a list or a dictionary.")


def flatten_url_dict(url_dict):
    """
    Flattens the dictionary into a list of (bibtex, url, title) tuples.
    """
    return [(bibtex, details["url"], details["title"]) for bibtex, details in url_dict.items()]


def download_pdfs(initial_driver, flattened_entries, download_folder, triage_folder, main_temp_folder,
                  geckodriver_path, firefox_binary_path):
    """
    Downloads PDFs from a flattened list of (bibtex, url, title) tuples and saves JSON metadata.
    Avoid multiple logins by using the initial driver's session cookies.
    For each URL:
      - Create a unique temporary folder inside main_temp_folder
      - Spawn a new driver with that folder as download dir
      - Transfer cookies from initial_driver to new driver
      - Download the PDF
      - Once done, rename/move PDF and save JSON
    """

    # Get cookies from initial_driver after login
    cookies = initial_driver.get_cookies()

    total_urls = sum(len(urls) for _, urls, _ in flattened_entries)
    with tqdm(total=total_urls, desc="Processing URLs") as pbar:
        for bibtex, urls, title in flattened_entries:
            for url in urls:
                # Create a unique temp folder for this URL
                # We can use bibtex + a timestamp or simple uniqueness
                timestamp = int(time.time() * 1000)
                temp_url_folder = os.path.join(main_temp_folder, f"{bibtex}_{timestamp}")
                os.makedirs(temp_url_folder, exist_ok=True)

                # Create a new driver for this URL with the custom download folder
                driver = create_driver(geckodriver_path, firefox_binary_path, temp_url_folder)

                # Inject cookies from initial driver to maintain logged-in session
                driver.get("https://ieeexplore.ieee.org/")  # Navigate to a page before adding cookies
                driver.delete_all_cookies()
                for c in cookies:
                    driver.add_cookie(c)
                driver.get("https://ieeexplore.ieee.org/")  # Refresh page to apply cookies

                logger.info(f"Processing URL: {url} for {bibtex}")

                status = "fail"
                actual_file = None

                try:
                    if '.pdf' in url.lower():
                        driver.execute_script("window.location.href = arguments[0];", url)
                        logger.info(f"Direct PDF download initiated for: {url}")
                    else:
                        driver.get(url)
                        logger.info(f"Navigated to: {url}")
                        pdf_link = WebDriverWait(driver, 10).until(
                            EC.element_to_be_clickable(
                                (By.XPATH, "//a[contains(@class, 'xpl-btn-pdf') and contains(@href, 'stamp')]"))
                        )
                        pdf_link.click()
                        logger.info(f"PDF download initiated via link for: {url}")

                    if wait_for_download_complete(temp_url_folder):
                        latest_file = get_latest_file(temp_url_folder)
                        if latest_file and latest_file.lower().endswith('.pdf'):
                            logger.info(f"Download complete: {latest_file}")
                            actual_file = latest_file
                            status = "success"
                        else:
                            logger.warning(f"No valid PDF file detected for: {url}")
                    else:
                        logger.warning(f"Download timed out for: {url}")

                except Exception as e:
                    logger.error(f"Could not download PDF for {url}: {e}")
                    driver.quit()
                    pbar.update(1)
                    continue

                # Save JSON metadata regardless of success/fail
                json_filename = os.path.join(temp_url_folder, f"{bibtex}.json")
                metadata = {
                    "expected_pdf_name": f"{bibtex}.pdf",
                    "actual_pdf_name": f"{actual_file if actual_file else 'None'}",
                    "status": status,
                    "url": url
                }
                with open(json_filename, 'w') as json_file:
                    json.dump(metadata, json_file, indent=4)
                logger.info(f"Saved JSON metadata: {json_filename}")

                # If success, rename PDF and move to final folder
                if status == "success" and actual_file:
                    # Rename PDF to bibtex.pdf
                    source_pdf = os.path.join(temp_url_folder, actual_file)
                    target_pdf_name = f"{bibtex}.pdf"
                    target_pdf = os.path.join(temp_url_folder, target_pdf_name)
                    os.rename(source_pdf, target_pdf)

                    # Move PDF and JSON to main download_folder
                    final_pdf_path = os.path.join(download_folder, f"{bibtex}.pdf")
                    final_json_path = os.path.join(download_folder, f"{bibtex}.json")

                    shutil.move(target_pdf, final_pdf_path)
                    shutil.move(json_filename, final_json_path)
                    logger.info(f"Moved PDF and JSON to {download_folder}")

                else:
                    # If fail, we still keep the JSON in main folder for reference
                    # and move the folder to triage
                    final_json_path = os.path.join(download_folder, f"{bibtex}.json")
                    shutil.move(json_filename, final_json_path)
                    logger.info("PDF download failed, JSON moved to main folder for reference.")
                    # Move the temp folder to triage for inspection (if it has leftovers)
                    # or at least keep a record
                    triage_bib_folder = os.path.join(triage_folder, f"{bibtex}_{timestamp}")
                    shutil.move(temp_url_folder, triage_bib_folder)
                    logger.info(f"Moved incomplete data to triage folder: {triage_bib_folder}")


                driver.quit()
                pbar.update(1)


def do_download_ieee(input_urls):
    """
    Orchestrates the download process.
    """
    try:
        url_dict = normalize_urls(input_urls)
        flattened_entries = flatten_url_dict(url_dict)

        geckodriver_path, firefox_binary_path, download_folder, triage_folder, main_temp_folder = setup_paths()

        # Single login driver
        initial_driver = create_driver(geckodriver_path, firefox_binary_path, main_temp_folder)
        login(initial_driver)
        logger.info("Starting PDF download process...")

        download_pdfs(
            initial_driver,
            flattened_entries,
            download_folder,
            triage_folder,
            main_temp_folder,
            geckodriver_path,
            firefox_binary_path
        )
    except Exception as e:
        logger.error(f"An error occurred: {e}")
    finally:
        # Close the initial driver after all downloads are done
        if 'initial_driver' in locals():
            initial_driver.quit()


def main():
    """
    Main function to log in once and download all PDFs.
    """
    input_urls = [
        (
            'Chen_C_2023',
            ['https://ieeexplore.ieee.org/ielx7/7333/10031624/10194963.pdf?tp=&arnumber=10194963&isnumber=10031624&ref='],
            'Self-Attentive Channel-Connectivity Capsule Network for EEG-Based Driving Fatigue Detection'
        ),
        (
            'Wei_C_2018',
            ['https://ieeexplore.ieee.org/ielx7/7333/8288842/08247228.pdf?tp=&arnumber=8247228&isnumber=8288842&ref='],
            'Toward Drowsiness Detection Using Non-hair-Bearing EEG-Based Brain-Computer Interfaces'
        )
    ]

    do_download_ieee(input_urls)


if __name__ == "__main__":
    main()
