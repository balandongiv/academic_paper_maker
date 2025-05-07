import os
from download_pdf.database_preparation import combine_scopus_bib_to_excel
# from personal_note.tutorial import output_excel

main_folder=r"C:\Users\balan\IdeaProjects\academic_paper_maker\bib_example"
# folder_path = r"C:\Users\balan\OneDrive - ums.edu.my\research_related\corona_discharge\database\scopus"
folder_path=r'C:\Users\balan\IdeaProjects\academic_paper_maker\bib_example'
output_excel =  os.path.join(main_folder,'combined_filtered.xlsx')
# output_excel =  r"C:\Users\balan\OneDrive - ums.edu.my\research_related\corona_discharge\database\combined_filtered.xlsx"

combine_scopus_bib_to_excel(folder_path, output_excel)