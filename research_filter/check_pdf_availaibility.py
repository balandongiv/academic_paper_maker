import os
import pandas as pd

# File paths
excel_path = r"C:\Users\rpb\OneDrive - ums.edu.my\Code Development\academic_paper_maker\research_filter\database\eeg_review.xlsx"
pdf_folder = r"C:\Users\rpb\OneDrive - ums.edu.my\research_related\0 eeg_trend_till24\eeg_review"
column_name = "pdf_name"  # Change this if the column has a different name

# Load the Excel file
df = pd.read_excel(excel_path)

# Iterate through the rows in the specified column
for index, row in df.iterrows():
    pdf_name = row[column_name]

    # Check if the cell is valid (not empty and ends with '.pdf')
    if isinstance(pdf_name, str) and pdf_name.endswith(".pdf"):
        pdf_path = os.path.join(pdf_folder, pdf_name)

        # Check if the file exists
        if not os.path.exists(pdf_path):
            df.at[index, column_name] = "need_to_download"

# Save the updated DataFrame back to the Excel file
df.to_excel(excel_path, index=False)

print("Excel file has been updated.")
