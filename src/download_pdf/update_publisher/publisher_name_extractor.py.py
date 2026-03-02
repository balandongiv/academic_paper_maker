'''

This script is the second approach in updating the publisher information in the main Excel file.
In most cases, the journal names in the main file are incomplete or inconsistent with the journal names in the supporting lists.

The json file is saved in the following format:
{
    "title": "The journal name : This is what we will search in google",
    "url": {
        "href": "The URL of the search result. For simplicity, we will only save the first search result",
        "text": "The title of the search result: Often, this is the publisher name"
    }
}

The json file will be saved in the following directory structure:
main_directory
|__ bibtex_key
|__ bibtex_key.json
|__ bibtex_key
|__ bibtex_key.json

Then, the script will process the json files and group the data based on the URL middle names.

The URL middle name is extracted from the URL up to the first '.my'. The middle name is used to group the data.
If the middle name is not found in the dynamic groups, the data will be grouped under 'other'.

'''



import json
import os
import re
from collections import defaultdict, Counter

import pandas as pd

from download_pdf.browse_internet.googlesearch_publisher import process_keywords

# Constants
THRESHOLD = 3

def extract_middle_name(url):
    """
    Extract the middle name for grouping from the URL.
    Specific cleanup rules are applied for certain domains.
    """
    try:
        match = re.match(r"https://([\w\.]+)/", url)
        if match:
            domain_parts = match.group(1).split('.')

            # Handle specific cases
            if "wiley" in domain_parts:
                return "wiley"
            if "springer" in domain_parts:
                return "springer"
            if "iopscience" in domain_parts:
                return "iopscience"
            if "iopscience" in domain_parts:
                return "iopscience"
            if "ieeexplore" in domain_parts:
                return "ieee"

            # General case: Ensure there are enough parts in the domain
            if len(domain_parts) >= 3:
                part_2 = domain_parts[-2]
                part_3 = domain_parts[-3]
                if part_3 == "www":
                    return part_2
                return f"{part_2}_{part_3}"
            elif len(domain_parts) == 2:
                return domain_parts[0]
        print(f"Unsupported URL structure: {url}")
    except Exception as e:
        print(f"Error processing URL '{url}': {e}")
    return None

def get_group_for_url(url, dynamic_groups):
    """
    Determine the group for a given URL based on dynamically created groups.
    """
    middle_name = extract_middle_name(url)
    if middle_name in dynamic_groups:
        return middle_name
    return "other"

def process_json_file(filepath):
    """
    Process a single JSON file and return its URL, key, and data if valid.
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as file:
            data = json.load(file)
            if isinstance(data, dict) and "url" in data and "href" in data["url"]:
                url = data["url"]["href"]
                key = os.path.splitext(os.path.basename(filepath))[0]
                return url, key, data
    except (json.JSONDecodeError, KeyError, IOError) as e:
        print(f"Error processing file {filepath}: {e}")
    return None, None, None

def analyze_url_counts(directory):
    """
    Analyze the counts of URLs (up to .my) from JSON files.
    """
    url_counter = Counter()

    for root, _, files in os.walk(directory):
        for filename in files:
            if filename.endswith(".json"):
                filepath = os.path.join(root, filename)
                url, _, _ = process_json_file(filepath)
                if url:
                    middle_name = extract_middle_name(url)
                    if middle_name:
                        url_counter[middle_name] += 1

    return url_counter

def process_directory(directory, dynamic_groups):
    """
    Traverse directories and group JSON data based on URL middle names.
    """
    grouped_data = defaultdict(dict)

    for root, _, files in os.walk(directory):
        for filename in files:
            if filename.endswith(".json"):
                filepath = os.path.join(root, filename)
                url, key, data = process_json_file(filepath)
                if url and key and data:
                    group = get_group_for_url(url, dynamic_groups)
                    grouped_data[group][key] = data

    return grouped_data

def load_and_filter_excel(file_path):
    """
    Load and filter data from an Excel file.
    """
    data = pd.read_excel(file_path)
    filtered_data = data[(data['ai_output'] == 'relevance') & (data['publisher'].isna()) & (data['journal'].notna())]

    return {
        row['bibtex']: row['journal']
        for _, row in filtered_data.iterrows()
        if pd.notna(row['bibtex']) and pd.notna(row['journal'])
    }

def update_excel_with_publishers(excel_file_path, grouped_data):
    """
    Update the Excel file with publisher names from grouped_data.
    """
    # Load the Excel file
    data = pd.read_excel(excel_file_path)

    # Iterate over rows and update publisher column based on bibtex
    for index, row in data.iterrows():
        bibtex = row.get('bibtex')
        for group, entries in grouped_data.items():
            if bibtex in entries:
                # Extract publisher name (group name in grouped_data)
                publisher_name = group
                data.at[index, 'publisher'] = publisher_name
                break  # Exit loop once a match is found

    # Save the updated Excel file
    updated_file_path = excel_file_path.replace('.xlsx', '_updated.xlsx')
    data.to_excel(updated_file_path, index=False)
    print(f"Excel file updated and saved to {updated_file_path}")


def overview_publisher(parent_directory):
    # Analyze URL statistics
    url_counts = analyze_url_counts(parent_directory)
    filtered_url_counts = {url: count for url, count in url_counts.items() if count >= THRESHOLD}

    # Display URL statistics
    print(f"URL Statistics (occurrence >= {THRESHOLD}):")
    for url, count in sorted(filtered_url_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"'{url}': {count} occurrences")

    # Create dynamic groups
    dynamic_groups = set(filtered_url_counts.keys())

    # Process the directory and group data
    grouped_data = process_directory(parent_directory, dynamic_groups)

    print("\nGrouped Data:")
    # Output grouped data
    for group, entries in grouped_data.items():
        print(f"\nGroup: {group}")
        print(f"Number of entries: {len(entries)}")
        for key, value in entries.items():
            print(f"{key} = {value}")

def extract_and_group_publishers(parent_directory, excel_file_path, geckodriver_path, firefox_binary_path, firefox_profile_path):
    """
    Main processing logic encapsulated in a function.
    """
    # Load and filter Excel data
    keywords = load_and_filter_excel(excel_file_path)
    do_internet_search = True
    if do_internet_search:
        # Process keywords
        process_keywords(keywords, geckodriver_path, firefox_binary_path, firefox_profile_path, parent_directory)

    grouped_data = process_directory(parent_directory, analyze_url_counts(parent_directory).keys())

    # Update Excel file with the extracted publishers
    update_excel_with_publishers(excel_file_path, grouped_data)

def main():
    # Paths
    geckodriver_path = r"D:\\geckodrive\\geckodriver.exe"
    firefox_binary_path = r"C:\\Program Files\\Mozilla Firefox\\firefox.exe"
    firefox_profile_path = r"C:\\Users\\balan\\AppData\\Roaming\\Mozilla\\Firefox\\Profiles\\ssjd4eo7.default-release"
    parent_directory = r"C:\\Users\\balan\\OneDrive - ums.edu.my\\research_related\\0 eeg_trend_till24\\eeg_review\\incomplete_publisher_name"
    excel_file_path = os.path.join(  os.path.join(os.path.dirname(__file__), "../../research_filter/database"), "eeg_review.xlsx")

    # Process all
    extract_and_group_publishers(parent_directory, excel_file_path, geckodriver_path, firefox_binary_path, firefox_profile_path)

if __name__ == "__main__":
    main()
