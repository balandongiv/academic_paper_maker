'''

This script is used to extract data from JSON files in a directory using jq schema.
The benefits of using jq schema are:
- we can extract multiple keys from the JSON files. the schema below extracts the bibtex, current_limitations, and comparison_with_existing_methods keys.
  {
            bibtex: .bibtex,
            current_limitations: .discussion.limitations_and_future_work.current_limitations,
            # comparison_with_existing_methods: .methodology.comparison_with_existing_methods
        }
'''

import os
import json

from langchain_community.document_loaders import DirectoryLoader, JSONLoader

# from personal_note.tutorial import FOLDER_PATH, main_folder


def clean_jq_schema(schema_str: str) -> str:
    """
    Preprocess the jq_schema string by removing comments.
    It removes:
      - Entire lines that start with '#' (after stripping whitespace)
      - Inline comments (anything after a '#' in a line)

    Note: This is a simple implementation and does not account for '#' inside string literals.
    """
    lines = schema_str.splitlines()
    cleaned_lines = []
    for line in lines:
        stripped = line.strip()
        # Skip the line if it is a full-line comment
        if stripped.startswith('#'):
            continue
        # Remove inline comments (everything after a '#' character)
        if '#' in line:
            line = line.split('#', 1)[0]
        cleaned_lines.append(line.rstrip())
    return "\n".join(cleaned_lines)

def load_json_files(folder_path, jq_schema):
    """
    Load JSON files from the directory using DirectoryLoader and JSONLoader.
    Extracts relevant fields using the provided (and cleaned) jq_schema.
    Returns a list of dictionaries containing the extracted data.
    """
    cleaned_jq_schema = clean_jq_schema(jq_schema)
    loader = DirectoryLoader(
        path=folder_path,
        glob="*.json",
        loader_cls=JSONLoader,
        show_progress=True,
        loader_kwargs={
            "jq_schema": cleaned_jq_schema,
            "text_content": False
        }
    )

    documents = loader.load()
    extracted_data = []

    for doc in documents:
        try:
            entry = json.loads(doc.page_content)  # Convert JSON string to dictionary
            extracted_data.append(entry)
        except json.JSONDecodeError:
            print(f"Skipping document due to JSON decoding error: {doc}")

    return extracted_data

def save_to_text(data, output_file):
    """
    Saves extracted data to a text file in a readable format.
    """
    with open(output_file, "w", encoding="utf-8") as f:
        for entry in data:
            f.write(f"BibTeX: {entry.get('bibtex', 'N/A')}\n\n")
            f.write("Current Limitations:\n")
            for limitation in entry.get("current_limitations", []):
                f.write(f"- {limitation}\n")
            f.write("\nComparison with Existing Methods:\n")
            comparison = entry.get("comparison_with_existing_methods", {})
            for key, value in comparison.items():
                f.write(f"{key}: {value}\n")
            f.write("\n" + "="*80 + "\n\n")
    print(f"Extracted data saved to text file: {output_file}")

def save_to_json(data, output_file):
    """
    Saves extracted data as a list of dictionaries in a JSON file.
    """
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    print(f"Extracted data saved to JSON file: {output_file}")

if __name__ == "__main__":
    # Define input/output paths
    # input_dir = r'G:\My Drive\research_related\corona_discharge\methodology_gap_extractor_partial_discharge\json_output\gemini-2.0-flash-thinking-exp-01-21'
    # output_dir = r'G:\My Drive\research_related\corona_discharge\methodology_gap_extractor_partial_discharge\json_output\gemini-2.0-flash-thinking-exp-01-21_updated'

    # main_folder=r"G:\My Drive\research_related\0 eeg_trend_till24\eeg_review\methodology_gap_extractor\json_output"
    main_folder=r"G:\My Drive\research_related\corona_discharge\methodology_gap_extractor_partial_discharge\json_output"

    FOLDER_PATH = os.path.join(main_folder, "gemini-2.0-flash-thinking-exp-01-21_updated")
    TXT_OUTPUT_FILE=os.path.join(main_folder, "gap_extracted_output.txt")
    JSON_OUTPUT_FILE = os.path.join(main_folder, "lit_review_pd.json")


    # Define the jq_schema with a commented-out line for troubleshooting
    # jq_schema = """
    #     {
    #         bibtex: .bibtex,
    #         current_limitations: .discussion.limitations_and_future_work.current_limitations,
    #         # comparison_with_existing_methods: .methodology.comparison_with_existing_methods
    #     }
    # """
    jq_schema = """
        {
            bibtex: .bibtex,
            introduction: .introduction,
            methods: .methodology
        }
    """
    # Load and extract data using the provided (and cleaned) jq_schema
    extracted_data = load_json_files(FOLDER_PATH, jq_schema)

    # Save in different formats
    # save_to_text(extracted_data, TXT_OUTPUT_FILE)
    save_to_json(extracted_data, JSON_OUTPUT_FILE)
