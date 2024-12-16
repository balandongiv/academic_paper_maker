import json
import logging
import os
import time
from datetime import datetime

import pandas as pd
import yaml
from dotenv import load_dotenv
from openai import OpenAI
from research_filter.agent_helper import combine_role_instruction, load_yaml,validate_json_data



# Initialize logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

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

def get_info_ai(bibtex_val,abstract, instruction, client, model_name="gpt-4o-mini"):
    """
    Get AI response for the given abstract using the provided instruction.
    Returns True, False, or 'Uncertain'.
    """

    try:
        completion = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": instruction},
                {"role": "user", "content": abstract}
            ]
        )
    except Exception as e:
        return f"Error when processing {bibtex_val}: {e}"
    try:
        output = completion.choices[0].message.content.strip()
        if output.lower() == 'true':
            return "relevance"
        elif output.lower() == 'false':
            return "not_relevance"
        else:
            return 'Uncertain'
    except Exception as e:
        return f"Error when processing {bibtex_val}: {e}"

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




def save_result_to_json(bibtex_val, ai_output, temp_folder):
    """
    Save the AI result to a JSON file named after the 'bibtex' column.
    """
    if pd.isna(bibtex_val):
        # If bibtex is not available, skip saving.
        return
    json_path = os.path.join(temp_folder, f"{bibtex_val}.json")
    data = {'ai_output': ai_output}
    with open(json_path, "w") as f:
        json.dump(data, f, indent=2)

def update_df_from_json(df, temp_folder):
    """
    After all processing is completed, update the DataFrame from the JSON files again to ensure
    all processed rows are reflected in the DataFrame.
    """
    for i, row in df.iterrows():
        bibtex_val = row.get('bibtex', None)
        if pd.notna(bibtex_val):
            json_path = os.path.join(temp_folder, f"{bibtex_val}.json")
            if os.path.exists(json_path):
                try:
                    with open(json_path, "r") as f:
                        data = json.load(f)
                    # Update the row with the saved ai_output if available
                    if 'ai_output' in data:
                        df.at[i, 'ai_output'] = data['ai_output']
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

def main():
    start_time = time.time()
    logger.info("Script execution started.")
    placeholders = {
        "topic": "EEG-based fatigue classification",
        "topic_context": "neurophysiological analysis"
    }
    csv_path = "eeg_test_simple_with_bibtex_v1.xlsx"
    agent_name = 'abstract_filter_fatigue_eeg'
    load_dotenv()
    yaml_path = "agents_fatigue_driving.yaml"
    logger.info(f"Loading YAML configuration from {yaml_path}.")
    config = load_yaml(yaml_path)
    logger.info("Generating new filenames.")
    new_filename = generate_new_filename(csv_path)
    output_path_xlsx = f"../research_filter/{new_filename}.xlsx"
    temp_folder = "temp_json"

    # Ensure temp folder exists
    if not os.path.exists(temp_folder):
        os.makedirs(temp_folder)

    try:
        logger.info(f"Combining role instruction for agent: {agent_name}.")
        role_instruction = combine_role_instruction(config, placeholders, agent_name)

        # Initialize OpenAI client
        logger.info("Initializing OpenAI client.")
        client = initialize_openai_client()
        model_name = "gpt-4o-mini"

        # Load Excel data
        logger.info(f"Loading Excel data from {csv_path}.")
        df = pd.read_excel(csv_path)

        # First, update DF from any existing JSON results (previous partial runs)
        logger.info("Updating DataFrame from existing JSON files if available.")
        df = load_partial_results_from_json(df, temp_folder)

        # Separate rows that need processing (NaN in ai_output) and already processed ones
        ai_related_nan_df = df[df['ai_output'].isna()]
        non_nan_df = df[~df['ai_output'].isna()]

        # Process only the NaN rows and save results to JSON
        logger.info("Processing rows with NaN ai_output.")
        for i, row in ai_related_nan_df.iterrows():
            abstract = row.get('abstract', '')
            bibtex_val = row.get('bibtex', None)
            # If no abstract or no bibtex, skip
            if not abstract or pd.isna(bibtex_val):
                continue
            # status=False

            ai_output = get_info_ai(bibtex_val,abstract, role_instruction, client, model_name=model_name)
            # validate_json_data(ai_output, role_instruction)
            # Save AI output to JSON, do not update DF yet
            # validated_output=parse_ai_output(ai_output)
            save_result_to_json(bibtex_val, ai_output, temp_folder)

        # After all processing is done, update DataFrame from the JSON files again
        logger.info("Updating DataFrame from newly created JSON files.")
        updated_df = update_df_from_json(df, temp_folder)

        # If we reach here without exceptions, we assume all good
        # Delete the JSON files as requested
        logger.info("All processes completed successfully. Cleaning up JSON files.")
        cleanup_json_files(updated_df, temp_folder)

        # Save the updated DataFrame back to Excel
        logger.info(f"Saving updated DataFrame back to {csv_path}.")
        updated_df.to_excel(csv_path, index=False)

        logger.info("Script execution completed successfully.")

    except Exception as e:
        logger.error(f"An error occurred: {e}", exc_info=True)
        # On error, do not delete JSON files - they will help resume next time.
    finally:
        elapsed_time = time.time() - start_time
        logger.info(f"Total execution time: {elapsed_time:.2f} seconds.")

if __name__ == "__main__":
    main()
