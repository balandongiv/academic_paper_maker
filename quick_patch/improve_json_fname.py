import os
import re
import shutil

# Folder containing the JSON files
source_folder = r"C:\Users\balan\OneDrive - ums.edu.my\research_related\corona_discharge\abstract_pd_discharge_relevance_sorter\json_output"

# Destination folder for the renamed files
destination_folder = r"C:\Users\balan\OneDrive - ums.edu.my\research_related\corona_discharge\renamed_json_output"
os.makedirs(destination_folder, exist_ok=True)  # Create the folder if it doesn't exist

def clean_filename(filename):
    """
    Cleans and shortens the filename:
    - Removes commas, periods, and other unnecessary characters.
    - Extracts and keeps the year.
    - Replaces multiple underscores with a single underscore.
    - Truncates the cleaned filename to a maximum of 10 characters, excluding the year.
    """
    # Remove commas, periods, and spaces
    cleaned = filename.replace(',', '').replace('.', '').replace(' ', '')

    # Extract the year (assuming it's at the end of the filename, preceded by an underscore)
    match = re.search(r'_(\d{4})$', cleaned)
    year = match.group(1) if match else ''

    # Remove the year from the base name to process it
    base_name = cleaned[:match.start()] if match else cleaned

    # Replace multiple underscores with a single underscore
    base_name = re.sub(r'__+', '_', base_name)

    # Remove any leading or trailing underscores
    base_name = base_name.strip('_')

    # Truncate to a maximum of 10 characters
    if len(base_name) > 10:
        base_name = base_name[:10]

    # Append the year back to the filename
    if year:
        base_name = f"{base_name}_{year}"

    return base_name

# Process each JSON file in the source folder
for filename in os.listdir(source_folder):
    if filename.lower().endswith(".json"):
        original_path = os.path.join(source_folder, filename)

        # Separate base name and extension
        base_name, ext = os.path.splitext(filename)

        # Clean the base name
        cleaned_base_name = clean_filename(base_name)

        # Create the new filename
        new_filename = cleaned_base_name + ext
        new_path = os.path.join(destination_folder, new_filename)

        # Move and rename the file to the destination folder
        shutil.move(original_path, new_path)
        print(f"Renamed and moved: {filename} -> {new_path}")

print("All filenames have been processed, renamed, and moved to the new folder.")
