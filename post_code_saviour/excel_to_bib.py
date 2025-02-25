import pandas as pd
import os
import re

# Define common BibTeX fields
BIBTEX_FIELDS = {
    "title": ["title", "booktitle", "paper_title"],
    "author": ["author", "authors", "writer"],
    "year": ["year", "pub_year", "publication_year"],
    "journal": ["journal", "conference", "proceedings"],
    "volume": ["volume", "vol"],
    "number": ["number", "issue"],
    "pages": ["pages", "page"],
    "doi": ["doi"],
    "publisher": ["publisher"],
    "url": ["url", "link"],
}

def format_authors(author_str):
    """Format author names properly for BibTeX."""
    if pd.isna(author_str) or not isinstance(author_str, str):
        return ""

    authors = author_str.split(",") if "," in author_str else author_str.split(" and ")
    formatted_authors = []

    for author in authors:
        author = author.strip()

        # Match "First Last" or "F. Last"
        if re.match(r"^[A-Z]\.? [A-Za-z-]+$", author):
            first_initial, last_name = author.split(" ", 1)
            formatted_authors.append(f"{first_initial}, {last_name}")

        # Match "Last, First"
        elif re.match(r"^[A-Za-z-]+, [A-Za-z-]+$", author):
            formatted_authors.append(author)

        # Fallback: Keep original
        else:
            formatted_authors.append(author)

    return " and ".join(formatted_authors)

def detect_columns(df):
    """Detects relevant columns by mapping them to BibTeX fields."""
    column_mapping = {}
    for key, aliases in BIBTEX_FIELDS.items():
        for alias in aliases:
            for col in df.columns:
                if alias.lower() in col.lower():
                    column_mapping[key] = col
                    break  # Stop after the first match
    return column_mapping

def generate_bibtex_entry(row, column_mapping, bibtex_column):
    """Generate a single BibTeX entry using the provided BibTeX citation key."""
    entry_type = "article"  # Default type; modify if needed
    citation_key = row[bibtex_column] if bibtex_column in row and pd.notna(row[bibtex_column]) else "unknown"

    bibtex_entry = f"@{entry_type}{{{citation_key},\n"
    for field, col_name in column_mapping.items():
        if col_name in row and pd.notna(row[col_name]):
            value = row[col_name]
            if field == "author":
                value = format_authors(value)  # Apply author formatting
            bibtex_entry += f"  {field} = {{{value}}},\n"
    bibtex_entry += "}\n"
    return bibtex_entry

def generate_bibtex(df, output_file="ascexmpl-new.bib"):
    """Generate a BibTeX file from a DataFrame using the 'bibtex' column for citation keys."""
    if "bibtex" not in df.columns:
        print("No 'bibtex' column found! Cannot generate citation keys.")
        return

    column_mapping = detect_columns(df)

    with open(output_file, "w", encoding="utf-8") as f:
        for _, row in df.iterrows():
            bibtex_entry = generate_bibtex_entry(row, column_mapping, "bibtex")
            f.write(bibtex_entry + "\n")

    print(f"BibTeX file generated: {output_file}")

if __name__ == "__main__":
    # Load the Excel file
    file_path = r"G:\My Drive\research_related\0 eeg_trend_till24\eeg_review\database\eeg_review.xlsx"
    output_path=r"G:\My Drive\research_related\0 eeg_trend_till24\eeg_review\database\eeg_review.bib"
    if not os.path.exists(file_path):
        print(f"Excel file not found at {file_path}!")
    else:
        df = pd.read_excel(file_path)

        # Generate BibTeX
        generate_bibtex(df,output_file=output_path)
