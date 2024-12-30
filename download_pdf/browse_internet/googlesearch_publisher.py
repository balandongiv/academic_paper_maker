import logging
import os
import sys

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

'''
This code will be use to search the publisher based on incomplete journal name from the excel file

'''


import json
from time import sleep
from bs4 import BeautifulSoup
from download_pdf.browse_internet.firefox_setting import create_driver_with_profile
from download_pdf.haltbrowser import show_popup

# Configure logger
logger = logging.getLogger("pdf_ieee")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)

def get_search_results_from_page_source(page_source, num_results):
    """
    Extracts the top N result URLs from the page source using BeautifulSoup.
    """
    soup = BeautifulSoup(page_source, 'html.parser')
    urls = []
    links = soup.find_all('a', href=True)
    for link in links:
        url = link['href']
        urls.append(url)
    return urls

def search_google_and_extract_urls(driver, keyword, num_results=10):
    """
    Searches Google for a given keyword and extracts the top N result URLs using BeautifulSoup.
    """
    driver.get(f"https://www.google.com/search?q={keyword} journal")
    sleep(2)  # Allow time for the page to load
    results = []

    # Use a more robust selector to find result containers
    search_result_elements = WebDriverWait(driver, 10).until(
        EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.g"))
    )

    for result_element in search_result_elements:
        try:
            # Find the anchor element and get href
            link_element = result_element.find_element(By.CSS_SELECTOR, "a")
            href = link_element.get_attribute("href")

            # Find the heading element and get text
            title_element = result_element.find_element(By.CSS_SELECTOR, "h3")
            text = title_element.text

            results.append({"href": href, "text": text})

        except Exception as e:
            print(f"Error processing a result element: {e}")
            # You might want to log the specific error or skip to the next result
            continue
    results=results[0] # I purposely added this line to get the first result. thou not efficient, but i want use the above code as sample in the future
    return results

def save_results_to_json(keyword, search_term, urls, main_directory=None):
    """
    Saves the search results to a JSON file in a directory named after the keyword.
    If main_directory is specified, it saves under that directory; otherwise, it saves in the current working directory.
    The JSON file will contain a "title" key for the search term and a "url" key for the list of URLs.
    """
    if main_directory:
        directory_name = os.path.join(main_directory, keyword)
    else:
        directory_name = keyword

    if not os.path.exists(directory_name):
        os.makedirs(directory_name)

    file_path = os.path.join(directory_name, f"{keyword}.json")
    data = {
        "title": search_term,
        "url": urls
    }
    with open(file_path, 'w') as json_file:
        json.dump(data, json_file, indent=4)

    logger.info(f"Results saved to {file_path}")

def check_if_json_exists(keyword, main_directory=None):
    """
    Checks if a JSON file for the given keyword already exists on disk.
    """
    if main_directory:
        directory_name = os.path.join(main_directory, keyword)
    else:
        directory_name = keyword

    file_path = os.path.join(directory_name, f"{keyword}.json")
    return os.path.exists(file_path)

def process_keywords(list_keyword, geckodriver_path, firefox_binary_path, firefox_profile_path, main_directory=None):
    """
    Processes a list of keywords, searches Google, and saves the results.
    """
    driver = create_driver_with_profile(geckodriver_path, firefox_binary_path, firefox_profile_path)
    print("Make sure to accept the notifications prompt in the browser.")
    user_response = show_popup()
    if not user_response:
        logger.info("User cancelled the operation.")
        driver.quit()
        sys.exit(0)

    for keyword, search_term in list_keyword.items():
        if check_if_json_exists(keyword, main_directory):
            logger.info(f"Skipping '{keyword}' as results already exist.")
            continue

        logger.info(f"Searching for: {keyword}")
        try:
            top_urls = search_google_and_extract_urls(driver, search_term)
        except Exception as e:
            continue
        save_results_to_json(keyword, search_term, top_urls, main_directory)

        logger.info(f"Top URLs for '{keyword}':")
        for i, url in enumerate(top_urls):
            logger.info(f"{i+1}. {url}")
        logger.info("-" * 30)

    driver.quit()

if __name__ == "__main__":
    geckodriver_path = r"D:\\geckodrive\\geckodriver.exe"
    firefox_binary_path = r"C:\\Program Files\\Mozilla Firefox\\firefox.exe"
    firefox_profile_path = r"C:\\Users\\balan\\AppData\\Roaming\\Mozilla\\Firefox\\Profiles\\ssjd4eo7.default-release"
    list_keyword = {
        "Jeong_J_2019": "Brain Sci",
        "Yuan_D_2023": "Rev Sci Instrum"
    }

    main_directory = None  # Specify a path here to save results in a specific directory, or leave as None
    process_keywords(list_keyword, geckodriver_path, firefox_binary_path, firefox_profile_path, main_directory)
