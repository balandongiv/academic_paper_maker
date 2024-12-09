import pandas as pd
import tkinter as tk
from tkinter import filedialog
import os
# Initialize tkinter root
root = tk.Tk()
root.withdraw()  # Hide the root window

# Open a file dialog to select the input file
file_path = filedialog.askopenfilename(
    title="Select a tab-delimited text file",
    filetypes=[("Text Files", "*.txt")]
)

# Check if a file was selected
if not file_path:
    print("No file selected. Exiting...")
    exit()

# Read the tab-delimited file
with open(file_path, 'r', encoding='utf-8') as file:
    lines = file.readlines()

# Process the lines to handle improperly split URLs
processed_lines = []
current_line = ""

for line in lines:
    # Check if the line starts with a URL or is a continuation of the previous line
    if line.startswith("http://") or line.startswith("https://"):
        # Append to the current line (handles split URLs)
        current_line = current_line.strip() + "\n" + line.strip()
    else:
        # Save the previous complete line if exists
        if current_line:
            processed_lines.append(current_line)
        current_line = line.strip()  # Start a new line

# Add the last line if it exists
if current_line:
    processed_lines.append(current_line)

# Convert processed lines into a tab-delimited DataFrame
data = [line.split("\t") for line in processed_lines]
df = pd.DataFrame(data)

# Define the desired headers
headers = [
    "Author",
    "Year",
    "Title",
    "Journal",
    "Volume",
    "Publisher",
    "DOI",
    "abstract: Abstract:",
    "File Attachments",
    "URL"
]

# If the file has fewer columns than the headers, fill in missing columns with None
while len(df.columns) < len(headers):
    df[len(df.columns)] = None

# If there are more columns than the defined headers, assume these extras are additional URLs
if len(df.columns) > len(headers):
    # Extract extra columns (beyond the first 10)
    extra_cols = df.columns[len(headers):]

    # Combine all extra columns into the last column "URL", separating by newlines
    df["URL"] = df["URL"].astype(str)
    for col in extra_cols:
        df["URL"] = df["URL"].where(df[col].isna(), df["URL"] + "\n" + df[col].astype(str))

    # Drop the extra URL columns
    df.drop(columns=extra_cols, inplace=True)

# Assign the final headers
df.columns = headers
# Extract the base name of the file (without extension)
base_name = os.path.splitext(os.path.basename(file_path))[0]
output_file = os.path.join(os.path.dirname(file_path), f"{base_name}.xlsx")

# Use Excel writer to retain newline characters
with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
    df.to_excel(writer, index=False)
    sheet = writer.sheets['Sheet1']
    for column in df.columns:
        column_letter = chr(ord('A') + list(df.columns).index(column))
        sheet.column_dimensions[column_letter].width = 30  # Adjust column width for better readability

print(f"Data has been successfully processed and saved to {output_file}.")
