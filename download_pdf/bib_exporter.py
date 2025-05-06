# -*- coding: utf-8 -*-
# Requires: pip install bibtexparser pandas

import os
import glob
import pandas as pd
import bibtexparser

def parse_scopus_bib_files(folder_path, output_csv=None):
    """
    Parses all .bib files in the specified folder and returns a pandas DataFrame.

    Args:
        folder_path (str): Path to the folder containing .bib files.
        output_csv (str): Optional path to save the merged DataFrame as a CSV file.

    Returns:
        pd.DataFrame: DataFrame containing parsed bibliographic records.
    """
    fields = [
        "author", "title", "year", "journal", "volume", "number", "doi", "url",
        "affiliations", "abstract", "author_keywords", "keywords",
        "correspondence_address", "publisher", "issn", "language",
        "abbrev_source_title", "type", "publication_stage", "source", "note"
    ]

    # Create full file paths for all .bib files in the folder
    bib_files = glob.glob(os.path.join(folder_path, "*.bib"))
    print(f'Found {len(bib_files)} .bib files in {folder_path}')
    records = []
    for bib_file in bib_files:
        with open(bib_file, encoding='utf-8') as bf:
            bib = bibtexparser.load(bf)
        for entry in bib.entries:
            rec = {field: entry.get(field) for field in fields}
            doc_type = entry.get('type') or entry.get('ENTRYTYPE')
            rec['document_type'] = doc_type.lower() if doc_type else None
            records.append(rec)

    df = pd.DataFrame(records, columns=fields + ['document_type'])

    if output_csv:
        df.to_csv(output_csv, index=False)

    return df

# Example usage:
if __name__ == "__main__":
    folder = r"C:\Users\balan\IdeaProjects\academic_paper_maker\bib_example"
    df = parse_scopus_bib_files(folder, output_csv="merged_scopus_output.csv")
    df.to_excel("merged_scopus_output.xlsx", index=False)
    print(df.head())
