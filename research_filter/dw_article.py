import os
import logging
from tqdm import tqdm
import pandas as pd
from scidownl.api.scihub import scihub_download
from research_filter.scrap_from_website import find_and_download_pdf
# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def create_pdf_store(directory):
    """Create a directory to store downloaded PDFs."""
    if not os.path.exists(directory):
        os.makedirs(directory)
        logger.info(f"Directory '{directory}' created.")
    else:
        logger.info(f"Directory '{directory}' already exists.")

import os
import logging

logger = logging.getLogger(__name__)

def download_paper(title, output_directory):
    """
    Download a research paper from Sci-Hub. If the download fails or the file is too small,
    attempts to download the paper using alternative search and download methods.

    Parameters:
        title (str): The title of the research paper.
        output_directory (str): The directory to save the PDF.

    Returns:
        str: The result of the download attempt ('Success', 'File too small', or 'No PDF found').
    """
    filename = "_".join(title.split()) + ".pdf"
    output_path = os.path.join(output_directory, filename)

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
                # Attempt alternative download
                logger.info("Attempting alternative download method.")
                remark = find_and_download_pdf(title, output_path)
                return remark
            else:
                logger.info(f"Successfully downloaded: {output_path}")
                return "Success"
        else:
            logger.warning(f"Sci-Hub download failed for: {title}")
            # Attempt alternative download
            logger.info("Attempting alternative download method.")
            remark = find_and_download_pdf(title, output_path)
            return remark
    except Exception as e:
        logger.error(f"Error during Sci-Hub download for '{title}': {e}")
        # Attempt alternative download
        logger.info("Attempting alternative download method.")
        remark = find_and_download_pdf(title, output_path)
        return remark


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
    df = df[df['ai_output'] == 'Related']
    df['pdf_scihub'] = ''
    df=df[6:8]
    for _, row in tqdm(df.iterrows(), total=len(df), desc="Processing papers"):
        title = row['title']
        download_status = download_paper(title, output_directory)
        df.loc[df['title'] == title, 'pdf_scihub'] = download_status

    return df

if __name__ == "__main__":
    # Configuration
    csv_path = r'../research_filter/corono_discharge_updated_20241130_231804_X.xlsx'
    pdf_store_directory = r'C:\Users\balan\IdeaProjects\academic_paper_maker\research_filter\pdf_store'

    # Create output directory
    create_pdf_store(pdf_store_directory)

    # Process the DataFrame and update download status
    logger.info("Starting the download process...")
    updated_df = process_dataframe(csv_path, pdf_store_directory)

    # Save the updated DataFrame
    output_csv_path = 'updated_corono_discharge_downloaded_status.xlsx'
    updated_df.to_excel(output_csv_path, index=False)
    logger.info(f"Updated DataFrame saved to {output_csv_path}")
