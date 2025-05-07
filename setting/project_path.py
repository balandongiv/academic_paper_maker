import os
def project_folder(project_review=None):

    if project_review is None:
        raise ValueError("Please specify the project_review parameter.")
    if project_review=='eeg_review':
        main_folder = rf"G:\My Drive\research_related\0 eeg_trend_till24\eeg_review"
        csv_path=os.path.join(main_folder,'database','eeg_review.xlsx')
    elif project_review=='corona_discharge':
        # main_folder = r"G:\My Drive\research_related\corona_discharge"
        main_folder=r'C:\Users\balan\IdeaProjects\academic_paper_maker\bib_example'
        # csv_path=os.path.join(main_folder,'database','combined_filtered.xlsx')
        csv_path=r'C:\Users\balan\IdeaProjects\academic_paper_maker\bib_example\xcombined_filtered.xlsx'
        # csv_path=rf"C:\Users\balan\OneDrive - ums.edu.my\research_related\corona_discharge\database\combined_filtered.xlsx"
    elif project_review=='wafer_defect':
        main_folder = r"G:\My Drive\research_related\wafer_defect"
        csv_path= os.path.join(main_folder ,'database','wafer_database.xlsx')
    path_dict = dict(
        main_folder=main_folder,
        csv_path=csv_path
    )
    return path_dict