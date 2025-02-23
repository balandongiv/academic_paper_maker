'''

This code aim to add bibtex key to existing json file
'''

import os
import json

# Define input and output directories
input_dir = r'G:\My Drive\research_related\0 eeg_trend_till24\eeg_review\methodology_gap_extractor\json_output\gemini-2.0-flash-thinking-exp-01-21'
output_dir = r'G:\My Drive\research_related\0 eeg_trend_till24\eeg_review\methodology_gap_extractor\json_output\gemini-2.0-flash-thinking-exp-01-21_updated'

# Ensure output directory exists
os.makedirs(output_dir, exist_ok=True)

# Process all JSON files in the input directory
for filename in os.listdir(input_dir):
    if filename.endswith(".json"):
        file_path = os.path.join(input_dir, filename)

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
        output_path = os.path.join(output_dir, filename)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(updated_data, f, indent=2, ensure_ascii=False)

print("JSON files have been updated and saved in the new directory.")
