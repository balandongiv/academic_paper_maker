import json
import logging
import os
import sys
import time
import tkinter as tk
from tkinter import messagebox

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from tqdm import tqdm

# from download_pdf.browse_internet.firefox_setting import create_driver_with_profile
# Configure logger
logger = logging.getLogger("pdf_ieee")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)
from selenium import webdriver
from selenium.webdriver.firefox.firefox_profile import FirefoxProfile
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.firefox.service import Service as FirefoxService
def accept_cookies_once(driver):
    """
    Handle cookie acceptance, if applicable. This is unique for springer
    """
    try:
        accept_cookies_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[text()='Accept all cookies']"))
        )
        accept_cookies_button.click()
        print("Accepted all cookies.")
    except Exception:
        print("Cookies acceptance not required or already accepted.")

def create_driver_with_profile(geckodriver_path, firefox_binary_path, firefox_profile_path,download_folder=None):
    """
    Creates a Firefox WebDriver using an existing profile.
    """
    options = FirefoxOptions()
    options.binary_location = firefox_binary_path
    profile = FirefoxProfile(firefox_profile_path)
    options.profile = profile  # Set the profile in options
    # The options below
    options.set_preference("browser.download.folderList", 2)
    if download_folder is not None: # Use custom download path
        options.set_preference("browser.download.dir", download_folder)
        options.set_preference("browser.helperApps.neverAsk.saveToDisk", "application/pdf")  # Automatically download PDF files
        options.set_preference("pdfjs.disabled", True)  # Disable built-in PDF viewer


    service = FirefoxService(executable_path=geckodriver_path)
    driver = webdriver.Firefox(service=service, options=options)
    return driver
def setup_paths():
    """
    Sets up necessary paths for the webdriver, download folder, and triage folder.
    """
    geckodriver_path = r'C:\Users\balan\IdeaProjects\academic_paper_maker\browser\geckodriver.exe'
    firefox_binary_path = r'C:\Program Files\Mozilla Firefox\firefox.exe'
    download_folder = r"C:\Users\balan\OneDrive - ums.edu.my\research_related\corona_discharge\pdf"
    main_temp_folder = os.path.join(download_folder, "temp_downloads")
    os.makedirs(main_temp_folder, exist_ok=True)
    triage_folder = os.path.join(download_folder, "triage")
    os.makedirs(triage_folder, exist_ok=True)

    return geckodriver_path, firefox_binary_path, download_folder, triage_folder, main_temp_folder


def create_driver(geckodriver_path, firefox_binary_path, download_directory):
    """
   Creates a Firefox WebDriver using an existing profile.
   """
    options = FirefoxOptions()
    options.binary_location = firefox_binary_path
    profile = FirefoxProfile(firefox_profile_path)
    options.profile = profile  # Set the profile in options
    # The options below
    options.set_preference("browser.download.folderList", 2)
    if download_directory is not None: # Use custom download path
        options.set_preference("browser.download.dir", download_folder)
        options.set_preference("browser.helperApps.neverAsk.saveToDisk", "application/pdf")  # Automatically download PDF files
        options.set_preference("pdfjs.disabled", True)  # Disable built-in PDF viewer


    service = FirefoxService(executable_path=geckodriver_path)
    driver = webdriver.Firefox(service=service, options=options)
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


def login_springer(driver):
    """
    Performs login using the first URL.
    Ensures only a single login is done at the start.
    """
    urls = ["https://www.sciencedirect.com/search?qs=Automated%20detection%20of%20driver%20fatigue%20from%20electroencephalography"]
    driver.get(urls[0])
    logger.info(f"Navigated to: {driver.title}")
    # accept_cookies_once(driver)


    logger.info("Make sure to login all the required loin...")
    user_response = show_popup()
    if not user_response:
        logger.info("User cancelled the operation.")
        driver.quit()
        sys.exit(0)
    logger.info("Do not forget to approve the pop up")
    logger.info("User confirmed. Proceeding with the login...")
    # Wait a bit for the login redirect to occur
    # time.sleep(10)
    logger.info("Logged in successfully.")


def normalize_urls(input_data):
    """
    Normalizes input URLs into a consistent dictionary format, including titles.
    """
    if isinstance(input_data, list):
        return {item[0]: {"doi": item[1], "title": item[2]} for item in input_data}
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
    return [(bibtex, details["doi"], details["title"]) for bibtex, details in url_dict.items()]


def download_pdfs(initial_driver, input_urls, download_folder, triage_folder, main_temp_folder,
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

    total_urls =len(input_urls)
    driver=initial_driver
    with tqdm(total=total_urls, desc="Processing URLs") as pbar:
        for key, value in input_urls.items():
            bibtex= key
            doi = value['doi']

            logger.info(f"Processing URL: {doi} for {bibtex}")

            try:
                # paper_title = "Automated detection of driver fatigue from electroencephalography"

                driver.get("https://www.sciencedirect.com/")
                print("[INFO] Navigated to https://www.sciencedirect.com/")

                # 3. Insert academic paper details in the search box
                #    The ID of the search input is 'qs'
                search_input = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.ID, "qs"))
                    )
                search_input.clear()
                search_input.send_keys(doi)
                print(f"[INFO] Entered query: {doi}")

                # 4. Submit the search

                search_input.submit()
                print("[INFO] Search submitted")

                 # Find all search result items
                search_results = WebDriverWait(driver, 10).until(
                        EC.presence_of_all_elements_located((By.CSS_SELECTOR, "li.ResultItem"))
                    )

                # Find the first search result anchor tag
                first_result = search_results[0].find_element(By.CSS_SELECTOR, "a.result-list-title-link")

                # Extract the href and anchor text
                href = first_result.get_attribute("href")
                anchor_text = first_result.find_element(By.CSS_SELECTOR, ".anchor-text span").text
                # driver.get(href)
                #
                #
                # # Locate the "View PDF" button and click it
                # pdf_button = driver.find_element(By.XPATH, "//span[contains(text(), 'View')]/parent::span/parent::span")
                # pdf_button.click()

                # Generate the filename from the bibtex value
                # bibtex = first_result.get_attribute("id")  # Assuming bibtex value is stored in the "id" attribute
                filename = f"{bibtex}.json"

                # Create a dictionary with the extracted data
                result_data = {
                        "href": href,
                        "text": anchor_text
                    }

                # Save the data to a JSON file
                with open(filename, "w") as json_file:
                    json.dump(result_data, json_file, indent=4)

                print(f"Data saved to {filename}: {result_data}")



            except Exception as e:
                # logger.error(f"Could not download PDF for {url}: {e}")
                driver.quit()
                pbar.update(1)
                continue



def do_download_scincedirect(input_urls):
    """
    Orchestrates the download process.
    """
    logger.warning("This script only can extract the url but cannot download as sciencedirect security faeature is unbreakable")
    try:
        # url_dict = normalize_urls(input_urls)
        # flattened_entries = flatten_url_dict(url_dict)

        geckodriver_path, firefox_binary_path, download_folder, triage_folder, main_temp_folder = setup_paths()

        # Single login driver

        firefox_profile_path = r"C:\Users\balan\AppData\Roaming\Mozilla\Firefox\Profiles\ssjd4eo7.default-release"
        initial_driver = create_driver_with_profile(geckodriver_path, firefox_binary_path, firefox_profile_path)
        # initial_driver = create_driver(geckodriver_path, firefox_binary_path, main_temp_folder)
        login_springer(initial_driver)
        logger.info("Starting PDF download process...")

        download_pdfs(
            initial_driver,
            input_urls,
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

    WARNING
    This script only can extract the url but cannot download as sciencedirect security faeature is unbreakable
    """
    input_urls = [
        (
            'dummy_C_2023',
            ['10.1016/j.dcn.2024.101447'],
            'dummy Detection'
        ),
        (
            'dummy_C_2018',
            ['10.1016/j.bspc.2024.107394'],
            'dummy Interfaces'
        )
        ,
        (
            'dummy_x_2018',
            ['nothi'],
            'dummy Interfaces'
        )
    ]

    do_download_scincedirect(input_urls)


if __name__ == "__main__":
    main()
