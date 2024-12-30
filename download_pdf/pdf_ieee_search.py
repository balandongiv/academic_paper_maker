import errno
import logging
import os
import shutil
import sys
import time
import tkinter as tk
from tkinter import messagebox

from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
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




def wait_for_download_complete(download_folder, timeout=600):
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


def login_ieee(driver):
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
    Downloads PDFs and handles errors gracefully to ensure the loop processes all entries.
    """
    # Extract cookies
    cookies = initial_driver.get_cookies()

    with tqdm(total=len(flattened_entries), desc="Processing URLs") as pbar:
        for key, value in flattened_entries.items():
            bibtex = key
            doi = value.get('doi', 'Unknown DOI')
            if bibtex == 'Eskandarian_C_2021':
                continue
            timestamp = int(time.time() * 1000)
            temp_url_folder = os.path.join(main_temp_folder, f"{bibtex}_{timestamp}")
            os.makedirs(temp_url_folder, exist_ok=True)

            driver = create_driver(geckodriver_path, firefox_binary_path, temp_url_folder)

            try:
                # Transfer cookies
                driver.get("https://ieeexplore.ieee.org/")
                driver.delete_all_cookies()
                for c in cookies:
                    driver.add_cookie(c)
                driver.get("https://ieeexplore.ieee.org/")

                logger.info(f"Processing DOI: {doi} for BibTeX key: {bibtex}")

                # Perform the search
                search_input = WebDriverWait(driver, 10).until(
                    EC.visibility_of_element_located((By.XPATH, "//input[@aria-label='main']"))
                )
                search_input.clear()
                search_input.send_keys(doi)

                search_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[@aria-label='Search']"))
                )
                search_button.click()

                # Locate PDF link
                pdf_link = WebDriverWait(driver, 20).until(
                    EC.presence_of_element_located((By.XPATH, "//a[contains(@href, '/stamp/stamp.jsp')]"))
                )
                pdf_href = pdf_link.get_attribute('href')
                driver.get(pdf_href)

                # Wait for download to complete
                if wait_for_download_complete(temp_url_folder):
                    latest_file = get_latest_file(temp_url_folder)
                    if latest_file and latest_file.lower().endswith('.pdf'):
                        handle_success(latest_file, bibtex, temp_url_folder, download_folder)
                    else:
                        logger.warning(f"No valid PDF file found for DOI {doi}.")
                        handle_failure(temp_url_folder, bibtex, triage_folder)
                else:
                    logger.warning(f"Download timed out for DOI {doi}.")
                    handle_failure(temp_url_folder, bibtex, triage_folder)

            except TimeoutException:
                logger.error(f"PDF link not found or download timeout for DOI {doi}.")
                handle_failure(temp_url_folder, bibtex, triage_folder)

            except OSError as e:
                if e.errno == errno.EBUSY:
                    logger.error(f"File lock issue for DOI {doi}: {e}")
                else:
                    logger.error(f"Unexpected file system error for DOI {doi}: {e}")
                handle_failure(temp_url_folder, bibtex, triage_folder)

            except Exception as e:
                logger.error(f"Unexpected error for DOI {doi}: {e}")
                handle_failure(temp_url_folder, bibtex, triage_folder)

            finally:
                driver.quit()
                pbar.update(1)

def handle_success(latest_file, bibtex, temp_url_folder, download_folder):
    """Handle successful download."""
    try:
        latest_file= os.path.join(temp_url_folder, latest_file)
        target_pdf_name = f"{bibtex}.pdf"
        target_pdf = os.path.join(temp_url_folder, target_pdf_name)
        os.rename(latest_file, target_pdf)

        final_pdf_path = os.path.join(download_folder, target_pdf_name)
        shutil.move(target_pdf, final_pdf_path)
        logger.info(f"PDF successfully downloaded and moved to: {final_pdf_path}")

    except Exception as e:
        logger.error(f"Error handling successful download for BibTeX {bibtex}: {e}")
        # raise  # Optionally re-raise for debugging purposes


def handle_failure(temp_url_folder, bibtex, triage_folder):
    """Handle failures gracefully by moving temp data to the triage folder."""
    triage_bib_folder = os.path.join(triage_folder, f"{bibtex}_{int(time.time() * 1000)}")
    try:
        shutil.move(temp_url_folder, triage_bib_folder)
        logger.info(f"Moved incomplete data for {bibtex} to triage folder: {triage_bib_folder}")
    except Exception as e:
        logger.error(f"Failed to move incomplete data for {bibtex} to triage folder: {e}")




def do_download_ieee_search(input_urls):
    """
    Orchestrates the download process.
    """
    try:
        # url_dict = normalize_urls(input_urls)
        # flattened_entries = flatten_url_dict(url_dict)

        geckodriver_path, firefox_binary_path, download_folder, triage_folder, main_temp_folder = setup_paths()

        # Single login driver
        initial_driver = create_driver(geckodriver_path, firefox_binary_path, main_temp_folder)
        login_ieee(initial_driver)
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
    """
    ieee_dict = {
        'dummy_Nguyen_H_2023': {
            'doi': '10.1109/JSEN.2023.3307766',
            'title': 'Behind-the-Ear EEG-Based Wearable Driver Drowsiness Detection System Using Embedded Tiny Neural Networks',
            'url': [
                'https://www.scopus.com/inward/record.uri?eid=2-s2.0-85170514053&doi=10.1109%2fJSEN.2023.3307766&partnerID=40&md5=03312515df8489961c92b88009cdda9a'
            ]
        },
        'dummy_Yaacob_H_2023': {
            'doi': '10.1109/ACCESS.2023.3296382',
            'title': 'Application of Artificial Intelligence Techniques for Brain-Computer Interface in Mental Fatigue Detection: A Systematic Review (2011-2022)',
            'url': [
                'https://www.scopus.com/inward/record.uri?eid=2-s2.0-85165289795&doi=10.1109%2fACCESS.2023.3296382&partnerID=40&md5=5133f41370bc67b73d7d337f83e38be5'
            ]
        },
        'dummy_Pan_J_2023': {
            'doi': '10.1109/TIM.2023.3307756',
            'title': 'Residual Attention Capsule Network for Multimodal EEG- and EOG-Based Driver Vigilance Estimation',
            'url': [
                'https://www.scopus.com/inward/record.uri?eid=2-s2.0-85168714318&doi=10.1109%2fTIM.2023.3307756&partnerID=40&md5=c91c54ed0ba4ab797b158b1e42f61c04'
            ]
        }
    }


    do_download_ieee_search(ieee_dict)


if __name__ == "__main__":
    main()
