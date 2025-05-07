import os
# def project_folder(project_review=None, main_folder=None):
#     if main_folder is None and project_review is None:
#         raise ValueError("Please specify either the main_folder or project_review parameter.")
#     if project_review is None:
#         raise ValueError("Please specify the project_review parameter.")
#     if main_folder is None:
#         # we need set the main folder as json file
#         pass
#
#     if project_review=='eeg_review':
#         main_folder = rf"G:\My Drive\research_related\0 eeg_trend_till24\eeg_review"
#         csv_path=os.path.join(main_folder,'database','eeg_review.xlsx')
#     elif project_review=='corona_discharge':
#         # main_folder = r"G:\My Drive\research_related\corona_discharge"
#         main_folder=r'C:\Users\balan\IdeaProjects\academic_paper_maker\bib_example'
#         # csv_path=os.path.join(main_folder,'database','combined_filtered.xlsx')
#         csv_path=r'C:\Users\balan\IdeaProjects\academic_paper_maker\bib_example\xcombined_filtered.xlsx'
#         # csv_path=rf"C:\Users\balan\OneDrive - ums.edu.my\research_related\corona_discharge\database\combined_filtered.xlsx"
#     elif project_review=='wafer_defect':
#         main_folder = r"G:\My Drive\research_related\wafer_defect"
#         csv_path= os.path.join(main_folder ,'database','wafer_database.xlsx')
#     path_dict = dict(
#         main_folder=main_folder,
#         csv_path=csv_path
#     )
#     return path_dict


# def project_folder(project_review=None, main_folder=None):
#     if main_folder is None and project_review is None:
#         raise ValueError("Please specify either the main_folder or project_review parameter.")
#     if project_review is None:
#         raise ValueError("Please specify the project_review parameter.")
#     if main_folder is not None:
#         # we need set the main folder as json file. this usually being executed if the repository is being used for the first time
#         #create a json file, and under the json file, create info aout the main_folder .
#         # for first time execution, we need need to create a json file
#         pass
#     if project_review is not None and main_folder is None:
#         # this block is usually executed after the second and subsequent execution.
#         # we need to get main_folder from the json file
#         csv_path= os.path.join(main_folder ,'database',f'{project_review}_database.xlsx')
#         pass
#
#     path_dict = dict(
#         main_folder=main_folder,
#         csv_path=csv_path
#     )
#     return path_dict


import json
from pathlib import Path

# Set up config file path
_CONFIG_FILENAME = Path('setting') / 'project_folders.json'
_CONFIG_FILENAME.parent.mkdir(parents=True, exist_ok=True)

def project_folder(project_review=None, main_folder=None):
    """
    Returns a dict with:
      - main_folder: the root folder for this project_review
      - csv_path: path to the project's database Excel file

    On first run: provide both project_review and main_folder;
    this stores them in a JSON file and creates folder structure.
    On later runs: provide only project_review to look up main_folder.
    """
    if main_folder is None and project_review is None:
        raise ValueError("Please specify either the main_folder or project_review parameter.")
    if project_review is None:
        raise ValueError("Please specify the project_review parameter.")

    # Load existing config if it exists
    if _CONFIG_FILENAME.exists():
        with open(_CONFIG_FILENAME, 'r', encoding='utf-8') as f:
            data = json.load(f)
    else:
        data = {}

    # FIRST TIME: Save mapping and create folders
    if main_folder is not None:
        main_folder = Path(main_folder).resolve()

        # Save mapping
        data[project_review] = str(main_folder)
        with open(_CONFIG_FILENAME, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)

        # Create folder structure
        (main_folder / 'database' / 'scopus').mkdir(parents=True, exist_ok=True)
        (main_folder / 'pdf').mkdir(parents=True, exist_ok=True)
        (main_folder / 'xml').mkdir(parents=True, exist_ok=True)

    # SUBSEQUENT TIME: Load from mapping
    else:
        try:
            main_folder = Path(data[project_review])
        except KeyError:
            raise KeyError(
                f"Project review {project_review!r} not found in {_CONFIG_FILENAME}; "
                "please re-run with main_folder specified."
            )

    # Build path to the Excel file
    csv_path = os.path.join(main_folder, 'database', f'{project_review}_database.xlsx')
    scopus_path= os.path.join(main_folder, 'database', 'scopus')
    xml_path= os.path.join(main_folder, 'xml')
    return {
        'main_folder': main_folder,
        'database_path': csv_path,
        'scopus_path': scopus_path,
        'xml_path': xml_path
    }
