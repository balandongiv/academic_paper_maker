import logging
import sys
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

    all_url=get_search_results_from_page_source(page_source, num_results)
    valid_urls = extract_valid_urls(all_url)
    return valid_urls


def main(list_keyword, geckodriver_path, firefox_binary_path, firefox_profile_path):
    """
    Main function to perform Google searches for a list of keywords
    using an existing Firefox profile and save the extracted URLs.
    """
    driver = create_driver_with_profile(geckodriver_path, firefox_binary_path, firefox_profile_path)
    all_search_results = {}
    driver.get(f"https://www.google.com/search?q=python")



    user_response = show_popup()
    if not user_response:
        logger.info("User cancelled the operation.")
        driver.quit()
        sys.exit(0)


    for keyword in list_keyword:
        print(f"Searching for: {keyword}")
        top_urls = search_google_and_extract_urls(driver, keyword)
        all_search_results[keyword] = top_urls
        print(f"Top URLs for '{keyword}':")
        for i, url in enumerate(top_urls):
            print(f"{i+1}. {url}")
        print("-" * 30)

    driver.quit()
    return all_search_results

if __name__ == "__main__":
    geckodriver_path = r"D:\geckodrive\geckodriver.exe"
    firefox_binary_path = r"C:\Program Files\Mozilla Firefox\firefox.exe"
    firefox_profile_path = r"C:\Users\balan\AppData\Roaming\Mozilla\Firefox\Profiles\ssjd4eo7.default-release"
    list_keyword = {
        "Subasi_A_2022": "EEG-Based Driver Fatigue Detection Using FAWT and Multiboosting Approaches",
        "Abidi_A_2022": "Automatic Detection of Drowsiness in EEG Records Based on Machine Learning Approaches"
    }

    search_results = main(list_keyword, geckodriver_path, firefox_binary_path, firefox_profile_path)
    print("\nAll search results:")
    for keyword, urls in search_results.items():
        print(f"Keyword: {keyword}")
        for i, url in enumerate(urls):
            print(f"  {i+1}. {url}")