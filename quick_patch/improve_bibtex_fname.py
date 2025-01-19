import pandas as pd

# Path to the Excel file
file_path = r"C:\Users\balan\OneDrive - ums.edu.my\research_related\corona_discharge\database\combined_filtered.xlsx"

# Load the Excel file
df = pd.read_excel(file_path)

# Check if the 'bibtex' column exists
if 'bibtex' in df.columns:
    # Clean the 'bibtex' column
    df['bibtex'] = df['bibtex'].str.replace(',', '', regex=False).str.replace('.', '', regex=False)

    # Save the updated DataFrame back to the same Excel file
    df.to_excel(file_path, index=False)
    print("The 'bibtex' column has been updated and saved.")
else:
    print("The 'bibtex' column does not exist in the Excel file.")
