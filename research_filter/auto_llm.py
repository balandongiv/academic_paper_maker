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
    load_partial_results_from_json,
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

expected_json_output ={
    "introduction": {
        "problem_statement": "string",
        "proposed_solution": "explanation about the proposed solution",
        "gap_in_previous_study": "long discussion about the technical gap identified in previous studies",
        "issue_being_addressed": "choose either one of the four following themes: 1. Tackling Subject Variability, 2. Reducing the Number of EEG Channels, 3. Multiclass Sleepiness Classification, 4. Enhancing Robustness and Generalization",
        "justification": "long explanation on why you choose the theme in the issue_being_addressed"
    },
    "methodology": {
        "methods_used": [
            "<Method 1>",
            "<Method 2>",
            "<list of other methods if available>"
        ],
        "exact_reasons_for_selection": {
            "<Method 1>": "multiple lines of the exact text from the input about the reason or motivation to use Method 1.",
            "<Method 2>": "multiple lines of the exact text from the input about the reason or motivation to use Method 2",
            "<list of other methods if available>": ""
        },
        "reasons_for_selection": {
            "<Method 1>": "Long and detailed explanation about the reason or motivation to use Method 1.",
            "<Method 2>": "Long and detailed explanation about the reason or motivation to use Method 2.",
            "<list of other methods if available>": ""
        },
        "performance_metrics": {
            "accuracy": "<Value or 'N/A'>",
            "precision": "<Value or 'N/A'>",
            "recall": "<Value or 'N/A'>",
            "f1_score": "<Value or 'N/A'>",
            "other_metrics": {
                "<Metric name>": "<Value>"
            }
        },
        "comparison_with_existing_methods": {
            "key_differences": "A long detailed comparison with other machine learning or state-of-the-art (SOTA) techniques, including their names, highlighting improvements, innovations, or weaknesses. If there is value associated, give"
        }
    },
    "discussion": {
        "limitations_and_future_work": {
            "current_limitations": [
                "list of limitation of the proposed study"
            ],
            "future_directions": [
                "list of future direction that you can think"
            ]
        }
    }
}

def process_main_agent_row_single_run(
        row: pd.Series,
        main_folder: str,
        output_folder: str,
        role_instruction: str,
        client,
        model_name: str,
        column_name: str
) -> None:
    """
    Process a single row with the main agent (ONE run):
    1. Checks whether a JSON file already exists. If yes, skip.
    2. Extract text from PDF (or abstract if PDF unavailable).
    3. Call the AI agent to get the response.
    4. Save result to a JSON file in output_folder.
    """

    source_text,status,bibtex_val,json_path=get_source_text(row,main_folder, output_folder)
    # If text extraction was successful
    if status:
        logger.info(f"Processing {bibtex_val} with AI agent {model_name}.")
        ai_output = get_info_ai(
            bibtex_val,
            source_text,
            role_instruction,
            client
        )
        parsed_data  = parse_ai_output(ai_output, column_name,model_name)



    else:
        parsed_data = {
            column_name: {
                "error_msg": f"error text {source_text}"
            }
        }

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


# --------------------------------------------------------------------------------
# Main Pipeline
# --------------------------------------------------------------------------------
def run_pipeline(
        placeholders: dict,
        model_name: str,
        csv_path: str,
        agent_name: str,
        column_name: str,
        yaml_path: str,
        main_folder: str,
        # Single-run output (if cross_check_enabled=False)
        methodology_json_folder: str,
        # Cross-check related
        cross_check_enabled: bool = False,
        cross_check_runs: int = 3,
        cross_check_agent_name: str = "agent_cross_check",
        multiple_runs_folder: str = None,
        final_cross_check_folder: str = None,
        # Cleanup
        cleanup_json: bool = False
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
    config = load_config_file(yaml_path)
    # gg=config['methodology_gap_extractor']['expected_output']
    # Prepare role instructions
    #  - The main agent's role
    role_instruction_main = get_role_instruction(config, placeholders, agent_name)

    if cross_check_enabled:
        #  - The cross-check agent's role
        role_instruction_cross_check = get_role_instruction(config, placeholders, cross_check_agent_name)
    else:
        role_instruction_cross_check = None

    client = setup_ai_model(model_name=model_name)

    # Load DataFrame from Excel
    logger.info(f"Loading DataFrame from {csv_path}")
    df = pd.read_excel(csv_path)
    df=df.head(10)
    batch_process=True
    deepseek=False
    iterative_confirmation=True

    if not cross_check_enabled and not batch_process:
        # Ensure main output folder exists
        create_folder_if_not_exists(methodology_json_folder)

        # Update DF from any existing JSON (previous partial runs)
        df = load_partial_results_from_json(df, methodology_json_folder)

        # Process each row with main agent once
        logger.info("Processing each row with main agent (SINGLE-RUN).")



        non_nan_df=df       # at this stage, im not filtering the rows
        for _, row in tqdm(non_nan_df.iterrows(), total=len(non_nan_df), leave=False):
            process_main_agent_row_single_run(
                row,
                main_folder,
                methodology_json_folder,
                role_instruction_main,
                client,
                model_name,
                column_name
            )

        # Update DF from final single-run JSON
        df = update_df_from_json(df, methodology_json_folder, column_name)

    elif iterative_confirmation:
        # yaml_file_path = r"C:\Users\balan\IdeaProjects\academic_paper_maker\research_filter\agent\cross_check.yaml"
        expected_json_output=config['methodology_gap_extractor']['expected_output']
        iterative_agent=config['iterative_validation']
        run_iterative_confirmation(
            df,
            main_folder,
            methodology_json_folder,
            model_name,
            role_instruction_main,
            client,
            column_name,
            expected_json_output,
            # yaml_file_path,
            iterative_agent
        )


    elif deepseek:
        '''
        In this approach, we process each row individually and save the JSON files in the deepseek folder.
        '''
        non_nan_df=df
        # Ensure the deepseek folder is set up outside the loop
        deepseek_json_folder = os.path.join(methodology_json_folder, 'deepseek')
        os.makedirs(deepseek_json_folder, exist_ok=True)
        for index, row in tqdm(non_nan_df.iterrows(), total=len(non_nan_df), leave=False):

            source_text,status,bibtex_val,json_path=get_source_text(row, main_folder, deepseek_json_folder)

            if os.path.exists(json_path):
                continue
            task = {"messages": [
                {
                    "role": "system",
                    "content": role_instruction_main
                },
                {
                    "role": "user",
                    "content": source_text
                }
            ]}


            # Save the task dictionary as a JSON file with pretty-printing
            with open(json_path, 'w', encoding='utf-8') as file:
                json.dump(task, file, ensure_ascii=False, indent=4)

    elif batch_process:
        tasks = []
        # https://cookbook.openai.com/examples/batch_processing
        non_nan_df=df       # at this stage, im not filtering the rows


        for index, row in tqdm(non_nan_df.iterrows(), total=len(non_nan_df), leave=False):

            source_text,status,bibtex_val,json_path=get_source_text(row, main_folder, methodology_json_folder)

            if status is False:
                continue
            task = {
                "custom_id": f"task-{bibtex_val}",
                "method": "POST",
                "url": "/v1/chat/completions",
                "body": {
                    # This is what you would have in your Chat Completions API call
                    "model": model_name,
                    "temperature": 0.1,
                    "response_format": {
                        "type": "json_object"
                    },
                    "messages": [
                        {
                            "role": "system",
                            "content": role_instruction_main
                        },
                        {
                            "role": "user",
                            "content": source_text
                        }
                    ],
                }
            }
            tasks.append(task)
        os.makedirs(methodology_json_folder, exist_ok=True)
        file_name = os.path.join(methodology_json_folder, "tasks.jsonl")

        with open(file_name, 'w') as file:
            for obj in tasks:
                file.write(json.dumps(obj) + '\n')


    else:
        # If cross_check_enabled is True, do multi-run approach
        if not multiple_runs_folder or not final_cross_check_folder:
            raise ValueError("When cross_check_enabled is True, you must provide multiple_runs_folder and final_cross_check_folder.")

        # Ensure these folders exist
        create_folder_if_not_exists(multiple_runs_folder)
        create_folder_if_not_exists(final_cross_check_folder)

        # No partial runs to load for multi-run scenario, or you could do so if desired:
        # df = load_partial_results_from_json(df, multiple_runs_folder)

        # Step 1: Run main agent cross_check_runs times for each row
        logger.info(f"Processing each row with main agent MULTI-RUNS = {cross_check_runs}")
        # non_nan_df = df[~df['pdf_name'].isna()]
        # non_nan_df=non_nan_df.head(10)

        non_nan_df = df[
            (df['year_relavency'] == 'yes') &
            (df['review_paper'] != 'yes') &
            (df['experimental'].isna()) &
            (df['pdf_name'].notna()) &
            (df['pdf_name'] != "no_pdf")
            ]
        non_nan_df=non_nan_df.head(2)
        for _, row in tqdm(non_nan_df.iterrows(), total=len(non_nan_df)):
            process_main_agent_row_multi_runs(
                row,
                main_folder,
                multiple_runs_folder,
                role_instruction_main,
                client,
                model_name,
                column_name,
                cross_check_runs
            )

        # Step 2: Combine partial outputs & run cross-check agent
        logger.info("Combining partial outputs and finalizing with cross-check agent.")
        df = finalize_cross_check_output(
            non_nan_df,
            multiple_runs_folder,
            final_cross_check_folder,
            cross_check_agent_name,
            role_instruction_cross_check,
            client,
            model_name,
            column_name
        )

    # Cleanup if needed
    if cleanup_json:
        if not cross_check_enabled:
            logger.info("Cleanup: removing JSON files in methodology_json_folder.")
            cleanup_json_files(df, methodology_json_folder)
        else:
            logger.info("Cleanup: removing partial JSON files in multiple_runs_folder.")
            # These partials can help resume if something fails, but if you want them removed, do:
            cleanup_json_files(df, multiple_runs_folder)
            # Also remove final JSON if needed:
            # cleanup_json_files(df, final_cross_check_folder)

        # (Optional) Save final DF to Excel
        # logger.info(f"Saving updated DataFrame to {csv_path}")
        # df.to_excel(csv_path, index=False)

    logger.info(f"Pipeline execution complete in {time.time() - start_time:.2f} s.")


# --------------------------------------------------------------------------------
# Main Function
# --------------------------------------------------------------------------------
def main():
    """
    We keep in main() only the parameters that are likely to change frequently.
    """


    # project_review='eeg_review'
    project_review='eeg_review'
    path_dic=project_folder(project_review=project_review)
    main_folder = path_dic['main_folder']

    agent_name = "methodology_gap_extractor"
    column_name = "methodology_gap_extractor"
    yaml_path = "agent/agent_ml.yaml"


    methodology_json_folder=os.path.join(main_folder,agent_name,'json_output')
    multiple_runs_folder =os.path.join(main_folder,agent_name,'multiple_runs_folder')
    final_cross_check_folder = os.path.join(main_folder,agent_name,'final_cross_check_folder')

    csv_path = path_dic['csv_path']
    # Basic placeholders for roles
    placeholders = {
        "topic": "EEG-based fatigue classification",
        "topic_context": "neurophysiological analysis"
    }

    # Editable variables
    # model_name = "gpt-4o"  # or "gpt-4o"
    # model_name="gpt-4o-mini"
    # model_name="gpt-o3-mini"
    # model_name='gemini-1.5-pro'

    model_name='gemini-exp-1206'


    # Single-run


    # Cross-check logic

    cross_check_enabled = False
    cross_check_runs = 3
    cross_check_agent_name = "agent_cross_check"
    cleanup_json = False

    # Run pipeline
    run_pipeline(
        placeholders=placeholders,
        model_name=model_name,
        csv_path=csv_path,
        agent_name=agent_name,
        column_name=column_name,
        yaml_path=yaml_path,
        main_folder=main_folder,
        methodology_json_folder=methodology_json_folder,
        cross_check_enabled=cross_check_enabled,
        cross_check_runs=cross_check_runs,
        cross_check_agent_name=cross_check_agent_name,
        multiple_runs_folder=multiple_runs_folder,
        final_cross_check_folder=final_cross_check_folder,
        cleanup_json=cleanup_json
    )


if __name__ == "__main__":
    main()
