import json
import json
import logging
import os

from tqdm import tqdm

from research_filter.agent_helper import (
    get_info_ai, get_source_text
)
from research_filter.agent_helper import parse_ai_output, load_config_file

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)
def load_iterative_agent(yaml_file_path):
    """
    Loads the YAML data from a file and returns it as a list of instructions.
    :param yaml_file_path: str, path to the YAML file
    :param load_config_file: function that loads the YAML
    :return: list of instructions (strings) or objects
    """
    yaml_data = load_config_file(yaml_file_path)
    # Convert dictionary to a list if needed
    if isinstance(yaml_data, dict):
        # If your YAML looks like:
        #   step1: "Instruction 1"
        #   step2: "Instruction 2"
        # ...this extracts the values into a list
        iterative_agent = [value for key, value in yaml_data.items()]
    elif isinstance(yaml_data, list):
        # Already a list of instructions
        iterative_agent = yaml_data
    else:
        # Fallback, wrap in a list
        iterative_agent = [yaml_data]
    return iterative_agent


def iterative_refinement(bibtex_val,
                         source_text,
                         role_instruction_main,
                         iterative_agent,
                         client,
                         column_name,
                         model_name,
                         expected_json_output,
                         ):
    """
    Orchestrates the multi-step iterative calls to the AI and returns the final parsed output.

    1) First call uses role_instruction_main.
    2) Subsequent calls use instructions from iterative_agent.
    3) Each call references the expected_json_output and the previous output.

    :param bibtex_val: str, bibtex reference
    :param source_text: str, the manuscript or text to process
    :param role_instruction_main: str, the initial instruction
    :param iterative_agent: list of instructions, loaded from YAML
    :param client: your AI client (OpenAI, etc.)
    :param column_name: str, relevant for parse_ai_output
    :param model_name: str, relevant for parse_ai_output
    :param expected_json_output: dict, describing the required JSON structure
    :param get_info_ai: function to call your AI model
    :param parse_ai_output: function to parse the AI response
    :return: dict, final parsed data after the last iteration
    """

    # 1) First iteration with role_instruction_main
    logger.info(f"Starting the processing the first instruction for {bibtex_val} ")
    ai_output = get_info_ai(bibtex_val, source_text, role_instruction_main, client)
    parsed_data = parse_ai_output(ai_output, column_name, model_name)

    # 2) For each subsequent instruction in iterative_agent
    for key_agent, instruction_me in iterative_agent.items():
        logger.info(f"Validating the output using {key_agent} for {bibtex_val} ")
        expected_output_str = json.dumps(expected_json_output, indent=2)
        previous_output_str = json.dumps(parsed_data, indent=2)

        # Build a single combined instruction
        combined_instruction = (
            f"{instruction_me}\n"
            f"The Expected Output: {expected_output_str}\n"
            f"The previous json is:\n{previous_output_str}\n\n"
            f"The manuscript is as follows:"
        )

        ai_output_second = get_info_ai(bibtex_val, source_text, combined_instruction, client)
        parsed_data = parse_ai_output(ai_output_second, column_name, model_name)

    return parsed_data


def run_iterative_confirmation(
        df,
        main_folder,
        methodology_json_folder,
        model_name,
        role_instruction_main,
        client,
        column_name,
        expected_json_output,
        iterative_agent,
):
    """
    Runs the entire iterative-confirmation process for each row in the dataframe.
    The final parsed data is saved to JSON for each row.

    :param df: pandas.DataFrame, your main dataframe
    :param main_folder: str, path to the main folder containing source texts
    :param methodology_json_folder: str, path to store generated JSON
    :param model_name: str, used in output file/folder naming
    :param role_instruction_main: str, the initial instruction for the AI
    :param client: AI client
    :param column_name: str, used in parse_ai_output
    :param expected_json_output: dict, describing the required JSON structure
    :param yaml_file_path: str, path to your .yaml file that holds iterative instructions
    :param load_config_file: function that loads a config (YAML, etc.)
    :param get_info_ai: function that queries your AI model
    :param parse_ai_output: function that parses AI responses
    """

    # 1) Load iterative instructions
    # iterative_agent = load_iterative_agent(yaml_file_path)

    # 2) Prepare the folder
    json_folder = os.path.join(methodology_json_folder, 'iterative', model_name)
    os.makedirs(json_folder, exist_ok=True)

    # 3) Iterate over dataframe rows
    # non_nan_df = df.dropna(subset=[column_name])  # or simply df if you're sure no nans
    for index, row in tqdm(df.iterrows(), total=len(df), leave=False):

        # Your existing function that returns
        # (source_text, status, bibtex_val, json_path)
        source_text, status, bibtex_val, json_path = get_source_text(
            row, main_folder, json_folder
        )

        if status is False:
            # skip this file as it might be already being procews
            continue
        # 4) Perform the iterative refinement
        final_parsed_data = iterative_refinement(
            bibtex_val=bibtex_val,
            source_text=source_text,
            role_instruction_main=role_instruction_main,
            iterative_agent=iterative_agent,
            client=client,
            column_name=column_name,
            model_name=model_name,
            expected_json_output=expected_json_output,
            # get_info_ai=get_info_ai,
            # parse_ai_output=parse_ai_output
        )

        # 5) Save the final output to JSON
        with open(json_path, 'w', encoding='utf-8') as file:
            json.dump(final_parsed_data, file, ensure_ascii=False, indent=4)
