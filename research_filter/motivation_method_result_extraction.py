
import json
import logging
import os
import time

import pandas as pd
from PyPDF2 import PdfReader  # Make sure PyPDF2 is installed
from dotenv import load_dotenv
from tqdm import tqdm

from research_filter.agent_helper import combine_role_instruction, load_yaml
from research_filter.helper import load_partial_results_from_json, initialize_openai_client, generate_new_filename, \
    save_result_to_json, update_df_from_json, cleanup_json_files

# Initialize logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)


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
                {"role": "user", "content": abstract},

            ],
            response_format= { "type":"json_object" }
        )
    except Exception as e:
        return f"Error when processing {bibtex_val}: {e}"
    try:
        output = completion.choices[0].message.content

        return output
    except Exception as e:
        return f"Error when processing {bibtex_val}: {e}"

def main():
    start_time = time.time()
    logger.info("Script execution started.")
    placeholders = {
        "topic": "EEG-based fatigue classification",
        "topic_context": "neurophysiological analysis"
    }
    model_name = "gpt-4o-mini"
    # model_name = "gpt-4o"
    cleanup_json=False
    csv_path = "database/eeg_review.xlsx"
    agent_name = 'concept_and_technique'
    column_name = 'concept_and_technique'
    load_dotenv()
    yaml_path = "agent/agent_ml.yaml"
    logger.info(f"Loading YAML configuration from {yaml_path}.")
    config = load_yaml(yaml_path)
    logger.info("Generating new filenames.")
    new_filename = generate_new_filename(csv_path)
    output_path_xlsx = f"../research_filter/{new_filename}.xlsx"
    # methodology_json_folder = r"C:\Users\balan\OneDrive - ums.edu.my\research_related\0 eeg_trend_till24\eeg_review\methodology"
    methodology_json_folder = r"C:\Users\balan\OneDrive - ums.edu.my\research_related\0 eeg_trend_till24\eeg_review\concept_and_technique"
    main_folder=r'C:\Users\balan\OneDrive - ums.edu.my\research_related\0 eeg_trend_till24\eeg_review'
    # Ensure temp folder exists
    if not os.path.exists(methodology_json_folder):
        os.makedirs(methodology_json_folder)

    try:
        logger.info(f"Combining role instruction for agent: {agent_name}.")
        role_instruction = combine_role_instruction(config, placeholders, agent_name)

        # Initialize OpenAI client
        logger.info("Initializing OpenAI client.")
        client = initialize_openai_client()


        # Load Excel data
        logger.info(f"Loading Excel data from {csv_path}.")
        df = pd.read_excel(csv_path)

        # First, update DF from any existing JSON results (previous partial runs)
        logger.info("Updating DataFrame from existing JSON files if available.")
        df = load_partial_results_from_json(df, methodology_json_folder)

        non_nan_df = df[~df['pdf_name'].isna()]

        # Process only the NaN rows and save results to JSON
        logger.info("Processing rows with NaN ai_output.")
        for i, row in tqdm(non_nan_df.iterrows(), total=len(non_nan_df)):
            pdf_filename = row.get('pdf_name', '')
            bibtex_val = row.get('bibtex', None)
            pdf_path=os.path.join(main_folder,pdf_filename)
            pdf_text = ""
            json_path = os.path.join(methodology_json_folder, f"{bibtex_val}.json")
            if not pdf_filename or pd.isna(bibtex_val):
                continue
            # status=False
            if os.path.exists(json_path):
                # The file has been process, we will skip
                continue

            if pdf_path and os.path.exists(pdf_path):
                try:
                    reader = PdfReader(pdf_path)
                    for page in reader.pages:
                        pdf_text += page.extract_text() + "\n"
                    status=True
                except Exception as e:
                    pdf_text = f"Error reading PDF: {e}"
                    status=False
            elif pdf_filename=='no_pdf':
                pdf_text = row.get('abstract', None)
                status=True
            else:
                continue
            if status:
                ai_output = get_info_ai(bibtex_val,pdf_text, role_instruction, client, model_name=model_name)
                # Parse the raw JSON string into a Python dictionary
                try:
                    parsed_data = json.loads(ai_output)
                except json.JSONDecodeError:
                    parsed_data = {
                        "methodology": {
                            "error_msg": f"error text {ai_output}"
                        }
                    }

            else:

                parsed_data = {
                    "methodology": {
                        "error_msg": f"error text {pdf_text}"
                    }
                }

            save_result_to_json(bibtex_val, parsed_data, json_path,column_name)

        # After all processing is done, update DataFrame from the JSON files again
        logger.info("Updating DataFrame from newly created JSON files.")
        updated_df = update_df_from_json(df, methodology_json_folder,column_name)




        if cleanup_json:
            # If we reach here without exceptions, we assume all good
            # Delete the JSON files as requested
            logger.info("All processes completed successfully. Cleaning up JSON files.")
            cleanup_json_files(updated_df, methodology_json_folder)

        # Save the updated DataFrame back to Excel
        logger.info(f"Saving updated DataFrame back to {csv_path}.")
        # updated_df.to_excel(csv_path, index=False)

        logger.info("Script execution completed successfully.")

    except Exception as e:
        logger.error(f"An error occurred: {e}", exc_info=True)
        # On error, do not delete JSON files - they will help resume next time.
    finally:
        elapsed_time = time.time() - start_time
        logger.info(f"Total execution time: {elapsed_time:.2f} seconds.")

if __name__ == "__main__":
    main()
