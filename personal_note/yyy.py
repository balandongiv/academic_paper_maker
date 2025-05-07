from download_pdf.database_preparation import combine_scopus_bib_to_excel
from setting.project_path import project_folder
import os
project_review='wafer_defect'
path_dic=project_folder(project_review=project_review)
folder_path =os.path.join(path_dic['main_folder'],'database','scopus')
output_excel = os.path.join(path_dic['main_folder'],'database','wafer_database.xlsx')


combine_scopus_bib_to_excel(folder_path, output_excel)
