import json
import os
import time

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from pdf_downloader import setup_driver


def setup_paths():
    """
    Sets up necessary paths for the webdriver and download folder.
    """
    geckodriver_path = r'D:\geckodrive\geckodriver.exe'
    firefox_binary_path = r'C:\Program Files\Mozilla Firefox\firefox.exe'
    download_folder = r"C:\Users\balan\Downloads"
    return geckodriver_path, firefox_binary_path, download_folder

def wait_for_download_complete(download_folder, timeout=60):
    """
    Waits for a download to complete by monitoring the download folder for the absence of .part files.
    """
    end_time = time.time() + timeout
    while time.time() < end_time:
        if not any(filename.endswith('.part') for filename in os.listdir(download_folder)):
            return True
        time.sleep(1)
    return False

def get_latest_file(download_folder):
    """
    Retrieves the most recently modified file in the download folder.
    """
    files = [os.path.join(download_folder, f) for f in os.listdir(download_folder) if os.path.isfile(os.path.join(download_folder, f))]
    if not files:
        return None
    latest_file = max(files, key=os.path.getmtime)
    return os.path.basename(latest_file)

def login(driver):
    """
    Performs login using the first URL.
    """
    urls = [
        "https://ieeexplore.ieee.org/document/10169941/",
    ]
    driver.get(urls[0])
    print("Navigated to:", driver.title)

    WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.CLASS_NAME, "inst-sign-in"))
    ).click()
    print("Clicked Institutional Sign In")

    WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.CLASS_NAME, "heading"))
    ).click()
    print("Clicked Access Through Your Institution")

    search_box = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.XPATH, '/html/body/ngb-modal-window/div/div/div/xpl-login-modal/div[1]/div[2]/div/div/xpl-login/div/section/div/div/div[2]/div[2]/xpl-inst-typeahead/div/div/input'))
    )
    search_box.send_keys("Universiti Malaysia Sabah")
    time.sleep(1)

    institution_link = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, "//a[@id='Universiti Malaysia Sabah']"))
    )
    institution_link.click()
    print("Selected Universiti Malaysia Sabah")
    print("Logged in successfully.")

def normalize_urls(input_data):
    """
    Normalizes input URLs into a consistent dictionary format.
    If input is a list, keys are generated from the last part of the URL.
    If input is already a dictionary, it is returned as-is.
    """
    if isinstance(input_data, list):
        return {url.rstrip('/').split('/')[-1]: url for url in input_data}
    elif isinstance(input_data, dict):
        return input_data
    else:
        raise ValueError("Input URLs must be either a list or a dictionary.")

def download_pdfs(driver, url_dict, download_folder):
    """
    Iterates through a dictionary of URLs to download PDFs and save JSON metadata.
    """
    for key, url in url_dict.items():
        driver.get(url)
        print(f"Navigated to: {url}")

        status = "fail"
        actual_file = None
        try:
            pdf_link = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//a[contains(@class, 'xpl-btn-pdf') and contains(@href, 'stamp')]"))
            )
            pdf_link.click()
            print(f"PDF download initiated for: {url}")

            if wait_for_download_complete(download_folder):
                latest_file = get_latest_file(download_folder)
                if latest_file:
                    print(f"Download complete: {latest_file}")
                    actual_file = latest_file
                    status = "success"
                else:
                    print(f"No new file detected for: {url}")
            else:
                print(f"Download timed out for: {url}")
                continue

        except Exception as e:
            print(f"Could not download PDF for {url}: {e}")
            continue

        # Save the JSON metadata
        json_filename = os.path.join(download_folder, f"{key}.json")
        metadata = {"expected_pdf_name": f"{key}.pdf",
                    "actual_pdf_name": actual_file,
                    "status": status,
                    "url": url}
        with open(json_filename, 'w') as json_file:
            json.dump(metadata, json_file, indent=4)
        print(f"Saved JSON metadata: {json_filename}")
def do_download_ieee(input_urls,bibtex=None):
    geckodriver_path, firefox_binary_path, download_folder = setup_paths()

    url_dict = normalize_urls(input_urls)

    driver = setup_driver(geckodriver_path, firefox_binary_path, download_folder)

    try:
        login(driver)
        download_pdfs(driver, url_dict, download_folder)
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        driver.quit()

def main():
    """
    Main function to set up the WebDriver, login, and download PDFs.
    """


    # Input URLs: Can be either a list or a dictionary
    input_urls = [
        "https://ieeexplore.ieee.org/document/10169941/",
        "https://ieeexplore.ieee.org/document/10216090/",
        # "https://ieeexplore.ieee.org/document/10236992/",
        # "https://ieeexplore.ieee.org/document/10366672/",
        # "https://ieeexplore.ieee.org/document/10366759/",
        # "https://ieeexplore.ieee.org/document/10428087/",
    ]

    # Uncomment below to use a dictionary instead
    # input_urls = {
    #     "Rezaee_Q": "https://ieeexplore.ieee.org/document/10169941/",
    #     "fasf": "https://ieeexplore.ieee.org/document/10216090/"
    # }


if __name__ == "__main__":
    main()
