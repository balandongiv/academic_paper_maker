import pandas as pd
from pdf_ieee import do_download_ieee

# Path to the Excel file
file_path = r'../research_filter/eeg_test_simple_with_bibtex_v1.xlsx'
data = pd.read_excel(file_path)

# Dictionaries for different URL categories
ieeexplore_dict = {}
springer_dict = {}
mdpi_dict = {}
other_dict = {}
sciencedirect_dict = {}
scopus_dict = {}
ncbi_dict = {}

# Iterate over the rows in the DataFrame to categorize URLs based on their domain
for index, row in data.iterrows():
    bibtex = row.get('bibtex', '')
    urls = row.get('url', '')  # Can be multiple URLs separated by newline
    doi = row.get('DOI', '')  # Assuming 'DOI' is a column in the DataFrame
    title = row.get('Title', '')  # Assuming 'Title' is a column in the DataFrame

    # Split URLs by newline and iterate over them
    for url in str(urls).split('\n'):
        url = url.strip()
        if not url:
            continue

        # Helper function to add subkeys
        def add_to_dict(target_dict, bibtex, url, doi, title):
            if bibtex not in target_dict:
                target_dict[bibtex] = {"url": [], "doi": doi, "title": title}
            target_dict[bibtex]["url"].append(url)

        # Check which category the URL falls into and add to corresponding dictionary
        if "ieeexplore.ieee.org" in url:
            add_to_dict(ieeexplore_dict, bibtex, url, doi, title)
        elif "scopus.com" in url:
            add_to_dict(scopus_dict, bibtex, url, doi, title)
        elif "ncbi.nlm.nih.gov" in url:
            add_to_dict(ncbi_dict, bibtex, url, doi, title)
        elif "springer" in url:
            add_to_dict(springer_dict, bibtex, url, doi, title)
        elif "mdpi" in url:
            add_to_dict(mdpi_dict, bibtex, url, doi, title)
        elif "sciencedirect" in url:
            add_to_dict(sciencedirect_dict, bibtex, url, doi, title)
        else:
            # If it doesn't match known cases, store in 'other_dict'
            add_to_dict(other_dict, bibtex, url, doi, title)

# Example: Using the categorized data
# Processing IEEE URLs with `do_download_ieee`
for bibtex, details in ieeexplore_dict.items():
    urls = details["url"]
    for url in urls:
        # Call your download function or other processing here
        do_download_ieee(url, bibtex=bibtex)
