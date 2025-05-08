import json
import logging
import os
import shutil
from datetime import datetime

from tqdm import tqdm

# Configure the logger
logging.basicConfig(
    level=logging.INFO,  # Can be DEBUG, INFO, WARNING, ERROR, CRITICAL
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("process.log"),  # Log to a file
        logging.StreamHandler()              # Also log to the console
    ]
)

# Create a logger instance
logger = logging.getLogger(__name__)

def save_with_backup(df, csv_path):
    """
    Save the DataFrame to `csv_path`, backing up the original file with a timestamp before overwriting.
    """


    timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    backup_path = f"{os.path.splitext(csv_path)[0]}_backup_{timestamp}.xlsx"

    if os.path.exists(csv_path):
        shutil.copy2(csv_path, backup_path)
        logger.info(f"Backup saved to {backup_path}")
        logger.info("New CSV has been created, but a backup has been made.")
    else:
        logger.info("No original file found to back up. Creating new CSV.")

    logger.info(f"Saving updated DataFrame to {csv_path}")
    df.to_excel(csv_path, index=False)


def combine_json_files(input_directory, output_file):
    """
    Combine all JSON files in a directory into a single JSON array and save to output_file.
    Uses tqdm for progress and logging for status updates.

    Args:
        input_directory (str): Path to the folder containing JSON files.
        output_file (str): Path to save the combined JSON file.
    """
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    combined_data = []

    logging.info(f"Scanning directory: {input_directory}")
    try:
        files = [f for f in os.listdir(input_directory) if f.endswith(".json")]
    except FileNotFoundError:
        logging.error(f"Directory not found: {input_directory}")
        return

    if not files:
        logging.warning("No JSON files found.")
        return

    logging.info(f"Found {len(files)} JSON files. Starting to process...")

    for filename in tqdm(files, desc="Combining JSON files"):
        file_path = os.path.join(input_directory, filename)
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                data = json.load(file)
                combined_data.append(data)
                logging.debug(f"Loaded: {filename}")
        except json.JSONDecodeError as e:
            logging.warning(f"Skipping {filename} due to JSON decode error: {e}")
        except Exception as e:
            logging.error(f"Error processing file {filename}: {e}")

    try:
        with open(output_file, 'w', encoding='utf-8') as outfile:
            json.dump(combined_data, outfile, indent=2)
        logging.info(f"Combined JSON saved to: {output_file}")
    except Exception as e:
        logging.error(f"Failed to write combined JSON: {e}")
