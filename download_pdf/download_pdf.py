import pandas as pd
import os
import glob
import json
import logging
from pdf_ieee import do_download_ieee
from pdf_scihub import do_download_scihub

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
    """Filter rows where 'ai_output' is 'relevance' and 'pdf_name' is empty."""
    return data[(data['ai_output'] == 'relevance') & (data['pdf_name'].isna() | data['pdf_name'].str.strip().eq(''))]


def categorize_urls(data):
    """Categorize URLs into domain-specific dictionaries."""
    categories = {
        "ieeexplore": {},
        "springer": {},
        "mdpi": {},
        "sciencedirect": {},
        "scopus": {},
        "ncbi": {},
        "other": {},
    }

    def add_to_dict(target_dict, bibtex, url, doi, title):
        if bibtex not in target_dict:
            target_dict[bibtex] = {"url": [], "doi": doi, "title": title}
        target_dict[bibtex]["url"].append(url)

    for _, row in data.iterrows():
        bibtex = row.get('bibtex', '')
        urls = row.get('url', '')  # Can be multiple URLs separated by newline
        doi = row.get('doi', '')
        title = row.get('title', '')

        for url in str(urls).split('\n'):
            url = url.strip()
            if not url:
                continue
            if "ieeexplore.ieee.org" in url:
                add_to_dict(categories["ieeexplore"], bibtex, url, doi, title)
            elif "scopus.com" in url:
                add_to_dict(categories["scopus"], bibtex, url, doi, title)
            elif "ncbi.nlm.nih.gov" in url:
                add_to_dict(categories["ncbi"], bibtex, url, doi, title)
            elif "springer" in url:
                add_to_dict(categories["springer"], bibtex, url, doi, title)
            elif "mdpi" in url:
                add_to_dict(categories["mdpi"], bibtex, url, doi, title)
            elif "sciencedirect" in url:
                add_to_dict(categories["sciencedirect"], bibtex, url, doi, title)
            else:
                add_to_dict(categories["other"], bibtex, url, doi, title)

    return categories


def process_scihub_downloads(categories, output_folder, data):
    """Download PDFs using Sci-Hub and update the data based on JSON responses."""
    logging.info("Starting Sci-Hub downloads...")
    categories={'scopus':categories['scopus']}
    for category in categories.values():
        try:
            do_download_scihub(category)
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
    ieee_keys_to_attempt = data[(data['scihub_pdf_download'] != 'success') & (data['bibtex'].isin(categories['ieeexplore'].keys()))]['bibtex'].unique()
    fallback_ieee_dict = {k: v for k, v in categories['ieeexplore'].items() if k in ieee_keys_to_attempt}

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


def save_data(data, file_path):
    """Save the updated data back to an Excel file."""
    output_excel_path = file_path.replace('.xlsx', '_updated_v3.xlsx')
    data.to_excel(output_excel_path, index=False)
    logging.info(f"Updated data has been saved to {output_excel_path}")


if __name__ == "__main__":
    # Paths and constants
    file_path = r'../research_filter/database/eeg_test_simple_with_bibtex_v1.xlsx'
    output_folder = r'C:\Users\balan\OneDrive - ums.edu.my\research_related\0 eeg_trend_till24\eeg_review'

    # Workflow
    data = load_data(file_path)
    data_filtered = filter_relevant_data(data)
    categories = categorize_urls(data_filtered)
    process_scihub_downloads(categories, output_folder, data_filtered)

    # Skipping the IEEE fallback step for testing
    # process_fallback_ieee(categories, data_filtered, output_folder)

    save_data(data_filtered, file_path)
