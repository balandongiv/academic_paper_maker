'''

This code aim to add bibtex key to existing json file
'''

import os
import json
import logging
from tqdm import tqdm

# Configure logging
logging.basicConfig(
    level=logging.INFO,  # Change to DEBUG for more detailed logs
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("bibtex_updater.log"),  # Log file
        logging.StreamHandler()  # Print logs to console
    ]
)

# Define input and output directories

# Define input and output directories
# main_folder=r'G:\My Drive\research_related\0 eeg_trend_till24\eeg_review\methodology_gap_extractor\json_output'
# input_dir =os.path.join(main_folder, "gemini-2.0-flash-thinking-exp-01-21")
# output_dir = os.path.join(main_folder, "gemini-2.0-flash-thinking-exp-01-21_updated")
input_dir = r'G:\My Drive\research_related\corona_discharge\methodology_gap_extractor_partial_discharge\json_output\gemini-2.0-flash-thinking-exp-01-21'
output_dir = r'G:\My Drive\research_related\corona_discharge\methodology_gap_extractor_partial_discharge\json_output\gemini-2.0-flash-thinking-exp-01-21_updated'
os.makedirs(output_dir, exist_ok=True)
logging.info(f"Output directory ensured: {output_dir}")

# Get the list of JSON files
json_files = [f for f in os.listdir(input_dir) if f.endswith(".json")]
total_files = len(json_files)

if total_files == 0:
    logging.warning("No JSON files found in the input directory.")
else:
    logging.info(f"Found {total_files} JSON files to process.")

# Process all JSON files with tqdm progress bar
for filename in tqdm(json_files, desc="Processing JSON files", unit="file"):
    try:
        file_path = os.path.join(input_dir, filename)
        output_path = os.path.join(output_dir, filename)

        # Read JSON file
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Extract filename without extension for the "bibtex" key
        bibtex_value = os.path.splitext(filename)[0]

        # Insert the "bibtex" key before "introduction"
        updated_data = {"bibtex": bibtex_value}  # Start with the new key
        for key, value in data.items():
            updated_data[key] = value

        # Save the updated JSON to the output directory
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(updated_data, f, indent=2, ensure_ascii=False)

        logging.info(f"Processed: {filename}")

    except Exception as e:
        logging.error(f"Error processing {filename}: {e}")

logging.info("All JSON files have been updated and saved in the new directory.")