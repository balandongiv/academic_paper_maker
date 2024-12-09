import logging
import os
import time
from datetime import datetime

import pandas as pd
import yaml
from dotenv import load_dotenv
from openai import OpenAI
from research_filter.agent_helper import combine_role_instruction
# Initialize logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)


def load_env():
    """Load environment variables."""
    load_dotenv()

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

def get_info_ai(abstract, instruction, client,model_name="gpt-4o-mini"):
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
            {"role": "user", "content": abstract}
        ]
    )

    try:
        output = completion.choices[0].message.content.strip()
        if output.lower() == 'true':
            return 'Related'
        elif output.lower() == 'false':
            return 'Not Related'
        else:
            return 'Uncertain'
    except Exception as e:
        return f"Error: {e}"


def process_dataframe(df, instruction, client,model_name):
    """
    Process a DataFrame by applying the get_info_ai function to the 'abstract' column.

    Args:
        df (pd.DataFrame): The input DataFrame.
        instruction (str): The instruction for the AI.
        client (OpenAI): The initialized OpenAI client.

    Returns:
        pd.DataFrame: The updated DataFrame with a new column containing AI outputs.
    """
    df["ai_output"] = df["abstract"].apply(lambda abstract: get_info_ai(abstract, instruction, client,model_name=model_name))
    return df



def generate_new_filename(file_path):
    # Extract the file name without extension
    base_name = os.path.splitext(os.path.basename(file_path))[0]

    # Get the current timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Create the new file name
    new_filename = f"corono_discharge_updated_{timestamp}"
    return new_filename

def main():
    """Main function to execute the script."""
    start_time = time.time()
    logger.info("Script execution started.")

    try:
        # Define placeholders
        csv_path = "../research_filter/eeg_based_fatigue_classification_trends_new_2024.xlsx"
        placeholders = {
            "topic": "fatigue or drowsiness classification and detection using machine learning techniques",
            # "topic": "Partial discharge or corona discharge classification and detection using machine learning techniques",
        }

        # Load environment variables
        logger.info("Loading environment variables.")
        load_env()

        # Load YAML configuration
        yaml_path = "agents_partial_discharge.yaml"
        logger.info(f"Loading YAML configuration from {yaml_path}.")
        config = load_yaml(yaml_path)

        # Combine YAML fields into role instruction
        agent_name = 'abstract_partial_discharge_sorter'
        logger.info(f"Combining role instruction for agent: {agent_name}.")


        role_instruction = combine_role_instruction(config, placeholders, agent_name)

        # Initialize OpenAI client
        logger.info("Initializing OpenAI client.")
        client = initialize_openai_client()

        # Load CSV data
        logger.info(f"Loading CSV data from {csv_path}.")
        model_name = "gpt-4o-mini"
        df = pd.read_excel(csv_path)
        # df = df.head(2)
        # Process DataFrame
        logger.info("Processing DataFrame.")
        updated_df = process_dataframe(df, role_instruction, client, model_name)

        # Generate new filenames
        logger.info("Generating new filenames.")
        new_filename = generate_new_filename(csv_path)
        output_path_csv = f"../research_filter/{new_filename}.csv"
        output_path_xlsx = f"../research_filter/{new_filename}.xlsx"

        # Save the updated DataFrame
        logger.info(f"Saving updated DataFrame to {output_path_csv} and {output_path_xlsx}.")
        updated_df.to_excel(output_path_xlsx, index=False)
        updated_df.to_csv(output_path_csv, index=False)

        logger.info("Script execution completed successfully.")
    except Exception as e:
        logger.error(f"An error occurred: {e}", exc_info=True)
    finally:
        elapsed_time = time.time() - start_time
        logger.info(f"Total execution time: {elapsed_time:.2f} seconds.")


if __name__ == "__main__":
    main()
