import logging
import sys
import os
'''
This code will be use to search the academic title using google search engine
'''


import json
import random
from time import sleep
from bs4 import BeautifulSoup
from download_pdf.browse_internet.firefox_setting import create_driver_with_profile
from download_pdf.browse_internet.urlcleaning import extract_valid_urls
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
    driver.get(f"https://www.google.com/search?q={keyword}")
    sleep(2)  # Allow time for the page to load

    # Get the page source
    page_source = driver.page_source

    # Delegate URL extraction to helper function
    all_urls = get_search_results_from_page_source(page_source, num_results)
    valid_urls = extract_valid_urls(all_urls)

    # Randomized sleep to avoid robotic detection
    random_sleep_time = random.uniform(2, 5)  # Random sleep between 2 and 5 seconds
    sleep(random_sleep_time)

    return valid_urls

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
        top_urls = search_google_and_extract_urls(driver, search_term)
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
        "Subasi_A_2022": "EEG-Based Driver Fatigue Detection Using FAWT and Multiboosting Approaches",
        "Abidi_A_2022": "Automatic Detection of Drowsiness in EEG Records Based on Machine Learning Approaches"
    }

    main_directory = None  # Specify a path here to save results in a specific directory, or leave as None
    process_keywords(list_keyword, geckodriver_path, firefox_binary_path, firefox_profile_path, main_directory)
