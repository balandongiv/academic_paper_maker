'''

This is a tutorial script to demonstrate how to use the `process_xml_file` function from the `grobid_tei_xml.xml_json` module.
'''
import json
import os
from grobid_tei_xml.xml_json import process_xml_file  # Update the module name if needed

def main():
    # Define the path to the test XML file
    xml_file_path = r"D:\Research Related\corona_discharge\xml\Abdel_Galil_T_K_2005.grobid.tei.xml"

    # Ensure the file exists
    if not os.path.exists(xml_file_path):
        print(f"Error: The specified XML file does not exist: {xml_file_path}")
        return

    # Set up the current directory as the working directory
    current_dir = os.getcwd()
    print(f"Using current directory: {current_dir}")

    # Set up folder paths for JSON output
    json_folder = os.path.join(current_dir, "json")
    no_intro_concl_folder = os.path.join(json_folder, "no_intro_conclusion")
    untitled_section_folder = os.path.join(json_folder, "untitled_section")

    # Ensure the output directories exist
    os.makedirs(json_folder, exist_ok=True)
    os.makedirs(no_intro_concl_folder, exist_ok=True)
    os.makedirs(untitled_section_folder, exist_ok=True)

    # --- Test case 1: Process XML and save JSON files ---
    print("\n--- Processing XML with JSON saving enabled ---")
    result = process_xml_file(
        xml_path=xml_file_path,
        save_json=True,
        json_folder=json_folder,
        no_intro_concl_folder=no_intro_concl_folder,
        untitled_section_folder=untitled_section_folder
    )
    print("Processing result (with JSON saving):")
    print(result)

    # --- Test case 2: Process XML without saving JSON files ---
    print("\n--- Processing XML with JSON saving disabled ---")
    result_no_save = process_xml_file(xml_file_path, save_json=False)
    print("Processing result (without JSON saving):")
    print(result_no_save)

    # --- Test case 3: Convert the list of dict to string ---
    print("\n--- Converting the list of dict to string ---")
    result_str = json.dumps(result, indent=2)
    print(result_str)
if __name__ == "__main__":
    main()
