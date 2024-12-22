from selenium import webdriver
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.firefox.firefox_profile import FirefoxProfile

from time import sleep

def create_driver_with_profile(geckodriver_path, firefox_binary_path, firefox_profile_path):
    """
    Creates a Firefox WebDriver using an existing profile.
    """
    options = FirefoxOptions()
    options.binary_location = firefox_binary_path
    profile = FirefoxProfile(firefox_profile_path)
    options.profile = profile  # Set the profile in options
    service = FirefoxService(executable_path=geckodriver_path)
    driver = webdriver.Firefox(service=service, options=options)
    return driver

def search_google_and_extract_urls(driver, keyword, num_results=10):
    """
    Searches Google for a given keyword and extracts the top N result URLs.
    """
    driver.get(f"https://www.google.com/search?q={keyword}")
    sleep(2)  # Allow time for the page to load

    urls = []
    search_results = driver.find_elements("xpath", "//div[@class='g']")  # Common container for search results

    for i, result in enumerate(search_results):
        if i >= num_results:
            break
        try:
            link_element = result.find_element("xpath", ".//a")
            url = link_element.get_attribute("href")
            urls.append(url)
        except Exception as e:
            print(f"Error extracting URL from result {i+1}: {e}")
    return urls

def main(list_keyword, geckodriver_path, firefox_binary_path, firefox_profile_path):
    """
    Main function to perform Google searches for a list of keywords
    using an existing Firefox profile and save the extracted URLs.
    """
    driver = create_driver_with_profile(geckodriver_path, firefox_binary_path, firefox_profile_path)
    all_search_results = {}

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
    list_keyword = ['eeg', 'emg']

    search_results = main(list_keyword, geckodriver_path, firefox_binary_path, firefox_profile_path)
    print("\nAll search results:")
    for keyword, urls in search_results.items():
        print(f"Keyword: {keyword}")
        for i, url in enumerate(urls):
            print(f"  {i+1}. {url}")