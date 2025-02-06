"""
This script assumes the pdf has been converted to xml using grobid.
Then, this script will process the XML files and extract the sections from the XML files.
"""
import glob
import json
import os
import re
from grobid_tei_xml.parsed_gorbid import parse_document_xml


def natural_sort_key(filename: str):
    """
    Sort filenames naturally (e.g., handles numerical parts correctly).
    """
    return [
        int(text) if text.isdigit() else text.lower()
        for text in re.split(r'(\d+)', os.path.basename(filename))
    ]


def parse_xml_content(xml_content: str):
    """
    Parse the XML content (already read as a string) and extract
    the relevant sections.

    Returns:
        tuple: A tuple containing:
            - combined_sections (dict): Combined sections with paragraphs.
            - has_introduction (bool): True if an Introduction is found.
            - has_conclusion (bool): True if a Conclusion is found.
            - has_untitled_section (bool): True if an untitled section is found.
    """
    # Parse the XML document using your external parser
    doc = parse_document_xml(xml_content)
    combined_sections = {}

    # Flags to track if specific sections exist
    has_introduction = False
    has_conclusion = False
    has_untitled_section = False

    # Iterate through each section from the parsed document
    for section_name, paragraphs in doc.sections.items():
        if not paragraphs:  # Skip empty sections
            continue

        normalized_section = section_name.lower()

        # Process Introduction sections
        if "introduction" in normalized_section or "intro" in normalized_section:
            has_introduction = True
            if len(paragraphs) > 1:
                paragraphs = paragraphs[1:]
                paragraphs.insert(0, "drop_par1")

        # Process untitled sections
        if "untitled section 1" in normalized_section:
            has_untitled_section = True
            if len(paragraphs) > 1:
                paragraphs = paragraphs[1:]
                paragraphs.insert(0, "drop_par1")

        # Skip Conclusion sections
        if "conclusion" in normalized_section:
            has_conclusion = True
            continue

        # Combine paragraphs with a prefix (e.g., "Par 1: ...")
        if paragraphs:
            combined_text = "\n\n".join(
                [f"Par {idx}: {paragraph}" for idx, paragraph in enumerate(paragraphs, start=1)]
            )
            combined_sections[section_name] = combined_text

    return combined_sections, has_introduction, has_conclusion, has_untitled_section


def save_json_data(xml_path: str,
                   combined_sections: dict,
                   has_introduction: bool,
                   has_conclusion: bool,
                   has_untitled_section: bool,
                   json_folder: str,
                   no_intro_concl_folder: str,
                   untitled_section_folder: str) -> dict:
    """
    Save the parsed data as JSON in multiple locations.

    Args:
        xml_path (str): Path to the original XML file.
        combined_sections (dict): Parsed sections to save.
        has_introduction (bool): Flag indicating if Introduction exists.
        has_conclusion (bool): Flag indicating if Conclusion exists.
        has_untitled_section (bool): Flag indicating if an untitled section exists.
        json_folder (str): Main folder where JSON should be saved.
        no_intro_concl_folder (str): Folder to save JSON if no intro/conclusion exists.
        untitled_section_folder (str): Folder to save JSON if untitled section is present.

    Returns:
        dict: The combined_sections dictionary.
    """
    base_name = os.path.splitext(os.path.basename(xml_path))[0]

    # Save JSON in the main folder
    output_json_path = os.path.join(json_folder, f"{base_name}.json")
    with open(output_json_path, 'w', encoding='utf-8') as out_file:
        json.dump(combined_sections, out_file, ensure_ascii=False, indent=2)
    print(f"Processed and saved: {output_json_path}")

    # If neither introduction nor conclusion is present, save in a separate folder
    if not has_introduction and not has_conclusion:
        separate_json_path = os.path.join(no_intro_concl_folder, f"{base_name}.json")
        with open(separate_json_path, 'w', encoding='utf-8') as out_file:
            json.dump(combined_sections, out_file, ensure_ascii=False, indent=2)
        print(f"Stored in 'no_intro_conclusion': {separate_json_path}")

    # If an untitled section is present, save in the specialized folder
    if has_untitled_section:
        untitled_json_path = os.path.join(untitled_section_folder, f"{base_name}.json")
        with open(untitled_json_path, 'w', encoding='utf-8') as out_file:
            json.dump(combined_sections, out_file, ensure_ascii=False, indent=2)
        print(f"Stored in 'untitled_section': {untitled_json_path}")

    return combined_sections


def process_xml_file(xml_path: str,
                     save_json: bool = True,
                     json_folder: str = None,
                     no_intro_concl_folder: str = None,
                     untitled_section_folder: str = None) -> dict:
    """
    Processes an XML file: parses its content and (optionally) saves the results as JSON.

    Args:
        xml_path (str): Path to the XML file.
        save_json (bool): If True, the parsed content is saved as JSON files.
        json_folder (str): Main folder for JSON output.
        no_intro_concl_folder (str): Folder for files with no intro/conclusion.
        untitled_section_folder (str): Folder for files with untitled sections.

    Returns:
        dict: The parsed combined_sections, or None if an error occurs.
    """
    try:
        # Read the XML file content
        with open(xml_path, 'r', encoding='utf-8') as xml_file:
            xml_content = xml_file.read()

        # Parse XML content
        combined_sections, has_introduction, has_conclusion, has_untitled_section = parse_xml_content(xml_content)

        # If saving to JSON is not required, just return the parsed data
        if not save_json:
            return combined_sections

        # Ensure that folder paths are provided when saving JSON
        if json_folder is None or no_intro_concl_folder is None or untitled_section_folder is None:
            raise ValueError("Folder paths must be provided when save_json is True.")

        # Delegate JSON saving to a separate function
        return save_json_data(xml_path, combined_sections,
                              has_introduction, has_conclusion, has_untitled_section,
                              json_folder, no_intro_concl_folder, untitled_section_folder)

    except Exception as e:
        print(f"Error processing {xml_path}: {e}")
        return None

def run_pipeline(FOLDER_PATH):
    JSON_FOLDER = os.path.join(FOLDER_PATH, 'json')
    NO_INTRO_CONCL_FOLDER = os.path.join(JSON_FOLDER, 'no_intro_conclusion')
    UNTITLED_SECTION_FOLDER = os.path.join(JSON_FOLDER, 'untitled_section')

    # Ensure directories exist
    os.makedirs(JSON_FOLDER, exist_ok=True)
    os.makedirs(NO_INTRO_CONCL_FOLDER, exist_ok=True)
    os.makedirs(UNTITLED_SECTION_FOLDER, exist_ok=True)

    # Get sorted list of XML files from the specified folder
    xml_files = glob.glob(os.path.join(FOLDER_PATH, "*.xml"))
    xml_files.sort(key=natural_sort_key)

    # Process each XML file
    for xml_path in xml_files:
        process_xml_file(xml_path,
                         save_json=True,
                         json_folder=JSON_FOLDER,
                         no_intro_concl_folder=NO_INTRO_CONCL_FOLDER,
                         untitled_section_folder=UNTITLED_SECTION_FOLDER)

# --- Example usage (main script) ---
if __name__ == "__main__":
    # Folder paths (update these as needed)
    FOLDER_PATH = r"G:\My Drive\research_related\0 eeg_trend_till24\eeg_review\xml"
    run_pipeline(FOLDER_PATH)

