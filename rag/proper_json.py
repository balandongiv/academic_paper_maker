import os
from langchain_community.document_loaders import DirectoryLoader, JSONLoader

# Define the directory containing JSON files
folder_path = r"G:\My Drive\research_related\0 eeg_trend_till24\eeg_review\methodology_gap_extractor\json_output\test"

# Define a schema to extract multiple keys
jq_schema = '{current_limitations: .discussion[].current_limitations, comparison_with_existing_methods: .discussion[].comparison_with_existing_methods}'

# Load all JSON files in the directory
loader = DirectoryLoader(
    path=folder_path,
    glob="*.json",  # Load only JSON files
    loader_cls=JSONLoader,
    loader_kwargs={
        "jq_schema": jq_schema,
        "text_content": False
    }
)

# Load the data from all JSON files
data = loader.load()

# Print extracted data
print(data)
