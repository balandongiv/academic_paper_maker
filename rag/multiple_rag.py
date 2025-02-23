import json
from langchain_community.document_loaders import DirectoryLoader, JSONLoader

def load_json_files(folder_path, jq_schema):
    """
    Load JSON files from the directory using DirectoryLoader and JSONLoader.
    Extracts relevant fields using the provided jq_schema.
    Returns a list of dictionaries containing extracted data.
    """
    loader = DirectoryLoader(
        path=folder_path,
        glob="*.json",
        loader_cls=JSONLoader,
        loader_kwargs={
            "jq_schema": jq_schema,
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
            f.write("\n" + "="*80 + "\n\n")  # Separator for readability

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
    FOLDER_PATH = r"G:\My Drive\research_related\0 eeg_trend_till24\eeg_review\methodology_gap_extractor\json_output\gemini-2.0-flash-thinking-exp-01-21_updated"
    TXT_OUTPUT_FILE = r"G:\My Drive\research_related\0 eeg_trend_till24\eeg_review\methodology_gap_extractor\json_output\gap_extracted_output.txt"
    JSON_OUTPUT_FILE = r"G:\My Drive\research_related\0 eeg_trend_till24\eeg_review\methodology_gap_extractor\json_output\gap_extracted_output.json"

    # Define the jq_schema externally so it can be easily modified or replaced.
    jq_schema = """
        {
            bibtex: .bibtex,
            current_limitations: .discussion.limitations_and_future_work.current_limitations,
            comparison_with_existing_methods: .methodology.comparison_with_existing_methods
        }
    """

    # Load and extract data using the provided jq_schema
    extracted_data = load_json_files(FOLDER_PATH, jq_schema)

    # Save in different formats
    save_to_text(extracted_data, TXT_OUTPUT_FILE)
    save_to_json(extracted_data, JSON_OUTPUT_FILE)
