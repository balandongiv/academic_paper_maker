import logging
import os

import fitz
from dotenv import load_dotenv
from openai import OpenAI

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




def xtest_download_and_validate_pdf(pdf_path, paper_title, client, model_name="gpt-4o-mini"):

    # pdf_path = download_pdf(pdf_url, save_path)
    pdf_document = fitz.open(pdf_path)
    first_page_content = pdf_document[0].get_text("text")

    # Check relevance using AI
    instruction = (f"Does the following text of the first page extracted have the title {paper_title}? "
                       f"Return Boolean True if relevant and False if not relevant.")
    is_relevant = get_info_ai(first_page_content, instruction, client, model_name=model_name)

    return is_relevant

# Example usage of the function
if __name__ == "__main__":
    # query = "Identification of contradictory patterns in experimental datasets for the development of models for electrical cables diagnostics"
    # query = "Identification of contradictory patterns in experimental datasets for the development of models for electrical cables diagnostics"
    save_path = "./downloads"  # Specify your save path here
    paper_title="Identification of contradictory patterns in experimental datasets for the development of models for electrical cables diagnostics"
    # remark = find_and_download_pdf(query, save_path)
    client = initialize_openai_client()
    pdf_path=r'C:\Users\balan\IdeaProjects\crewai-flows-crash-course\research_filter\downloads\s13202-024-01777-9.pdf'
    remark=xtest_download_and_validate_pdf(pdf_path, paper_title, client, model_name="gpt-4o-mini")
    print(remark)
