'''

This will be the first step in updating the publisher information in the main Excel file.
We will use the journal names from the supporting journal lists to determine the publisher of each journal in the main file.
However, this script assumes that the journal names in the main file are consistent with the journal names in the supporting lists.
'''

import os

import pandas as pd


def main():
    # Set the main path (adjust if needed)

    main_path = r"../../research_filter/database"
    os.chdir(main_path)  # Change working directory

    # Filenames
    file_eeg = "eeg_review.xlsx"
    file_springer = "springer_journal.xlsx"
    file_mdpi = "mdpi_journal.xlsx"
    file_iopscience = "iopscience_journal.xlsx"
    file_sciencedirect = "sciencedirect_journal.xlsx"
    output_file = "eeg_review_v2.xlsx"

    # Read the main Excel file into a DataFrame
    df_eeg = pd.read_excel(file_eeg)

    # Read supporting journal lists
    df_springer = pd.read_excel(file_springer)
    df_mdpi = pd.read_excel(file_mdpi)
    df_sciencedirect = pd.read_excel(file_sciencedirect)
    df_iopscience = pd.read_excel(file_iopscience)
    df_wiley = pd.read_excel("wiley_journal.xlsx")

    # Remove brackets and their content from journal names
    df_eeg['journal'] = df_eeg['journal'].str.replace(r'\([^)]*\)', '', regex=True).str.strip()

    # Convert to sets for faster lookup (lowercasing for case-insensitive matching)
    springer_journals = set(df_springer['journal'].str.lower().dropna())
    mdpi_journals = set(df_mdpi['journal'].str.lower().dropna())
    sciencedirect_journals = set(df_sciencedirect['journal'].str.lower().dropna())
    iopscience_journals = set(df_iopscience['journal'].str.lower().dropna())
    wiley_journals = set(df_wiley['journal'].str.lower().dropna())
    # Define a helper function to determine the publisher
    def get_publisher(journal_name):
        if not isinstance(journal_name, str):
            return None
        j_lower = journal_name.lower().strip()
        if j_lower in springer_journals:
            return "springer"
        elif j_lower in mdpi_journals:
            return "mdpi"
        elif j_lower in sciencedirect_journals:
            return "sciencedirect"
        elif j_lower in iopscience_journals:
            return "iopscience"
        elif j_lower in wiley_journals:
            return "wiley"
        elif "ieee" in j_lower:  # Check for "ieee" in the journal name
            return "ieee"
        elif journal_name.strip().startswith("Frontiers"):
            return "frontiers"
        elif journal_name.strip().startswith("Fron"):
            return "frontiers"

        return None

    # Apply the helper function to each journal_name in df_eeg
    df_eeg['publisher'] = df_eeg['journal'].apply(get_publisher)

    # Save the updated DataFrame to a new Excel file
    df_eeg.to_excel(output_file, index=False)
    print(f"Updated file saved as: {output_file}")

if __name__ == "__main__":
    main()
