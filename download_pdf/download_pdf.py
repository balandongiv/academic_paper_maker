import pandas as pd
from pdf_ieee import do_download_ieee
# Load the Excel file
file_path = r'C:\Users\balan\IdeaProjects\academic_paper_maker\research_filter\eeg_test_simple_with_bibtex.xlsx'
data = pd.read_excel(file_path)

# Initialize an empty dictionary to store the results
ieeexplore_dict = {}

# Iterate over the rows in the DataFrame to extract the desired data
for index, row in data.iterrows():
    urls = str(row.get('url', '')).split(';')  # Assuming URLs are separated by semicolons
    bibtex = row.get('bibtex', '')
    for url in urls:
        if url.startswith('https://ieeexplore'):
            ieeexplore_dict[bibtex] = url

do_download_ieee(ieeexplore_dict)
h=1