import logging
import os
import time
import urllib.parse
import urllib.parse

import fitz
import requests
import yaml
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from duckduckgo_search import DDGS
from googlesearch import search
from openai import OpenAI

from research_filter.agent_helper import combine_role_instruction

# Initialize logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)


logger.info("Loading environment variables.")

def initialize_openai_client():
    load_env()
    """Initialize the OpenAI client using the API key from environment variables."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OpenAI API key not found in environment variables.")
    os.environ["OPENAI_API_KEY"] = api_key
    return OpenAI()

def load_env():
    """Load environment variables."""
    load_dotenv()

def get_info_ai(first_page_content, instruction, client,model_name="gpt-4o-mini"):
    """
    Get AI response for the given abstract using the provided instruction.

    Args:
        abstract (str): The abstract text to process.
        instruction (str): The instruction or prompt for the AI.
        client (OpenAI): The initialized OpenAI client.

    Returns:
        str: The AI's response.
    """
    completion = client.chat.completions.create(
        model=model_name,
        messages=[
            {"role": "system", "content": instruction},
            {"role": "user", "content": first_page_content}
        ]
    )

    try:
        output = completion.choices[0].message.content.strip()
        return output
    except Exception as e:
        return f"Error: {e}"


def download_pdf(pdf_url, save_path="."):
    """
    Download the PDF from the given URL and save it to the specified path.
    """
    # pdf_name = pdf_url.split('/')[-1]
    # full_path = f"{save_path}/{pdf_name}"
    print(f"Downloading PDF: {pdf_url} to {save_path}")
    try:
        response = requests.get(pdf_url)
        response.raise_for_status()
        with open(save_path, 'wb') as f:
            f.write(response.content)
        print(f"Saved PDF: {save_path}")
        return save_path
    except Exception as e:
        print(f"Error downloading PDF {pdf_url}: {e}")
        return None

def search_with_google(query, max_attempts=3):
    """
    Search for the query using Google with retry logic.
    """
    for attempt in range(max_attempts):
        try:
            return [url for url in search(query, tld="co.in", num=10, stop=10, pause=2)]
        except Exception as e:
            print(f"Error using Google on attempt {attempt + 1}: {e}")
            time.sleep(5)  # Cooling period
    print("Google search failed after multiple attempts.")
    return []

def search_with_ddgs(query, max_attempts=5, delay=5):
    """
    Search for the query using DuckDuckGo Search with retry logic.
    """
    for attempt in range(max_attempts):
        try:
            results = DDGS().text(query, max_results=10)
            return [result['href'] for result in results]
        except Exception as e:
            print(f"Error using DDGS on attempt {attempt + 1}: {e}")
            time.sleep(delay)  # Delay between attempts
    print("DuckDuckGo search failed after multiple attempts.")
    return []



def download_and_validate_pdf(pdf_url, save_path,  client, role_instruction,model_name):
    """
    Download a PDF and validate its relevance using AI.
    """
    try:
        pdf_path = download_pdf(pdf_url, save_path)
        pdf_document = fitz.open(pdf_path)
        first_page_content = pdf_document[0].get_text("text")

        # Check relevance using AI
        # instruction = (f"Does the following text of the first page extracted have the title {paper_title}? "
        #                f"Return Boolean True if relevant and False if not relevant.")
        is_relevant = get_info_ai(first_page_content, role_instruction, client, model_name=model_name)

        if is_relevant == "False":
            pdf_document.close()
            os.remove(pdf_path)
            status='FAIL'
            return status
        else:
            status='SUCCESS'
            return status
    except Exception as e:
        status='FAIL'
        print(f"Error downloading or validating PDF from {pdf_url}: {e}")
        return status

def extract_pdf_links(html_content, base_url):
    """
    Extract all PDF links from the given HTML content.
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    pdf_links = []
    for link in soup.find_all('a', href=True):
        href = urllib.parse.urljoin(base_url, link['href'])
        if href.lower().endswith('.pdf'):
            pdf_links.append(href)
    return pdf_links

def process_single_url(url, save_path, paper_title, client, role_instruction,model_name="gpt-4o-mini"):
    """
    Process a single URL to find a valid PDF.
    """
    if url.lower().endswith('.pdf'):
        status =download_and_validate_pdf(url,  save_path,  client, role_instruction,model_name)
        return status
    else:
        try:
            response = requests.get(url)
            response.raise_for_status()
            pdf_links = extract_pdf_links(response.text, url)
            for pdf_url in pdf_links:
                status = download_and_validate_pdf(pdf_url,  save_path,  client, role_instruction,model_name)
                if status == 'SUCCESS':
                    return status
        except Exception as e:

            print(f"Error processing {url}: {e}")
            return 'FAIL'

def process_urls(urls, save_path, client, paper_title,role_instruction):
    """
    Process a list of URLs to find and download a valid PDF.
    """

    for url in urls:
        print(f"\nProcessing URL: {url}")
        status = process_single_url(url, save_path, paper_title, client,role_instruction)
        if status=='SUCCESS':
           return status


def load_yaml(file_path):
    """Load a YAML file and return its contents."""
    with open(file_path, "r") as file:
        return yaml.safe_load(file)

def find_and_download_pdf(query, save_path=".",paper_title=None):
    """
    Main function to find and download a PDF for the given query.
    """
    # Load YAML configuration
    yaml_path = "../research_filter/agents.yaml"
    logger.info(f"Loading YAML configuration from {yaml_path}.")
    config = load_yaml(yaml_path)

    # Combine YAML fields into role instruction
    agent_name = 'pdf_align_with_title'
    logger.info(f"Combining role instruction for agent: {agent_name}.")


    placeholders = {
        "paper_title": 'Pattern recognition of partial discharge by using simplified fuzzy ARTMAP',
    }

    role_instruction = combine_role_instruction(config, placeholders, agent_name)

    print(f"Searching for: {query}")
    # all_url=[]
    # Try Google first
    urls = search_with_google(query)
    if not urls:
        # Fall back to DuckDuckGo if Google fails
        urls = search_with_ddgs(query)

    if not urls:
        return "I have used Google and DuckDuckGo despite multiple attempts, but still unable to find the PDF."
    # urls=['https://link.springer.com/article/10.1007/s13202-024-01777-9']
    # print("\nFound URLs:")
    # for url in urls:
    #     print(url)






    client = initialize_openai_client()
    status = process_urls(urls, save_path,client,paper_title,role_instruction)

    # file_size = os.path.getsize(pdf_path)
    # file_size_kb = file_size / 1024
    # if file_size_kb < 10:
    #     return f"Downloaded file '{pdf_path}' is too small: {file_size_kb} KB"
    if status=='SUCCESS':
        return f"PDF successfully downloaded: {paper_title}"
    else:

        considered_urls = "\n".join(urls)
        return f"No PDF found. The following URLs were considered:\n{considered_urls}"

# Example usage of the function
if __name__ == "__main__":
    # query = "Identification of contradictory patterns in experimental datasets for the development of models for electrical cables diagnostics"
    # query = "Pattern recognition of partial discharge by using simplified fuzzy ARTMAP"
    # Define the folder and filename
    query = "Pattern recognition of partial discharge by using simplified fuzzy ARTMAP"
    filename = "_".join(query.split()) + ".pdf"
    folder_path = r"C:\Users\balan\IdeaProjects\crewai-flows-crash-course\research_filter\downloads"

    # Check if the downloads folder exists, and create it if not
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)

    # Construct the output path
    output_path = os.path.join(folder_path, filename)

    # Normalize the path to ensure it's in the correct format
    output_path = os.path.normpath(output_path)

    remark = find_and_download_pdf(query, output_path)
    print(remark)
