from research_filter.agent_helper import validate_json_data
from setting.project_path import project_folder
import os
# DEBUG mode
DEBUG = True

path_dic=project_folder()
main_folder = path_dic['main_folder']

agent_name = "concept_and_technique"
column_name = "concept_and_technique"
yaml_path = "agent/agent_ml.yaml"


methodology_json_folder=os.path.join(main_folder,agent_name,'json_output')
multiple_runs_folder =os.path.join(main_folder,agent_name,'multiple_runs_folder')
final_cross_check_folder = os.path.join(main_folder,agent_name,'final_cross_check_folder')

csv_path = path_dic['csv_path']

# Default activity
DEFAULT_ACTIVITY = "analyse_pdf"  # abstract_filtering or analyse_pdf
if DEBUG:
    # If debugging, force activity to abstract_filtering to avoid multiple dropdown selections
    ACTIVITY_NOW = "analyse_pdf"
else:
    ACTIVITY_NOW = DEFAULT_ACTIVITY

# Placeholders
placeholders = {
    "topic": "EEG-based driver fatigue classification",
    "topic_context": "neurophysiological analysis"
}

# Hardcoded agent names based on activity
AGENT_NAME_MAPPING = {
    "abstract_filtering": "abstract_filter_fatigue_eeg",
    "analyse_pdf": "methodology_extractor_agent" # To change later to appropriate agent name
}

import os

# Get the directory of the current script
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Define the relative YAML path
YAML_PATH = os.path.join(SCRIPT_DIR, "agent","agents_fatigue_driving.yaml")
FILE_PATH = path_dic['csv_path']
# Files and paths
# FILE_PATH = r"..\research_filter\eeg_test_simple_with_bibtex_v1.xlsx"
# YAML_PATH = r"..\esearch_filter\agents_fatigue_driving.yaml"

# JSON output directory
JSON_OUTPUT_DIR = "json_output"
if not os.path.exists(JSON_OUTPUT_DIR):
    os.makedirs(JSON_OUTPUT_DIR)


def validate_json_data_abstract_filtering(json_input, system_prompt):
    """Validation logic specific to abstract_filtering."""
    return validate_json_data(json_input, system_prompt)


def validate_json_data_analyse_pdf(json_input, system_prompt):
    """Validation logic specific to analyse_pdf."""
    # return validate_json_data(json_input, system_prompt)
    return True, json_input


# Map activities to validation functions
validation_functions = {
    "abstract_filtering": validate_json_data_abstract_filtering,
    "analyse_pdf": validate_json_data_analyse_pdf,
}

# map columns to validation functions
col_df_saved = {
    "abstract_filtering":"ai_output",
    "analyse_pdf":"pdf_analysis"
}