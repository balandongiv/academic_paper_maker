import os
import shutil
import json
import pandas as pd

EXCEL_PATH = r'C:\Users\balan\IdeaProjects\academic_paper_maker\research_filter\database\eeg_review.xlsx'
PDF_FOLDER_MANUAL_DOWNLOAD = r'C:\Users\balan\OneDrive - ums.edu.my\research_related\0 eeg_trend_till24\eeg_review\manual_download'
PDF_FOLDER = r'C:\Users\balan\OneDrive - ums.edu.my\research_related\0 eeg_trend_till24\eeg_review'
JSON_FOLDER = r'C:\Users\balan\OneDrive - ums.edu.my\research_related\0 eeg_trend_till24\eeg_review'

def update_pdf_names_main_folder(df: pd.DataFrame, pdf_folder: str) -> pd.DataFrame:
    pdf_files = [f for f in os.listdir(pdf_folder) if f.lower().endswith('.pdf')]
    pdf_file_base_names = {os.path.splitext(pdf)[0]: pdf for pdf in pdf_files}

    for index, row in df.iterrows():
        if pd.notna(row['pdf_name']) and row['pdf_name'] in pdf_files:
            continue
        bibtex_value = str(row['bibtex'])
        matched_pdf = pdf_file_base_names.get(bibtex_value)
        if matched_pdf:
            df.at[index, 'pdf_name'] = matched_pdf
    return df

def load_excel(file_path: str) -> pd.DataFrame:
    df = pd.read_excel(file_path)
    if 'pdf_name' not in df.columns:
        df['pdf_name'] = None
    return df

def update_pdf_names_from_files(df: pd.DataFrame, pdf_folder: str, json_folder: str) -> pd.DataFrame:
    pdf_files = [f for f in os.listdir(pdf_folder) if f.lower().endswith('.pdf')]

    for index, row in df.iterrows():
        bibtex_value = str(row['bibtex']).strip()
        matched_pdf = next((pdf for pdf in pdf_files if bibtex_value in pdf), None)
        if matched_pdf:
            df.at[index, 'pdf_name'] = matched_pdf
            src_path = os.path.join(pdf_folder, matched_pdf)
            dest_path = os.path.join(json_folder, matched_pdf)
            try:
                shutil.move(src_path, dest_path)
                print(f"Moved PDF file: {matched_pdf} to {json_folder}")
            except Exception as e:
                print(f"Error moving file {matched_pdf}: {e}")
            pdf_files.remove(matched_pdf)
    return df

def update_pdf_names_from_json(df: pd.DataFrame, json_folder: str) -> pd.DataFrame:
    mapping = {}

    for filename in os.listdir(json_folder):
        if filename.endswith('.json'):
            identifier = os.path.splitext(filename)[0]
            json_path = os.path.join(json_folder, filename)

            try:
                with open(json_path, 'r', encoding='utf-8') as file:
                    data = json.load(file)
                actual_pdf_name = data.get('expected_pdf_name')
                status = data.get('status')

                if actual_pdf_name and status == 'success':
                    mapping[identifier] = actual_pdf_name
                    os.remove(json_path)
                    print(f"Successfully updated and deleted JSON file: {filename}")
            except Exception as e:
                print(f"Error processing file {filename}: {e}")

    df['pdf_name'] = df.apply(
        lambda row: mapping.get(row['bibtex'], row['pdf_name']), axis=1
    )

    return df

def combine_with_unprocessed_rows(original_df: pd.DataFrame, updated_df: pd.DataFrame) -> pd.DataFrame:
    """
    Combines the original rows that were not updated with the updated rows.
    """
    unprocessed_rows = original_df[~original_df.index.isin(updated_df.index)]
    combined_df = pd.concat([updated_df, unprocessed_rows], ignore_index=True)
    return combined_df

def save_updated_excel(df: pd.DataFrame, output_path: str) -> None:
    df.to_excel(output_path, index=False)
    print(f"Updated Excel file saved at: {output_path}")

def main() -> None:
    df_original = load_excel(EXCEL_PATH)
    df_updated = update_pdf_names_main_folder(df_original.copy(), PDF_FOLDER)
    df_updated = update_pdf_names_from_json(df_updated, JSON_FOLDER)
    final_df = combine_with_unprocessed_rows(df_original, df_updated)

    # updated_excel_path = os.path.splitext(EXCEL_PATH)[0] + "_updatedx.xlsx"
    save_updated_excel(final_df, EXCEL_PATH)

if __name__ == "__main__":
    main()
