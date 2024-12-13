import pandas as pd
from pdf_ieee import do_download_ieee

# Path to the Excel file
file_path = r'../research_filter/eeg_test_simple_with_bibtex.xlsx'
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

    # Split URLs by newline and iterate over them
    for url in str(urls).split('\n'):
        url = url.strip()
        if not url:
            continue

        # Check which category the URL falls into
        if "ieeexplore.ieee.org" in url:
            if bibtex not in ieeexplore_dict:
                ieeexplore_dict[bibtex] = []
            ieeexplore_dict[bibtex].append(url)
        elif "scopus.com" in url:
            if bibtex not in scopus_dict:
                scopus_dict[bibtex] = []
            scopus_dict[bibtex].append(url)
        elif "ncbi.nlm.nih.gov" in url:
            if bibtex not in ncbi_dict:
                ncbi_dict[bibtex] = []
            ncbi_dict[bibtex].append(url)
        elif "springer" in url:
            if bibtex not in springer_dict:
                springer_dict[bibtex] = []
            springer_dict[bibtex].append(url)

        elif "mdpi" in url:
            if bibtex not in mdpi_dict:
                mdpi_dict[bibtex] = []
            mdpi_dict[bibtex].append(url)
        elif "sciencedirect" in url:
            if bibtex not in sciencedirect_dict:
                sciencedirect_dict[bibtex] = []
            sciencedirect_dict[bibtex].append(url)
        else:
            # If it doesn't match known cases, store in 'other_dict'
            if bibtex not in other_dict:
                other_dict[bibtex] = []
            other_dict[bibtex].append(url)

# At this point, you have four dictionaries:
# ieeexplore_dict, springer_dict, mdpi_dict, and other_dict,
# each mapping a bibtex to a list of URLs from that source.

# Example: Using the categorized data
# If you want to process IEEE URLs using `do_download_ieee`, for example:
for bibtex, urls in ieeexplore_dict.items():
    for url in urls:
        # Call your download function or other processing here
        do_download_ieee(url, bibtex=bibtex)
