import os
import json
from pathlib import Path

def project_folder(project_review=None, main_folder=None, config_file=None):
    """
    Returns a dict with:
      - main_folder: the root folder for this project_review
      - database_path: path to the project's database Excel file
      - scopus_path: subfolder for scopus-related files
      - xml_path: subfolder for xml-related files

    Parameters:
    - project_review (str): Project identifier.
    - main_folder (str or Path): Path to the main folder (used on first run).
    - config_file (str or Path): Optional custom path to the config JSON file.

    Usage:
    - First time: provide both `project_review` and `main_folder` to create and save.
    - Later: provide only `project_review` to retrieve saved paths.
    """

    if main_folder is None and project_review is None:
        raise ValueError("Please specify either the main_folder or project_review parameter.")
    if project_review is None:
        raise ValueError("Please specify the project_review parameter.")

    # Use default config file if none is provided
    config_path = Path(config_file) if config_file else Path('setting') / 'project_folders.json'
    config_path.parent.mkdir(parents=True, exist_ok=True)

    # Load existing config if it exists
    if config_path.exists():
        with open(config_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    else:
        data = {}

    # FIRST TIME: Save mapping and create folders
    if main_folder is not None:
        main_folder = Path(main_folder).resolve()

        # Save mapping
        data[project_review] = str(main_folder)
        with open(config_path, 'w', encoding='utf-8') as f:
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
                f"Project review {project_review!r} not found in {config_path}; "
                "please re-run with main_folder specified."
            )

    # Build path to files and folders
    return {
        'main_folder': main_folder,
        'database_path': main_folder / 'database' / f'{project_review}_database.xlsx',
        'scopus_path': main_folder / 'database' / 'scopus',
        'xml_path': main_folder / 'xml'
    }
