import os
import pandas as pd
import json

# Define the paths
download_path = r'C:\Users\balan\OneDrive - ums.edu.my\research_related\0 eeg_trend_till24\eeg_review'
excel_path = r'C:\Users\balan\IdeaProjects\academic_paper_maker\research_filter\database\eeg_test_simple_with_bibtex_v1.xlsx'

# Load the Excel file into a DataFrame
df = pd.read_excel(excel_path)

# Ensure the 'pdf_name' column exists
if 'pdf_name' not in df.columns:
    df['pdf_name'] = None

# Iterate over all JSON files in the download path
for filename in os.listdir(download_path):
    if filename.endswith('.json'):
        # Construct the full path of the JSON file
        json_path = os.path.join(download_path, filename)

        # Extract the filename without extension (identifier in the DataFrame)
        identifier = os.path.splitext(filename)[0]

        try:
            # Read the JSON file
            with open(json_path, 'r') as file:
                data = json.load(file)

            # Extract the actual_pdf_name value
            actual_pdf_name = data.get('expected_pdf_name', None)
            status = data.get('status', None)
            if actual_pdf_name and status == 'success':
                # Update the DataFrame with the extracted PDF filename (not full path)
                df.loc[df['bibtex'] == identifier, 'pdf_name'] = actual_pdf_name

                # Delete the JSON file after updating
                os.remove(json_path)
                print(f"Successfully updated and deleted JSON file: {filename}")
        except Exception as e:
            # Log the error and continue with the next file
            print(f"Error processing file {filename}: {e}")
            continue

# Save the updated DataFrame back to Excel
updated_excel_path = r'C:\Users\balan\IdeaProjects\academic_paper_maker\research_filter\database\eeg_test_simple_with_bibtex_v1_updated.xlsx'
df.to_excel(updated_excel_path, index=False)

print(f"Updated Excel file saved at: {updated_excel_path}")
