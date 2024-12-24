from pdf_downloader import setup_driver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from pdf_downloader import setup_driver


def download_pdf(driver, url, download_folder):
    """
    Navigate to the URL and download the PDF file.
    """

# Define paths and folder
geckodriver_path = r'D:\geckodrive\geckodriver.exe'
firefox_binary_path = r'C:\Program Files\Mozilla Firefox\firefox.exe'
download_folder = r"C:\\Users\\balan\\Downloads"

# List of URLs to download PDFs from
springer_urls = [
    "https://www.sciencedirect.com/science/article/pii/S0028393218305967?via%3Dihub",
    # "https://link.springer.com/article/10.1007/s00521-022-07466-0",
    # Add more URLs as needed
]

# Setup the WebDriver
driver = setup_driver(geckodriver_path, firefox_binary_path, download_folder)
url=springer_urls[0]
driver.get(url)
print("Navigated to:", driver.title)
# Step 2: Perform login and access via another organization dynamically
try:
    # Wait for the list item with class "SelectAnotherInstitution" to be present
    institution_element = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CLASS_NAME, "SelectAnotherInstitution"))
    )

    # Locate the anchor (<a>) tag within the list item and extract its href attribute
    access_link = institution_element.find_element(By.TAG_NAME, "a")
    access_href = access_link.get_attribute("href")
    print("Found access link:", access_href)

    # Click on the access link
    access_link.click()
    print("Clicked 'Access through another organization'")

    # Wait for and accept cookies
    WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.ID, "onetrust-accept-btn-handler"))
    ).click()
    print("Accepted all cookies")

    # Additional steps after clicking the link, e.g., entering organizational email
    org_input = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, "your-input-field-id"))  # Replace with the actual ID or locator
    )
    org_input.send_keys("universiti malaysia sabah")
    print("Entered organizational email: universiti malaysia sabah")

    # Submit the form or proceed to the next step, if needed
    org_input.submit()
    print("Submitted the organizational email")

except Exception as e:
    print("An error occurred during Step 2:", str(e))

