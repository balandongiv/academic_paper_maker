import os
import time

from selenium import webdriver


def setup_driver(geckodriver_path, firefox_binary_path, download_folder):
    """
    Setup the Firefox WebDriver with custom settings for downloading PDFs.
    """
    options = webdriver.FirefoxOptions()
    options.binary_location = firefox_binary_path

    options.set_preference("browser.download.folderList", 2)  # Use custom download path
    options.set_preference("browser.download.dir", download_folder)
    options.set_preference("browser.helperApps.neverAsk.saveToDisk", "application/pdf")  # Automatically download PDF files
    options.set_preference("pdfjs.disabled", True)  # Disable built-in PDF viewer

    service = webdriver.firefox.service.Service(geckodriver_path)
    driver = webdriver.Firefox(service=service, options=options)
    return driver

def wait_for_download_complete(download_folder, timeout=60):
    """
    Wait for a download to complete by monitoring the download folder for the absence of .part files.
    """
    end_time = time.time() + timeout
    while time.time() < end_time:
        if not any(filename.endswith('.part') for filename in os.listdir(download_folder)):
            return True
        time.sleep(1)
    return False



# This file is a utility module and doesn't run directly.
