import os
import pandas as pd
from post_code_saviour.excel_to_bib import generate_bibtex
from setting.project_path import project_folder

# Define your project
project_review = 'corona_discharge'

# Load project paths
path_dic = project_folder(project_review=project_review)
main_folder = path_dic['main_folder']

# Define input and output paths
input_excel = os.path.join(main_folder, 'database', 'combined_filtered.xlsx')
output_bib = os.path.join(main_folder, 'database', 'filtered_output.bib')

# Load the filtered Excel file
df = pd.read_excel(input_excel)

# Generate BibTeX file
generate_bibtex(df, output_file=output_bib)
