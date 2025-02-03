"""
This script assume the pdf has been converted to xml using grobid.
Then, this script will process the XML files and extract the sections from the XML files.
"""

import glob
import json
import os
import re
from grobid_tei_xml.parsed_gorbid import parse_document_xml

# Define folder paths
FOLDER_PATH = r"G:\My Drive\research_related\0 eeg_trend_till24\eeg_review\xml"
JSON_FOLDER = os.path.join(FOLDER_PATH, 'json')
NO_INTRO_CONCL_FOLDER = os.path.join(JSON_FOLDER, 'no_intro_conclusion')

# Ensure directories exist
os.makedirs(JSON_FOLDER, exist_ok=True)
os.makedirs(NO_INTRO_CONCL_FOLDER, exist_ok=True)


def natural_sort_key(filename):
    """Sort filenames naturally (e.g., handles numerical parts correctly)."""
    return [int(text) if text.isdigit() else text.lower()
            for text in re.split(r'(\d+)', os.path.basename(filename))]


def process_xml_file(xml_path):
    """Processes an XML file, extracts sections, and saves it as JSON."""
    try:
        with open(xml_path, 'r', encoding='utf-8') as xml_file:
            xml_content = xml_file.read()

        # Parse document
        doc = parse_document_xml(xml_content)
        combined_sections = {}

        # Track if introduction and conclusion exist
        has_introduction = False
        has_conclusion = False

        # Iterate through each section
        for section_name, paragraphs in doc.sections.items():
            if not paragraphs:  # Skip empty sections
                continue

            normalized_section = section_name.lower()

            # Identify if document has introduction or conclusion
            if "introduction" in normalized_section or "intro" in normalized_section:
                has_introduction = True

                if len(paragraphs) > 1:
                    paragraphs = paragraphs[1:]
                    paragraphs.insert(0, "drop_par1")  # Adding "drop_par1" after the first paragraph


            if "conclusion" in normalized_section:
                has_conclusion = True
                continue  # Skip conclusion sections

            if paragraphs:
                combined_text = "\n\n".join(
                    [f"Par {idx}: {paragraph}" for idx, paragraph in enumerate(paragraphs, start=1)]
                )
                combined_sections[section_name] = combined_text

        # Define output path
        base_name = os.path.splitext(os.path.basename(xml_path))[0]
        output_json_path = os.path.join(JSON_FOLDER, f"{base_name}.json")

        # Save JSON
        with open(output_json_path, 'w', encoding='utf-8') as out_file:
            json.dump(combined_sections, out_file, ensure_ascii=False, indent=2)

        print(f"Processed and saved: {output_json_path}")

        # If neither introduction nor conclusion is present, store in a separate folder
        if not has_introduction and not has_conclusion:
            separate_json_path = os.path.join(NO_INTRO_CONCL_FOLDER, f"{base_name}.json")
            with open(separate_json_path, 'w', encoding='utf-8') as out_file:
                json.dump(combined_sections, out_file, ensure_ascii=False, indent=2)

            print(f"Stored in 'no_intro_conclusion': {separate_json_path}")

    except Exception as e:
        print(f"Error processing {xml_path}: {e}")


if __name__ == "__main__":
    # Get sorted list of XML files
    xml_files = glob.glob(os.path.join(FOLDER_PATH, "*.xml"))
    xml_files.sort(key=natural_sort_key)

    # Skip first two files if needed
    # xml_files = xml_files[2:]

    # Process each XML file
    for xml_path in xml_files:
        process_xml_file(xml_path)
