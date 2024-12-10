import os
from pydantic import RootModel
from typing import Any, Dict, Union

# DEBUG mode
DEBUG = False

# Default activity
DEFAULT_ACTIVITY = "abstract_filtering"  # abstract_filtering or analyse_pdf
if DEBUG:
    # If debugging, force activity to abstract_filtering to avoid multiple dropdown selections
    ACTIVITY_NOW = "abstract_filtering"
else:
    ACTIVITY_NOW = DEFAULT_ACTIVITY

# Placeholders
placeholders = {
    "topic": "EEG-based fatigue classification",
    "topic_context": "neurophysiological analysis"
}

# Hardcoded agent names based on activity
AGENT_NAME_MAPPING = {
    "abstract_filtering": "abstract_fatigue_filter",
    "analyse_pdf": "pdf_fatigue_reader"
}

import os

# Get the directory of the current script
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Define the relative YAML path
YAML_PATH = os.path.join(SCRIPT_DIR, "agents_fatigue_driving.yaml")
FILE_PATH = os.path.join(SCRIPT_DIR, "eeg_test_simple_with_bibtex.xlsx")
# Files and paths
# FILE_PATH = r"..\research_filter\eeg_test_simple_with_bibtex.xlsx"
# YAML_PATH = r"..\esearch_filter\agents_fatigue_driving.yaml"

# JSON output directory
JSON_OUTPUT_DIR = "json_output"
if not os.path.exists(JSON_OUTPUT_DIR):
    os.makedirs(JSON_OUTPUT_DIR)


# Pydantic model for validation using RootModel
class AIOutputModel(RootModel[Union[bool, Dict[str, Any]]]):
    pass
