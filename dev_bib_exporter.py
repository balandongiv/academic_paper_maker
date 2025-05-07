
import os
from download_pdf.database_preparation import combine_scopus_bib_to_excel
from setting.project_path import project_folder

project_review='corona_discharge'
path_dic=project_folder(project_review=project_review)
main_folder = path_dic['main_folder']
folder_path=os.path.join(main_folder,'database','scopus')
output_excel =  os.path.join(main_folder,'database','combined_filtered.xlsx')
combine_scopus_bib_to_excel(folder_path, output_excel)