import os
import shutil

# Define the source and destination directories
source_dir = r"C:\Users\balan\OneDrive - ums.edu.my\research_related\0 eeg_trend_till24\eeg_review\methodology_extractor_agent_to_compare_later\json_output"
destination_dir = r"C:\Users\balan\OneDrive - ums.edu.my\research_related\0 eeg_trend_till24\eeg_review\methodology_extractor_agent_to_compare_later\json_output_run_0"

# Create the destination directory if it doesn't exist
os.makedirs(destination_dir, exist_ok=True)

# Iterate through all files in the source directory
for filename in os.listdir(source_dir):
    if filename.endswith(".json"):  # Only process JSON files
        # Construct the new filename
        new_filename = f"{os.path.splitext(filename)[0]}_run_0.json"
        # Copy and rename the file to the destination directory
        shutil.copy2(
            os.path.join(source_dir, filename),
            os.path.join(destination_dir, new_filename)
        )

print("All JSON files have been renamed and copied successfully!")
