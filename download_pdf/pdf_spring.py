import os
from pdf_downloader import setup_driver, wait_for_download_complete
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
def accept_cookies_once(driver):
    """
    Handle cookie acceptance, if applicable.
    """
    try:
        accept_cookies_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[text()='Accept all cookies']"))
        )
        accept_cookies_button.click()
        print("Accepted all cookies.")
    except Exception:
        print("Cookies acceptance not required or already accepted.")

def download_pdf(driver, url, download_folder):
    """
    Navigate to the URL and download the PDF file.
    """
    try:
        driver.get(url)
        print("Navigated to:", driver.title)

        # Wait for the page to load completely
        WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.TAG_NAME, "body")))

        # Locate and click on the "Download PDF" button/link
        download_button = WebDriverWait(driver, 30).until(
            EC.element_to_be_clickable((By.XPATH, "//a[contains(@class, 'pdf-download__link')]"))
        )
        download_button.click()
        time.sleep(5)
        # Wait for the download to complete
        if wait_for_download_complete(download_folder):
            print("Download completed successfully.")
        else:
            print("Download did not complete within the timeout period.")

    except Exception as e:
        print("An error occurred:", e)

# Define paths and folder
geckodriver_path = r'D:\geckodrive\geckodriver.exe'
firefox_binary_path = r'C:\Program Files\Mozilla Firefox\firefox.exe'
download_folder = r"C:\\Users\\balan\\Downloads"

# List of URLs to download PDFs from
springer_urls = [
    "https://link.springer.com/article/10.1007/s11063-022-10858-x",
    "https://link.springer.com/article/10.1007/s00521-022-07466-0",
    # Add more URLs as needed
]

# Setup the WebDriver
driver = setup_driver(geckodriver_path, firefox_binary_path, download_folder)

try:
    # Navigate to a sample page to accept cookies once
    driver.get(springer_urls[0])
    accept_cookies_once(driver)

    # Iterate through the list of URLs and download each PDF
    for url in springer_urls:
        print(f"Processing URL: {url}")
        download_pdf(driver, url, download_folder)

finally:
    # Close the browser
    driver.quit()
    print("Browser closed.")
