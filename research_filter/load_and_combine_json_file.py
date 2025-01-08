import os
import json
import unicodedata

def sanitize_filename(filename):
    """
    Convert filename to proper characters by normalizing Unicode and replacing any spaces or unusual characters.
    """
    normalized = unicodedata.normalize('NFKD', filename)
    ascii_only = normalized.encode('ascii', 'ignore').decode('utf-8')
    sanitized = ascii_only.replace(" ", "_")
    return sanitized

# Specify the folder path containing the JSON files
folder_path = r"C:\Users\balan\OneDrive - ums.edu.my\research_related\0 eeg_trend_till24\eeg_review\concept_and_technique"

# Initialize a dictionary to store combined data
combined_data = {}

try:
    # Load and combine JSON files
    for filename in os.listdir(folder_path):
        if filename.endswith(".json"):
            # Sanitize the file name to remove any alien characters
            sanitized_key = sanitize_filename(os.path.splitext(filename)[0])
            file_path = os.path.join(folder_path, filename)
            with open(file_path, 'r', encoding='utf-8') as file:
                file_data = json.load(file)
                combined_data[sanitized_key] = file_data

    # Output the combined data to a file
    output_path = os.path.join(folder_path, "combined_data_sanitized.json")
    with open(output_path, 'w', encoding='utf-8') as output_file:
        json.dump(combined_data, output_file, indent=4)

    print(f"Combined JSON saved successfully at: {output_path}")

except FileNotFoundError:
    print("The specified folder path does not exist or cannot be accessed.")
except Exception as e:
    print(f"An error occurred: {e}")
