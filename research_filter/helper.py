import json
import logging
import os
from datetime import datetime

import pandas as pd
import yaml
from PyPDF2 import PdfReader  # Make sure PyPDF2 is installed
from openai import OpenAI

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)
def extract_pdf_text(pdf_path):
    pdf_text=''
    try:
    #
        reader = PdfReader(pdf_path)
        for page in reader.pages:
            pdf_text += page.extract_text() + "\n"
        status=True
    except Exception as e:
        pdf_text = f"Error reading PDF: {e}"
        status=False


    return pdf_text,status

def load_yaml(file_path):
    """Load a YAML file and return its contents."""
    with open(file_path, "r") as file:
        return yaml.safe_load(file)


def initialize_openai_client():
    """Initialize the OpenAI client using the API key from environment variables."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OpenAI API key not found in environment variables.")
    os.environ["OPENAI_API_KEY"] = api_key
    return OpenAI()



def generate_new_filename(file_path):
    # Extract the file name without extension
    base_name = os.path.splitext(os.path.basename(file_path))[0]
    # Get the current timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    # Create the new file name
    new_filename = f"{base_name}_{timestamp}"
    return new_filename

def load_partial_results_from_json(df, temp_folder):
    """
    Load previously saved partial results from JSON files and update the DataFrame accordingly.
    Instead of checking every row, we load all JSON files first and then update rows that match.
    """
    if not os.path.isdir(temp_folder):
        return df  # If temp_folder doesn't exist, just return df as is.

    # List all JSON files in the directory
    json_files = [f for f in os.listdir(temp_folder) if f.endswith(".json")]

    # If there are no JSON files, return df unchanged
    if not json_files:
        return df

    # Create a mapping of bibtex -> ai_output from the JSON files
    bibtex_to_output = {}
    for file_name in json_files:
        json_path = os.path.join(temp_folder, file_name)
        bibtex_val = os.path.splitext(file_name)[0]  # Filename without extension as bibtex key
        try:
            with open(json_path, "r") as f:
                data = json.load(f)
            ai_output = data.get("ai_output")
            bibtex_to_output[bibtex_val] = ai_output
        except Exception as e:
            logger.warning(f"Unable to load {json_path}: {e}")

    # Update the DataFrame where bibtex matches the keys found in the folder
    # Use 'apply' for vectorized operation
    df['ai_output'] = df.apply(
        lambda row: bibtex_to_output[row['bibtex']] if row['bibtex'] in bibtex_to_output else row['ai_output'],
        axis=1
    )

    return df




def save_result_to_json(bibtex_val, ai_output, json_path,column_name):
    """
    Save the AI result to a JSON file named after the 'bibtex' column.
    """
    if pd.isna(bibtex_val):
        # If bibtex is not available, skip saving.
        return


    # data = {column_name: ai_output}
    with open(json_path, "w") as f:
        json.dump(ai_output, f, indent=2)

def update_df_from_json(df, temp_folder,column_name):
    """
    After all processing is completed, update the DataFrame from the JSON files again to ensure
    all processed rows are reflected in the DataFrame.
    """
    logger.info('Now we going to update the DataFrame from the JSON files')
    for i, row in df.iterrows():
        bibtex_val = row.get('bibtex', None)
        if pd.notna(bibtex_val):
            json_path = os.path.join(temp_folder, f"{bibtex_val}.json")
            if os.path.exists(json_path):
                try:
                    with open(json_path, "r") as f:
                        data = json.load(f)
                    # Update the row with the saved ai_output if available
                    # if column_name in data:
                    df.at[i, column_name] = data
                except Exception as e:
                    logger.warning(f"Unable to re-load {json_path}: {e}")
    return df

def cleanup_json_files(df, temp_folder):
    """
    If all processes are successful, delete the corresponding JSON files.
    """
    for i, row in df.iterrows():
        bibtex_val = row.get('bibtex', None)
        if pd.notna(bibtex_val):
            json_path = os.path.join(temp_folder, f"{bibtex_val}.json")
            if os.path.exists(json_path):
                try:
                    os.remove(json_path)
                except Exception as e:
                    logger.warning(f"Unable to delete {json_path}: {e}")
