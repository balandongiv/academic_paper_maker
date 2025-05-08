import json
import logging
import os
import time

import pandas as pd
from dotenv import load_dotenv
from tqdm import tqdm

from research_filter.agent_helper import (
    get_info_ai, setup_ai_model,
    get_source_text
)
from research_filter.agent_helper import parse_ai_output, create_folder_if_not_exists, load_config_file, \
    get_role_instruction
from research_filter.helper import (
    save_result_to_json,
    update_df_from_json,
    cleanup_json_files,
    extract_pdf_text,
)
from research_filter.iterative_llm import run_iterative_confirmation
from setting.project_path import project_folder

# --------------------------------------------------------------------------------
# Logger Setup
# --------------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)




logger = logging.getLogger(__name__)

def process_main_agent_row_single_run(
        row: pd.Series,
        main_folder: str,
        output_folder: str,
        role_instruction: str,
        client,
        model_name: str,
        column_name: str,
        process_setup: dict,
) -> None:
    """
    Process a single row with the main agent (ONE run):
    1. Checks whether a JSON file already exists. If yes, skip.
    2. Extract text from PDF (or abstract if PDF unavailable).
    3. Call the AI agent to get the response.
    4. Parse AI output and handle errors.
    5. Save result to a JSON file in output_folder.
    """

    bibtex_val = row.get('bibtex')
    json_path = os.path.join(output_folder, f"{bibtex_val}.json")
    json_path_issue = os.path.join(output_folder, "issue", f"{bibtex_val}.json")

    # Skip processing if output already exists
    if os.path.exists(json_path):
        logger.info(f"Already processed: {bibtex_val}, saved at {json_path}")
        return
    if os.path.exists(json_path_issue):
        logger.info(f"Already processed: {bibtex_val}, saved at {json_path_issue}")
        return

    # Extract source text
    source_text, status_text, bibtex_val, json_path = get_source_text(row, main_folder, output_folder, process_setup)

    if status_text:
        logger.info(f"Processing {bibtex_val} with AI agent {model_name}.")

        # Call AI agent for response
        ai_output = get_info_ai(
            bibtex_val,
            source_text,
            role_instruction,
            client
        )

        # Parse AI output
        parsed_data, status_parsing = parse_ai_output(ai_output, column_name, model_name)
        if status_parsing is False or parsed_data is None:
            status_text= False
            json_path = json_path_issue
            # Attempt to extract JSON content between markers.

            parsed_data = {
                column_name: {
                    "error_msg": f"not able to parse {source_text}",
                    "system_message":role_instruction,
                    "user_message":source_text
                }
            }
    else:
        parsed_data = {
            column_name: {
                "error_msg": f"Error extracting text: {source_text}"
            }
        }
        json_path = json_path_issue
        status_text= False

    # Save results based on status
    if status_text is False or status_parsing is False:
        logger.warning(f"Issue encountered, saving {bibtex_val} at {json_path_issue}")
        save_result_to_json(bibtex_val, parsed_data, json_path_issue, column_name)
    elif status_parsing is True and status_text is True:
        logger.info(f"Successfully processed {bibtex_val}, saving at {json_path}")
        save_result_to_json(bibtex_val, parsed_data, json_path, column_name)
    else:
        logger.info(f"Successfully processed {bibtex_val}, saving at {json_path}")
        save_result_to_json(bibtex_val, parsed_data, json_path, column_name)


# --------------------------------------------------------------------------------
# Multi-Run Main Agent (when cross_check_enabled = True)
# --------------------------------------------------------------------------------
def process_main_agent_row_multi_runs(
        row: pd.Series,
        main_folder: str,
        output_folder: str,
        role_instruction: str,
        client,
        model_name: str,
        column_name: str,
        cross_check_runs: int
) -> None:
    """
    Process a single row with the main agent, but repeated cross_check_runs times:
    1. For each run (0..cross_check_runs-1), we create a JSON file named {bibtex_val}_run_{i}.json
    2. We do NOT combine them here. We only store them for future cross-check usage.
    """
    pdf_filename = row.get('pdf_name', '')
    bibtex_val = row.get('bibtex', None)
    if not pdf_filename or pd.isna(bibtex_val):
        return

    pdf_path = os.path.join(main_folder, pdf_filename)
    if pdf_filename == 'no_pdf':
        # Fallback to 'abstract' column if no PDF
        pdf_text = row.get('abstract', None)
        # pdf_text=''
        status = True
    elif pdf_filename and os.path.exists(pdf_path):
        pdf_text, status = extract_pdf_text(pdf_path)
    else:
        # If PDF path is invalid or missing, skip
        return

    if not status:
        # If text extraction was not successful, skip
        return

    for run_idx in range(cross_check_runs):
        # Build path for the partial JSON
        json_path = os.path.join(output_folder, f"{bibtex_val}_run_{run_idx}.json")

        # If it already exists, skip
        if os.path.exists(json_path):
            continue

        ai_output = get_info_ai(
            bibtex_val,
            pdf_text,
            role_instruction,
            client
        )
        parsed_data  = parse_ai_output(ai_output, column_name)
        # parsed_data=ai_output

        save_result_to_json(bibtex_val, parsed_data, json_path, column_name)


def combine_multi_runs_for_bibtex(bibtex_val: str, folder: str) -> dict:
    """
    Collect all multi-run JSON files for a single bibtex from the given folder
    and combine them into a single Python dictionary.
    Example filenames: {bibtex_val}_run_0.json, {bibtex_val}_run_1.json
    """
    combined_data = {}
    for filename in os.listdir(folder):
        # Check for matching bibtex_val and suffix "_run_*.json"
        if filename.startswith(bibtex_val) and "_run_" in filename and filename.endswith(".json"):
            file_path = os.path.join(folder, filename)
            run_key = filename.rsplit(".json", 1)[0]  # e.g., "bibtex_run_0"
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except json.JSONDecodeError:
                data = {"error": "Failed to parse JSON"}
            combined_data[run_key] = data
    return combined_data


# --------------------------------------------------------------------------------
# Cross-Check Agent to finalize combined data
# --------------------------------------------------------------------------------
def finalize_cross_check_output(
        df: pd.DataFrame,
        source_folder: str,
        final_folder: str,
        cross_check_agent_name: str,
        role_instruction: str,
        client,
        model_name: str,
        column_name: str
) -> pd.DataFrame:
    """
    1. For each row in the DataFrame, load its multi-run JSON files from source_folder.
    2. Combine them into a single JSON-like dict, call the cross_check_agent.
    3. Save the final single-run JSON in final_folder, named {bibtex_val}.json
    4. Update DF from final_folder.
    """
    if not os.path.exists(final_folder):
        os.makedirs(final_folder)

    for idx, row in df.iterrows():
        bibtex_val = row.get("bibtex", None)
        if not bibtex_val or pd.isna(bibtex_val):
            continue

        # Combine multiple runs
        combined_data = combine_multi_runs_for_bibtex(bibtex_val, source_folder)
        final_json_path = os.path.join(final_folder, f"{bibtex_val}.json")
        if not combined_data:
            continue  # skip if no partial results
        if os.path.exists(final_json_path):
            print("Already processed", final_json_path)
            continue
        # Convert combined data to a JSON string
        combined_str = json.dumps(combined_data, indent=2)
        ai_output = get_info_ai(
            bibtex_val,
            combined_str,
            role_instruction,
            client
        )
        parsed_data  = parse_ai_output(ai_output, column_name)

        with open(final_json_path, 'w', encoding='utf-8') as f:
            json.dump(parsed_data, f, indent=4)

    # Finally, update the DF from final_folder
    updated_df = update_df_from_json(df, final_folder, column_name)
    return updated_df

def process_single_run(df: pd.DataFrame,
                       main_folder: str,
                       methodology_json_folder: str,
                       role_instruction: str,
                       client,
                       model_name: str,
                       column_name: str,
                       process_setup: dict) -> pd.DataFrame:
    """Process each row once with the main agent and update the DF."""
    # Ensure main output folder exists
    os.makedirs(methodology_json_folder, exist_ok=True)
    os.makedirs(os.path.join(methodology_json_folder, 'issue'), exist_ok=True)

    for _, row in tqdm(df.iterrows(), total=len(df), leave=False):
        process_main_agent_row_single_run(
            row,
            main_folder,
            methodology_json_folder,
            role_instruction,
            client,
            model_name,
            column_name,
            process_setup
        )

    return update_df_from_json(df, methodology_json_folder, column_name)


def process_iterative_confirmation_branch(df: pd.DataFrame,
                                          main_folder: str,
                                          methodology_json_folder: str,
                                          model_name: str,
                                          role_instruction: str,
                                          client,
                                          column_name: str,
                                          config: dict,
                                          process_setup: dict) -> pd.DataFrame:
    """Kick off the iterative confirmation approach."""
    expected_output = config['methodology_gap_extractor']['expected_output']
    iterative_agent = config['iterative_validation']
    run_iterative_confirmation(
        df,
        main_folder,
        methodology_json_folder,
        model_name,
        role_instruction,
        client,
        column_name,
        expected_output,
        iterative_agent
    )



def process_manual_paste_llm(df: pd.DataFrame,
                             main_folder: str,
                             deepseek_json_folder: str,
                             role_instruction: str) -> pd.DataFrame:
    """Prepare JSON files for manual paste into the LLM playground."""
    os.makedirs(deepseek_json_folder, exist_ok=True)

    for _, row in tqdm(df.iterrows(), total=len(df), leave=False):
        source_text, status, bibtex_val, json_path = get_source_text(
            row, main_folder, deepseek_json_folder
        )
        if os.path.exists(json_path):
            continue

        task = {
            "messages": [
                {"role": "system", "content": role_instruction},
                {"role": "user",   "content": source_text}
            ]
        }
        with open(json_path, 'w', encoding='utf-8') as file:
            json.dump(task, file, ensure_ascii=False, indent=4)


def process_batch_process(df: pd.DataFrame,
                          main_folder: str,
                          methodology_json_folder: str,
                          role_instruction: str,
                          model_name: str) -> pd.DataFrame:
    """Build a tasks.jsonl file for OpenAI batch processing."""
    os.makedirs(methodology_json_folder, exist_ok=True)
    tasks = []

    for _, row in tqdm(df.iterrows(), total=len(df), leave=False):
        source_text, status, bibtex_val, _ = get_source_text(
            row, main_folder, methodology_json_folder
        )
        if not status:
            continue

        task = {
            "custom_id": f"task-{bibtex_val}",
            "method": "POST",
            "url": "/v1/chat/completions",
            "body": {
                "model": model_name,
                "temperature": 0.1,
                "response_format": {"type": "json_object"},
                "messages": [
                    {"role": "system", "content": role_instruction},
                    {"role": "user",   "content": source_text}
                ],
            }
        }
        tasks.append(task)

    file_name = os.path.join(methodology_json_folder, "tasks.jsonl")
    with open(file_name, 'w') as f:
        for obj in tasks:
            f.write(json.dumps(obj) + "\n")


def process_multi_run_cross_check(df: pd.DataFrame,
                                  main_folder: str,
                                  methodology_json_folder: str,
                                  multiple_runs_folder: str,
                                  final_cross_check_folder: str,
                                  role_instruction_main: str,
                                  role_instruction_cross: str,
                                  client,
                                  model_name: str,
                                  column_name: str,
                                  process_setup: dict) -> pd.DataFrame:
    """Run the multi-run + cross-check logic and return the updated DF."""
    # ensure folders
    create_folder_if_not_exists(multiple_runs_folder)
    create_folder_if_not_exists(final_cross_check_folder)

    # Step 1: partial runs
    non_nan_df = df[
        (df['year_relavency'] == 'yes') &
        (df['review_paper'] != 'yes') &
        (df['experimental'].isna()) &
        (df['pdf_name'].notna()) &
        (df['pdf_name'] != "no_pdf")
        ]
    # you can parameterize head(n) if you want
    for _, row in tqdm(non_nan_df.iterrows(), total=len(non_nan_df)):
        process_main_agent_row_multi_runs(
            row,
            main_folder,
            multiple_runs_folder,
            role_instruction_main,
            client,
            model_name,
            column_name,
            process_setup['cross_check_runs']
        )

    # Step 2: combine + cross-check
    updated_df = finalize_cross_check_output(
        non_nan_df,
        multiple_runs_folder,
        final_cross_check_folder,
        process_setup['cross_check_agent_name'],
        role_instruction_cross,
        client,
        model_name,
        column_name
    )
    return updated_df
# --------------------------------------------------------------------------------
# Main Pipeline
# --------------------------------------------------------------------------------
def run_pipeline(
        agentic_setting ,process_setup,
        placeholders: dict,
        csv_path: str,
        main_folder: str,
        methodology_json_folder: str,
        multiple_runs_folder: str = None,
        final_cross_check_folder: str = None,
):
    """
    Orchestrate the entire flow:

    LOGIC OVERVIEW:
    1) Load config, role instructions, client
    2) Load Excel DataFrame
    3) If cross_check_enabled == False:
         - Run main agent ONCE per row, store JSON in methodology_json_folder
         - Update DataFrame from JSON
       If cross_check_enabled == True:
         - Run main agent cross_check_runs times per row, store JSON in multiple_runs_folder
         - Combine partial outputs and run cross-check agent once per row => final_cross_check_folder
         - Update DataFrame from final_cross_check_folder
    4) Optionally cleanup
    5) Save updated DataFrame
    """
    start_time = time.time()
    logger.info("Pipeline execution started.")

    # Load env & config
    load_dotenv()
    config = load_config_file(agentic_setting['yaml_path'])
    model_name = agentic_setting['model_name']
    column_name = agentic_setting['column_name']
    # Prepare role instructions
    logger.info(f"Preparing role instructions for {agentic_setting['agent_name']}.")
    role_instruction_main = get_role_instruction(config, placeholders, agentic_setting['agent_name'])

    if process_setup['cross_check_enabled']:
        #  - The cross-check agent's role
        role_instruction_cross_check = get_role_instruction(config, placeholders, process_setup['cross_check_agent_name'])
    else:
        role_instruction_cross_check = None

    client = setup_ai_model(model_name=model_name)

    # Load DataFrame from Excel
    logger.info(f"Loading DataFrame from {csv_path}")
    df = pd.read_excel(csv_path)


    if not process_setup['cross_check_enabled']:
        df = process_single_run(
            df, main_folder, methodology_json_folder,
            role_instruction_main, client,
            model_name, column_name, process_setup
        )

    elif process_setup['iterative_confirmation']:

        logger.info("→ Iterative confirmation branch")
        process_iterative_confirmation_branch(
            df, main_folder, methodology_json_folder,
            model_name, role_instruction_main,
            client, column_name, config, process_setup
        )

    elif process_setup['manual_paste_llm']:

        logger.info("→ Manual-paste-LLM branch")
        deepseek_folder = os.path.join(methodology_json_folder, 'deepseek')
        process_manual_paste_llm(
            df, main_folder, deepseek_folder, role_instruction_main
        )

    elif process_setup['batch_process']:
        logger.info("→ Batch-process branch")
        process_batch_process(
            df, main_folder, methodology_json_folder,
            role_instruction_main, model_name
        )

    else:

        logger.info("→ Multi-run + cross-check branch")
        if not multiple_runs_folder or not final_cross_check_folder:
            raise ValueError(
                "When cross_check_enabled is True, you must provide "
                "multiple_runs_folder and final_cross_check_folder."
            )
        role_instruction_cross='im not sure what is role_instruction_cross'
        df = process_multi_run_cross_check(
            df, main_folder, methodology_json_folder,
            multiple_runs_folder, final_cross_check_folder,
            role_instruction_main, role_instruction_cross,
            client, model_name, column_name, process_setup
        )


    # Cleanup if needed
    if process_setup['cleanup_json']:
        if not process_setup['cross_check_enabled']:
            logger.info("Cleanup: removing JSON files in methodology_json_folder.")
            cleanup_json_files(df, methodology_json_folder)
        else:
            logger.info("Cleanup: removing partial JSON files in multiple_runs_folder.")
            # These partials can help resume if something fails, but if you want them removed, do:
            cleanup_json_files(df, multiple_runs_folder)
            # Also remove final JSON if needed:
            # cleanup_json_files(df, final_cross_check_folder)

        # (Optional) Save final DF to Excel

    if process_setup['overwrite_csv']:
        logger.info(f"Saving updated DataFrame to {csv_path}")
        df.to_excel(csv_path, index=False)

    logger.info(f"Pipeline execution complete in {time.time() - start_time:.2f} s.")


# --------------------------------------------------------------------------------
# Main Function
# --------------------------------------------------------------------------------
def main():
    """
    We keep in main() only the parameters that are likely to change frequently.
    """


    # project_review='eeg_review'
    project_review='corona_discharge'
    path_dic=project_folder(project_review=project_review)
    main_folder = path_dic['main_folder']

    # Editable variables
    # model_name = "gpt-4o"  # or "gpt-4o"
    # model_name="gpt-4o-mini"
    # model_name="gpt-o3-mini"
    # model_name='gemini-1.5-pro'

    # model_name='gemini-exp-1206'
    model_name='gemini-2.0-flash-thinking-exp-01-21'


    # agentic_setting = {
    #     "agent_name": "abstract_wafer_abstract_filter",
    #     "column_name": "abstract_wafer_abstract_filter",
    #     "yaml_path": "agent/agent_ml.yaml",
    #     "model_name": model_name
    # }
    agent_name="methodology_gap_extractor_partial_discharge"
    agentic_setting = {
        "agent_name": agent_name,
        "column_name": agent_name,
        "yaml_path": "agent/agent_ml.yaml",
        "model_name": model_name
    }

    methodology_json_folder=os.path.join(main_folder,agentic_setting['agent_name'],'json_output')
    multiple_runs_folder =os.path.join(main_folder,agentic_setting['agent_name'],'multiple_runs_folder')
    final_cross_check_folder = os.path.join(main_folder,agentic_setting['agent_name'],'final_cross_check_folder')

    csv_path = path_dic['csv_path']
    # Basic placeholders for roles
    placeholders = {
        "topic": "EEG-based fatigue classification",
        "topic_context": "neurophysiological analysis"
    }


    process_setup={
        'batch_process':False,  # This is for the batch processing which have 50% discount. use with the code research_filter/check_batch_process.py
        'manual_paste_llm':False,       # This is for the manual paste of the LLM
        'iterative_confirmation':False,
        'overwrite_csv':False,      # careful when set to true as this will overwrite the csv file
        'cross_check_enabled':False,
        'cross_check_runs':3,
        'cross_check_agent_name':'agent_cross_check',
        'cleanup_json':False,
        'used_abstract':True    # when working with pdf, always set this option to True, so that we use the abstract on behlaf of the pdf
    }

    # Run pipeline
    run_pipeline(
        agentic_setting ,process_setup,
        placeholders=placeholders,
        csv_path=csv_path,
        main_folder=main_folder,
        methodology_json_folder=methodology_json_folder,
        multiple_runs_folder=multiple_runs_folder,
        final_cross_check_folder=final_cross_check_folder,
    )


if __name__ == "__main__":
    main()
