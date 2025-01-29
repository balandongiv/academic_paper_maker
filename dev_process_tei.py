import glob
import json
import os
import re

from grobid_tei_xml.parsed_gorbid import parse_document_xml

# Define folder path
folder_path = r"G:\My Drive\research_related\0 eeg_trend_till24\eeg_review\xml"

# Function for natural sorting (handles numbers in filenames correctly)
def natural_sort_key(filename):
    return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', os.path.basename(filename))]

# Get list of XML files and sort naturally
xml_files = glob.glob(os.path.join(folder_path, "*.xml"))
xml_files.sort(key=natural_sort_key)

# Process each XML file
for xml_path in xml_files:
    try:
        with open(xml_path, 'r', encoding='utf-8') as xml_file:
            xml_content = xml_file.read()
            doc = parse_document_xml(xml_content)
            non_empty_sections = [key for key, value in doc.sections.items() if value]
            section_keys_json = json.dumps(non_empty_sections, indent=4)
            print(f"Processed: {os.path.basename(xml_path)}")
            print(doc)  # Adjust this line if you want a more structured output
    except Exception as e:
        print(f"Error processing {xml_path}: {e}")
