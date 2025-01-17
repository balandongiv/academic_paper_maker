import os
import glob
import pandas as pd
import re
import unicodedata

def format_name(name: str) -> str:
    """
    Normalize author name to remove diacritics and special characters.
    Return the cleaned name parts joined by underscores.
    """
    # Normalize text to remove diacritics (alien characters)
    name = unicodedata.normalize('NFD', name).encode('ascii', 'ignore').decode('utf-8')
    # Split the name on spaces, hyphens, and dots
    parts = re.split(r'[ \.-]+', name)
    # Combine all parts with underscores
    return '_'.join(parts)

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
        df = df[df['document_type'].isin(['Article', 'Review'])]
    else:
        print("Warning: 'document_type' column not found. No filtering on document_type applied.")

    if 'language_of_original_document' in df.columns:
        df = df[df['language_of_original_document'].isin(['English'])]
    else:
        print("Warning: 'language_of_original_document' column not found. No filtering on language applied.")

    return df

def remove_duplicates_by_doi_and_title(df: pd.DataFrame) -> pd.DataFrame:
    """
    Remove duplicate rows based on the combination of 'doi' and 'title'.
    If both 'doi' and 'title' are present, use both columns.
    If only one is present, use that.
    """
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
    Example: 'authors' -> 'author', 'source_title' -> 'journal'.
    """
    rename_map = {
        'authors': 'author',
        'source_title': 'journal',
        'link': 'url'
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
        'document_type',
        'author',
        'doi',
        'journal',
        'volume',
        'issue',
        'publisher',
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
    csv_files = gather_csv_files(folder_path)
    if not csv_files:
        print(f"No CSV files found in {folder_path}. Process aborted.")
        return

    # 2. Load CSV files into a single DataFrame
    df = load_csv_files(csv_files)
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
