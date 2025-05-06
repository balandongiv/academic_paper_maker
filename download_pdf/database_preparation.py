'''
This is the first step in the data preparation process. The script combines multiple Scopus CSV files in a folder, applies cleaning/formatting, removes duplicates, and saves to Excel.

'''

import os
import glob
import pandas as pd
import re
import unicodedata
from download_pdf.bib_exporter import parse_scopus_bib_files
def map_publisher_long(df):
    # Create a full dictionary for mapping
    publisher_mapping = {
        'Elsevier Ltd': 'sciencedirect',
        'Elsevier B.V.': 'sciencedirect',
        'Elsevier Inc.': 'sciencedirect',
        'Elsevier Ireland Ltd': 'sciencedirect',
        'Elsevier Masson s.r.l.': 'sciencedirect',
        'Elsevier Masson SAS': 'sciencedirect',
        'John Wiley and Sons Inc': 'wiley',
        'John Wiley and Sons Ltd': 'wiley',
        'John Wiley and Sons Inc.': 'wiley',
        'Wiley-Blackwell Publishing': 'wiley',
        'Springer Science and Business Media Deutschland GmbH': 'springer',
        'Springer Nature': 'springer',
        'Springer New York LLC': 'springer',
        'Springer London': 'springer',
        'Springer-Verlag London Ltd': 'springer',
        'Springer-Verlag Italia s.r.l.': 'springer',
        'Springer Berlin Heidelberg': 'springer',
        'Springer International Publishing': 'springer',
        'Springer-Verlag Wien': 'springer',
        'Springer New York': 'springer',
        'Springer Japan': 'springer',
        'Springer India': 'springer',
        'Springer Netherlands': 'springer',
        'Springer Tokyo': 'springer',
        'Springer': 'springer',
        'Multidisciplinary Digital Publishing Institute (MDPI)': 'mdpi',
        'MDPI': 'mdpi',
        'MDPI AG': 'mdpi',
        'World Scientific': 'worldscientific',
        'Institute of Physics Publishing': 'iopscience',
        'IOP Publishing Ltd': 'iopscience',
        'Institute of Electrical and Electronics Engineers Inc.': 'ieee',
        'IEEE': 'ieee',
        'IEEE Computer Society': 'ieee',
        'Inderscience Publishers': 'inderscience',
        'IOS Press': 'iospress_content',
        'IOS Press BV': 'iospress_content',
        'National Institute of Health': 'nih_nlm',
        'Nature Publishing Group': 'nature',
        'Nature Research': 'nature',
        'Frontiers Media SA': 'frontiers',
        'Frontiers Media S.A.': 'frontiers',
        'Public Library of Science': 'plos_journals',
        'American Chemical Society': 'rsc_pubs',
        'Royal Society of Chemistry': 'rsc_pubs',
        'Taylor and Francis Ltd.': 'tandfonline',
        'Taylor and Francis Ltd': 'tandfonline',
        'Taylor and Francis Inc.': 'tandfonline',
        'Hindawi Limited': 'biorxiv',
        'American Institute of Physics': 'aip_pubs',
        'American Institute of Physics Inc.': 'aip_pubs',
        'SAGE Publications Ltd': 'sagepub_journals',
        'SAGE Publications Inc.': 'sagepub_journals',
        'American Society of Mechanical Engineers (ASME)': 'scimagojr',
        'Wolters Kluwer Medknow Publications': 'lww_journals',
        'De Gruyter Open Ltd': 'degruyter',
        'Scibulcom Ltd.': 'sciencepubco',
        'Semarak Ilmu Publishing': 'sciencepubco',
        'Bentham Science Publishers': 'neuroquantology',
        'Edizioni Minerva Medica': 'neuroquantology',
        'Elsevier GmbH': 'sciencedirect',
        'Penerbit Akademia Baru': 'edu_iium',
        'University of Medicine and Pharmacy Targu Mures': 'edu_unimap',
        'KeAi Publishing Communications Ltd.': 'edu_chd',
        'Inderscience Publishers': 'inderscience',
        'Polska Akademia Nauk': 'edu_tyut',
        'Turkiye Klinikleri': 'gov_tubitak',
        'Journal of Infection in Developing Countries': 'fpz_trafficandtransportation',
        'Korean Institute of Electrical Engineers': 'edu_fudan',
        'ISA - Instrumentation, Systems, and Automation Society': 'edu_tyut',
        'Chinese Society for Electrical Engineering': 'edu_chd',
        'Research India Publications': 'ripublication',
        'Tech Science Press': 'techscience',
        'Science and Engineering Research Support Society': 'iaescore_ijece',
        'Institute of Advanced Engineering and Science': 'iaescore_ijece',
        'International Institute of Anticancer Research': 'imrpress',
        'Kluwer Academic Publishers': 'sharif_scientiairanica',
        'Association for Computing Machinery': 'acm',
        'American Physical Society': 'aps',
        'Academic Press': 'academicpress',
        'Academic Press Inc.': 'academicpress',
        'Informa Healthcare': 'sagepub_journals',
        'IEEE Canada': 'ieee',
        'IEEE': 'ieee',
        'Elsevier': 'sciencedirect',
        'Elsevier Ltd:': 'sciencedirect',
        'BioMed Central': 'biomedcentral',
        'BioMed Central Ltd': 'biomedcentral',
        'Springer-Verlag': 'springer',
        'Blackwell Publishing Ltd': 'wiley',
        'BMJ Publishing Group': 'bmj',
        'Cambridge University Press': 'cambridge',
        'Elsevier': 'sciencedirect',
        'Blackwell Publishing Inc.': 'wiley',
        'W.B. Saunders Ltd': 'sciencedirect',
        'BioMed Central Ltd.': 'biomedcentral',
        'Institute of Physics': 'iopscience',
        'Institution of Engineering and Technology': 'iet',
        'Lippincott Williams and Wilkins': 'lww_journals',
        'Oxford University Press': 'oup',
        'Springer Verlag': 'springer',
        'Springer Science and Business Media B.V.': 'springer',
        # Default for unmatched cases
        'nan': 'other'
    }

    # Assuming df is your DataFrame
    df['publisher'] = df['publisher_long'].map(publisher_mapping)

    # Fill unmapped values with 'other'
    df['publisher'] = df['publisher'].fillna('other')

    return df


def format_name(name: str, style: str = "underscore") -> str:
    """
    Normalize author name to remove diacritics and special characters.
    Returns the cleaned name parts formatted according to the chosen style.

    :param name: The input name string.
    :param style: Formatting style ("underscore" or "concat").: underscore >> Piao_M,Piao_ML,Piao_MLK :: concat >> PiaoM,PiaoML,PiaoMLK
    :return: Formatted string based on the selected style.
    """
    # Normalize text to remove diacritics (alien characters)
    name = unicodedata.normalize('NFD', name).encode('ascii', 'ignore').decode('utf-8')

    # Split the name on spaces, hyphens, and dots
    parts = re.split(r'[ \.-]+', name)

    # Apply the chosen style
    if style == "underscore":
        return '_'.join(parts[:1] + [''.join(parts[1:])])  # First part + joined remainder with underscore
    elif style == "concat":
        return ''.join(parts)  # Direct concatenation of all parts
    else:
        raise ValueError("Invalid style: Choose 'underscore' or 'concat'.")

def gather_csv_files(folder_path: str) -> list:
    """
    Gather all CSV file paths in the given folder.
    """
    return glob.glob(os.path.join(folder_path, "*.csv"))

def load_csv_files(csv_files: list) -> pd.DataFrame:
    """
    Load each CSV file into a list of DataFrames, then concatenate them.
    """
    df_list = []
    for csv_path in csv_files:
        try:
            temp_df = pd.read_csv(csv_path)
            df_list.append(temp_df)
        except Exception as e:
            print(f"Error reading {csv_path}: {e}")

    if not df_list:
        print("No CSV files found or error in reading files.")
        return pd.DataFrame()  # Return empty DataFrame if none loaded

    return pd.concat(df_list, ignore_index=True)

def clean_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """
    Rename columns to be lowercase, strip spaces, remove parentheses, etc.
    """
    new_columns = []
    for col in df.columns:
        clean_col = (
            col.lower()
            .strip()
            .replace(" ", "_")
            .replace("(", "")
            .replace(")", "")
            .replace(".", "")
            .replace("/", "_")
        )
        new_columns.append(clean_col)
    df.columns = new_columns
    return df

def filter_rows(df: pd.DataFrame) -> pd.DataFrame:
    """
    Filter rows based on document_type and language_of_original_document.
    Only keep 'Article' or 'Review' in 'document_type' if present.
    Only keep 'English' in 'language_of_original_document' if present.
    """
    if 'document_type' in df.columns:
        df = df[df['document_type'].fillna('').str.lower().isin(['article', 'review'])]

    else:
        print("Warning: 'document_type' column not found. No filtering on document_type applied.")

    if 'language' in df.columns:
        df = df[df['language'].str.lower() == 'english']
    else:
        print("Warning: 'language_of_original_document' column not found. No filtering on language applied.")

    return df

def remove_duplicates_by_doi_and_title(df: pd.DataFrame) -> pd.DataFrame:
    """
    Remove duplicate rows based on the combination of 'doi' and 'title'.
    If both 'doi' and 'title' are present, use both columns.
    If only one is present, use that.
    """
    original_len = len(df)
    print(f'Initial number of rows: {original_len}')
    has_doi = 'doi' in df.columns
    has_title = 'title' in df.columns

    if has_doi and has_title:
        df = df.drop_duplicates(subset=['doi', 'title'], keep='first')
    elif has_doi:
        df = df.drop_duplicates(subset=['doi'], keep='first')
    elif has_title:
        df = df.drop_duplicates(subset=['title'], keep='first')
    else:
        print("Warning: Neither 'doi' nor 'title' found. No duplicate removal based on doi/title.")
    print(f'Number of rows after duplicate removal: {len(df)}. Total duplicates removed: {original_len - len(df)}')
    return df

def extract_first_author(df: pd.DataFrame) -> pd.DataFrame:
    """
    Extract the first author from 'authors' column and apply name formatting.
    Creates a new column 'first_author'.
    """
    if 'author' in df.columns:
        # Split the author field by '.;' and take the first
        df['first_author'] = df['author'].str.split('.;').str[0].str.strip()
        df['first_author'] = df['first_author'].apply(format_name)
    else:
        print("Warning: 'authors' column not found. 'first_author' not extracted.")
        df['first_author'] = ""
    return df

# Clean the 'first_author' column
def clean_first_author(name):
    """
    Clean the first_author name:
    - Remove everything after the first comma or period.
    - Remove commas and periods entirely.
    """
    if pd.isna(name) or not isinstance(name, str):
        return ""

    # Find the first comma or period and truncate the name
    name = name.split(",")[0].split(".")[0]

    # Remove any remaining commas or periods (unlikely after truncation)
    name = name.replace(",", "").replace(".", "")

    return name

def create_bibtex_column(df: pd.DataFrame) -> pd.DataFrame:
    """
    Create and disambiguate a 'bibtex' column of the form 'first_author_year',
    adding numeric suffixes when duplicates occur.
    """
    if 'first_author' not in df.columns:
        df['first_author'] = ""

    if 'year' not in df.columns:
        # If there's no 'year' column, use a placeholder (e.g., 'NA')
        df['year'] = "NA"

    # Apply the cleaning function
    df['first_author'] = df['first_author'].apply(clean_first_author)
    df['bibtex'] = df['first_author'] + '_' + df['year'].astype(str)
    bibtex_counts = {}
    final_bibtex = []

    for bib in df['bibtex']:
        if bib not in bibtex_counts:
            bibtex_counts[bib] = 1
            final_bibtex.append(bib)
        else:
            versioned_bibtex = f"{bib}_{bibtex_counts[bib]}"
            bibtex_counts[bib] += 1
            final_bibtex.append(versioned_bibtex)

    df['bibtex'] = final_bibtex
    return df

def rename_columns_for_final_schema(df: pd.DataFrame) -> pd.DataFrame:
    """
    Map original column names to final schema where necessary.
    Example:
        'authors' -> 'author',
        'source_title' -> 'journal'.
        'link' -> 'url',
        'publisher' -> 'publisher_long',
    """
    rename_map = {
        'authors': 'author',
        'source_title': 'journal',
        'link': 'url',
        'publisher': 'publisher_long',
        # Add more renames as needed
    }
    return df.rename(columns=rename_map)

def ensure_and_reorder_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Ensure all required columns are present, even if empty,
    then reorder them to the final desired order.
    """
    final_columns = [
        'bibtex',
        'title',
        'abstract',
        'year',
        'index_keywords',
        'document_type',
        'author',
        'doi',
        'journal',
        'volume',
        'issue',
        'publisher',
        'publisher_long',
        'attachments',
        'url',
        'cited_by',
        'references',
        'open_access',
        'first_author',
        'ai_output',
        'year_relevancy',
        'pdf_analysis_output',
        'pdf_name',
        'methodology',
        'status_cross_check_title_abstract',
        'other_note',
        'experimental'
    ]

    # Ensure all final columns exist
    for col in final_columns:
        if col not in df.columns:
            df[col] = ""

    # Keep only columns in final_columns and reorder
    df = df[final_columns]
    return df

def combine_scopus_csvs_to_excel(folder_path: str, output_excel_path: str) -> None:
    """
    Main function that combines multiple Scopus CSV files in a folder,
    applies cleaning/formatting, removes duplicates, and saves to Excel.
    """
    # 1. Gather all CSV files
    # csv_files = gather_csv_files(folder_path)
    df=parse_scopus_bib_files(folder_path)
    # if not csv_files:
    #     print(f"No CSV files found in {folder_path}. Process aborted.")
    #     return

    # 2. Load CSV files into a single DataFrame
    # df = load_csv_files(csv_files)
    if df.empty:
        print("No valid data to process. Process aborted.")
        return

    # 3. Clean column names
    df = clean_column_names(df)

    # 4. Filter rows based on conditions
    df = filter_rows(df)

    # 5. Remove duplicates by DOI and Title
    df = remove_duplicates_by_doi_and_title(df)

    # 6. Rename columns to final schema
    df = rename_columns_for_final_schema(df)

    # 7. Extract the first author
    df = extract_first_author(df)
    unique_val=df['publisher_long'].unique()
    print(f'These are the unique publisher_long values: {unique_val}')
    df = map_publisher_long(df)

    unique_val=df['publisher'].unique()
    print(unique_val)
    # 8. Create bibtex column
    df = create_bibtex_column(df)

    # 9. Ensure final columns exist and reorder
    df = ensure_and_reorder_columns(df)

    # 10. Write the combined DataFrame to Excel
    df.to_excel(output_excel_path, index=False, engine='openpyxl')
    print(f"Combined file has been saved to: {output_excel_path}")

if __name__ == "__main__":
    folder_path = r"C:\Users\balan\OneDrive - ums.edu.my\research_related\corona_discharge\database\scopus"
    output_excel =  r"C:\Users\balan\OneDrive - ums.edu.my\research_related\corona_discharge\database\combined_filtered.xlsx"

    combine_scopus_csvs_to_excel(folder_path, output_excel)
