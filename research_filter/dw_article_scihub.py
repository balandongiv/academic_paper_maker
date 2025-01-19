import logging
import os

import pandas as pd
from tqdm import tqdm

from scidownl.api.scihub import scihub_download
from setting.project_path import project_folder

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)




logger = logging.getLogger(__name__)

def download_paper(title, output_directory,bibtex_val):
    """
    Download a research paper from Sci-Hub. If the download fails or the file is too small,
    attempts to download the paper using alternative search and download methods.

    Parameters:
        title (str): The title of the research paper.
        output_directory (str): The directory to save the PDF.

    Returns:
        str: The result of the download attempt ('Success', 'File too small', or 'No PDF found').
    """
    # filename = "_".join(title.split()) + ".pdf"
    output_path = os.path.join(output_directory, bibtex_val + ".pdf")

    # Check if the file already exists
    if os.path.exists(output_path):
        logger.info(f"File already exists: {output_path}")
        return "Success"

    # Attempt to download using Sci-Hub
    try:
        scihub_download(title, out=output_path)
        if os.path.exists(output_path):
            file_size = os.path.getsize(output_path)
            file_size_kb = file_size / 1024
            if file_size_kb < 10:
                logger.warning(f"Downloaded file '{output_path}' is too small: {file_size_kb} KB")
                os.remove(output_path)  # Remove the invalid file

                return 'File too small'
            else:
                logger.info(f"Successfully downloaded: {output_path}")
                return "Success"
        else:
            logger.warning(f"Sci-Hub download failed for: {title}")

            return 'No PDF found'
    except Exception as e:
        logger.error(f"Error during Sci-Hub download for '{title}': {e}")

        logger.info("Attempting alternative download method.")

        return 'No PDF found'


def process_dataframe(input_csv, output_directory):
    """
    Process the DataFrame, downloading papers and updating success status.
    
    Parameters:
        input_csv (str): Path to the input CSV file.
        output_directory (str): Directory to store downloaded PDFs.
        
    Returns:
        pd.DataFrame: Updated DataFrame with download status.
    """
    df = pd.read_excel(input_csv)
    df = df[df['ai_output'] == True]
    df['pdf_scihub'] = ''

    for _, row in tqdm(df.iterrows(), total=len(df), desc="Processing papers"):
        title = row['title']
        bibtex_val = row['bibtex']
        download_status = download_paper(title, output_directory,bibtex_val)
        df.loc[df['title'] == title, 'pdf_scihub'] = download_status

    return df

if __name__ == "__main__":

    project_review='partial_discharge'
    path_dic=project_folder(project_review=project_review)
    main_folder = path_dic['main_folder']

    csv_path = path_dic['csv_path']
    pdf_store_directory = os.path.join(main_folder, 'pdf')

    # Create output directory
    os.makedirs(pdf_store_directory, exist_ok=True)


    # Process the DataFrame and update download status
    logger.info("Starting the download process...")
    updated_df = process_dataframe(csv_path, pdf_store_directory)

    # Save the updated DataFrame
    output_csv_path = os.path.join(main_folder, 'updated_corono_discharge_downloaded_status.xlsx')
    updated_df.to_excel(output_csv_path, index=False)
    logger.info(f"Updated DataFrame saved to {output_csv_path}")
