import glob
import json
import logging
import os
from pdf_mdpi import do_download_mdpi
import pandas as pd

from pdf_ieee import do_download_ieee
from pdf_scihub import do_download_scihub
from pdf_sciencedirect import do_download_scincedirect
from pdf_ieee_search import do_download_ieee_search
from setting.project_path import project_folder
# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')


def load_data(file_path):
    """Load the data from the Excel file."""
    data = pd.read_excel(file_path)
    # Ensure necessary columns exist or create them
    if 'scihub_pdf_download' not in data.columns:
        data['scihub_pdf_download'] = ''
    if 'pdf_name' not in data.columns:
        data['pdf_name'] = ''
    return data

def filter_relevant_data(data):
    """
    Filter rows where 'ai_output' is 'relevance' and 'pdf_name' has no value
    (e.g., NaN, empty, or whitespace).

    Args:
        data (DataFrame): Input pandas DataFrame with columns 'ai_output' and 'pdf_name'.

    Returns:
        DataFrame: Filtered pandas DataFrame.
    """
    # Filter rows where 'ai_output' is 'relevance' and 'pdf_name' is empty or NaN
    filtered_data = data[
        (data['ai_output'] == 'relevance') &
        (data['pdf_name'].isnull() | data['pdf_name'].str.strip().eq(''))
        ]

    return filtered_data




def categorize_publisher(data):
    # Dictionary to dynamically hold publishers and their corresponding data
    categories = {}

    def add_to_dict(target_dict, publisher, bibtex, url, doi, title):
        # Ensure the publisher category exists
        if publisher not in target_dict:
            target_dict[publisher] = {}

        # Add bibtex entry if not already present
        if bibtex not in target_dict[publisher]:
            target_dict[publisher][bibtex] = {"url": [], "doi": doi, "title": title}

        # Append URL if available
        if url:
            target_dict[publisher][bibtex]["url"].append(url)

    for _, row in data.iterrows():
        bibtex = row.get('bibtex', '')
        urls = row.get('url', '')  # Can be multiple URLs separated by newline
        doi = row.get('doi', '')
        title = row.get('title', '')
        try:
            publisher = row.get('publisher', 'other').strip().lower() or 'other'
        except AttributeError:
            continue
        # Normalize publisher name
        publisher_key = publisher.split()[0]  # Take the first word as the key (e.g., "ieee", "mdpi")

        # Ensure urls is a string to prevent errors
        if not isinstance(urls, str):
            urls = ""

        # Add each URL (if multiple URLs are separated by newlines)
        for url in urls.split('\n'):
            add_to_dict(categories, publisher_key, bibtex, url.strip(), doi, title)

    return categories





def process_scihub_downloads(categories, output_folder, data):
    """Download PDFs using Sci-Hub and update the data based on JSON responses."""
    logging.info("Starting Sci-Hub downloads...")
    # categories={'scopus':categories['scopus']}
    for category in categories.values():
        try:
            do_download_scihub(category,output_folder)
        except Exception as e:
            logging.error(f"Error downloading from Sci-Hub: {e}")

    # Process Sci-Hub JSON responses
    logging.info("Processing Sci-Hub JSON responses...")
    json_files = glob.glob(os.path.join(output_folder, '*.json'))

    for json_file in json_files:
        bibtex_key = os.path.splitext(os.path.basename(json_file))[0]
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data_json = json.load(f)
            status = data_json.get('status', '').lower()
            data.loc[data['bibtex'] == bibtex_key, 'scihub_pdf_download'] = 'success' if status == 'success' else 'not available in scihub repo'
            if status == 'success' and 'pdf_name' in data_json:
                data.loc[data['bibtex'] == bibtex_key, 'pdf_name'] = data_json['pdf_name']
        except Exception as e:
            logging.error(f"Error reading {json_file}: {e}")


def process_fallback_ieee(categories, data, output_folder):
    """Attempt to download PDFs from IEEE for entries not available on Sci-Hub."""
    ieee_keys_to_attempt = data[(data['scihub_pdf_download'] != 'success') & (data['bibtex'].isin(categories['ieee'].keys()))]['bibtex'].unique()
    fallback_ieee_dict = {k: v for k, v in categories['ieee'].items() if k in ieee_keys_to_attempt}

    if fallback_ieee_dict:
        logging.info("Attempting IEEE-specific downloads for entries not available on Sci-Hub...")
        try:
            do_download_ieee(fallback_ieee_dict)
        except Exception as e:
            logging.error(f"Error downloading from IEEE: {e}")

        # Process IEEE JSON responses
        ieee_json_files = glob.glob(os.path.join(output_folder, '*.json'))
        for json_file in ieee_json_files:
            bibtex_key = os.path.splitext(os.path.basename(json_file))[0]
            if data.loc[data['bibtex'] == bibtex_key, 'scihub_pdf_download'].item() != 'success':
                try:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        data_json = json.load(f)
                    status = data_json.get('status', '').lower()
                    if 'ieee_pdf_download' not in data.columns:
                        data['ieee_pdf_download'] = ''
                    if status == 'success':
                        data.loc[data['bibtex'] == bibtex_key, 'ieee_pdf_download'] = 'success'
                        if 'pdf_name' in data_json:
                            data.loc[data['bibtex'] == bibtex_key, 'pdf_name'] = data_json['pdf_name']
                    else:
                        data.loc[data['bibtex'] == bibtex_key, 'ieee_pdf_download'] = 'not available in ieee repo'
                except Exception as e:
                    logging.error(f"Error reading {json_file}: {e}")


def process_fallback_ieee_search(categories, data, output_folder):
    """Attempt to download PDFs from IEEE for entries not available on Sci-Hub."""
    ieee_keys_to_attempt = data[(data['scihub_pdf_download'] != 'success') & (data['bibtex'].isin(categories['ieee'].keys()))]['bibtex'].unique()
    fallback_ieee_dict = {k: v for k, v in categories['ieee'].items() if k in ieee_keys_to_attempt}

    if fallback_ieee_dict:
        logging.info("Attempting IEEE-specific downloads for entries not available on Sci-Hub...")
        try:
            do_download_ieee_search(fallback_ieee_dict)
        except Exception as e:
            logging.error(f"Error downloading from IEEE: {e}")

        # Process IEEE JSON responses
        ieee_json_files = glob.glob(os.path.join(output_folder, '*.json'))
        for json_file in ieee_json_files:
            bibtex_key = os.path.splitext(os.path.basename(json_file))[0]
            if data.loc[data['bibtex'] == bibtex_key, 'scihub_pdf_download'].item() != 'success':
                try:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        data_json = json.load(f)
                    status = data_json.get('status', '').lower()
                    if 'ieee_pdf_download' not in data.columns:
                        data['ieee_pdf_download'] = ''
                    if status == 'success':
                        data.loc[data['bibtex'] == bibtex_key, 'ieee_pdf_download'] = 'success'
                        if 'pdf_name' in data_json:
                            data.loc[data['bibtex'] == bibtex_key, 'pdf_name'] = data_json['pdf_name']
                    else:
                        data.loc[data['bibtex'] == bibtex_key, 'ieee_pdf_download'] = 'not available in ieee repo'
                except Exception as e:
                    logging.error(f"Error reading {json_file}: {e}")


def process_fallback_mdpi(categories, data, output_folder):
    """Attempt to download PDFs from IEEE for entries not available on Sci-Hub."""
    mdpi_keys_to_attempt = data[(data['scihub_pdf_download'] != 'success') & (data['bibtex'].isin(categories['mdpi'].keys()))]['bibtex'].unique()
    fallback_mdpi_dict = {k: v for k, v in categories['mdpi'].items() if k in mdpi_keys_to_attempt}

    if fallback_mdpi_dict:
        logging.info("Attempting IEEE-specific downloads for entries not available on Sci-Hub...")
        try:
            do_download_mdpi(fallback_mdpi_dict)
        except Exception as e:
            logging.error(f"Error downloading from IEEE: {e}")

def process_fallback_sciencedirect(categories, data, output_folder):
    """Attempt to download PDFs from IEEE for entries not available on Sci-Hub."""
    sciencedirect_keys_to_attempt = data[(data['scihub_pdf_download'] != 'success') & (data['bibtex'].isin(categories['sciencedirect'].keys()))]['bibtex'].unique()
    fallback_sciencedirect_dict = {k: v for k, v in categories['sciencedirect'].items() if k in sciencedirect_keys_to_attempt}

    if fallback_sciencedirect_dict:
        logging.info("Attempting IEEE-specific downloads for entries not available on Sci-Hub...")
        try:
            do_download_scincedirect(fallback_sciencedirect_dict)
        except Exception as e:
            logging.error(f"Error downloading from IEEE: {e}")

def save_data(data, file_path):
    """Save the updated data back to an Excel file."""
    output_excel_path = file_path.replace('.xlsx', '_updated_v3.xlsx')
    data.to_excel(output_excel_path, index=False)
    logging.info(f"Updated data has been saved to {output_excel_path}")

def run_pipeline(file_path):
    # Workflow
    data_filtered  = load_data(file_path)
    # data_filtered = filter_relevant_data(data_filtered)
    categories = categorize_publisher(data_filtered)
    return categories,data_filtered

if __name__ == "__main__":
    # Paths and constants
    project_review='wafer_defect'
    path_dic=project_folder(project_review=project_review)
    main_folder = path_dic['main_folder']

    # csv_path = path_dic['csv_path']
    # pdf_store_directory = os.path.join(main_folder, 'pdf')


    file_path = path_dic['csv_path']
    output_folder =  os.path.join(main_folder, 'pdf')


    categories,data_filtered=run_pipeline(file_path)
    # First step, we will always use the scihub to download the pdf
    process_scihub_downloads(categories, output_folder, data_filtered)

    # Skipping the IEEE fallback step for testing
    # process_fallback_ieee(categories, data_filtered, output_folder)

    # process_fallback_ieee_search(categories, data_filtered, output_folder)

    # process_fallback_mdpi(categories, data_filtered, output_folder)

    # The sciencedirect only allow to extract the url, but not able to download the pdf due to the tight security feature
    # process_fallback_sciencedirect(categories, data_filtered, output_folder)
    # save_data(data_filtered, file_path)
