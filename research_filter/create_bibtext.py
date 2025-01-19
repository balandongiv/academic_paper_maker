# import pandas as pd
# import os
# # Get the directory of the current script
# SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
#
# # Define the relative YAML path
# # YAML_PATH = os.path.join(SCRIPT_DIR, "agents_fatigue_driving.yaml")
# file_path = os.path.join(SCRIPT_DIR, "eeg_based_fatigue_classification_trends_new_2024.xlsx")
# output_file_path = os.path.join(SCRIPT_DIR, "eeg_test_simple_with_bibtex_v1.xlsx")
# # output_file_path = r'C:\Users\balan\IdeaProjects\academic_paper_maker\research_filter\eeg_test_simple_with_bibtex_v1.xlsx'
# # Load the EEG test data from the Excel file
# # file_path = r'C:\Users\balan\IdeaProjects\academic_paper_maker\research_filter\eeg_test_simple.xlsx'
# df = pd.read_excel(file_path)
#
# # Ensure the required columns 'Author' and 'Year' are present
# if 'Author' not in df.columns or 'Year' not in df.columns:
#     raise ValueError("The dataset must contain 'Author' and 'Year' columns.")
#
# # Extract the first author and format it
# df['first_author'] = df['Author'].str.split(',').str[0].str.strip()
# df['first_author'] = df['first_author'].str.split(' ').apply(
#     lambda x: f"{x[-1]}_{x[0][0]}" if len(x) > 1 else x[0]
# )
#
# # Create a bibtex column
# df['bibtex'] = df['first_author'] + '_' + df['Year'].astype(str)
#
# # Handle duplicates by adding versioning
# bibtex_counts = {}
# final_bibtex = []
#
# for bibtex in df['bibtex']:
#     if bibtex not in bibtex_counts:
#         bibtex_counts[bibtex] = 1
#         final_bibtex.append(bibtex)
#     else:
#         versioned_bibtex = f"{bibtex}_{bibtex_counts[bibtex]}"
#         bibtex_counts[bibtex] += 1
#         final_bibtex.append(versioned_bibtex)
#
# df['bibtex'] = final_bibtex
#
# # Save the modified dataframe to a new file
#
# df.to_excel(output_file_path, index=False)
