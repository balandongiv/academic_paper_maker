import os
import requests
from bs4 import BeautifulSoup

def download_pdf(pdf_url, download_folder):
    """
    Download a PDF from a given URL and save it to the specified folder.

    Args:
        pdf_url (str): The URL of the PDF to download.
        download_folder (str): The folder where the PDF should be saved.
    """
    response = requests.get(pdf_url, stream=True)
    if response.status_code == 200:
        pdf_name = os.path.basename(pdf_url)
        pdf_path = os.path.join(download_folder, pdf_name)
        with open(pdf_path, 'wb') as pdf_file:
            for chunk in response.iter_content(chunk_size=1024):
                pdf_file.write(chunk)
        print(f"Downloaded PDF: {pdf_path}")
    else:
        print(f"Failed to download PDF: {pdf_url}")

def check_and_download_pdf(html_file_path, search_text, download_folder):
    """
    Check if the HTML file contains the specified text and download any PDF linked in the file if the text is found.

    Args:
        html_file_path (str): Path to the HTML file.
        search_text (str): The text to search for in the HTML content.
        download_folder (str): The folder where the PDF should be saved.
    """
    # Ensure the download folder exists
    if not os.path.exists(download_folder):
        os.makedirs(download_folder)

    # Read the HTML content
    with open(html_file_path, 'r', encoding='utf-8') as file:
        html_content = file.read()

    # Parse the HTML content
    soup = BeautifulSoup(html_content, 'html.parser')

    # Check if the search text exists in the HTML content
    if search_text in soup.get_text():
        print(f"Text found: {search_text}")

        # Find all <a> tags with href ending in .pdf
        pdf_links = soup.find_all('a', href=lambda href: href and href.endswith('.pdf'))

        for link in pdf_links:
            pdf_url = link['href']

            # Handle relative URLs
            if not pdf_url.startswith('http'):
                pdf_url = os.path.join(os.path.dirname(html_file_path), pdf_url)

            # Download the PDF
            download_pdf(pdf_url, download_folder)
    else:
        print(f"Text not found: {search_text}")

if __name__ == "__main__":
    # Define the HTML file path, search text, and download folder
    html_file_path = "../download_pdf/find_title.htm"
    search_text = "Automatic detection of drowsiness in EEG records based on multimodal analysis"
    download_folder = "downloaded_pdfs"

    # Run the function
    check_and_download_pdf(html_file_path, search_text, download_folder)
