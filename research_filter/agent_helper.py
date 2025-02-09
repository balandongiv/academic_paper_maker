import json
import logging
import os
import re
from typing import Any, Dict, Union
from collections import OrderedDict
import yaml
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import RootModel
import traceback
from research_filter.helper import (
    generate_new_filename
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)
from grobid_tei_xml.xml_json import process_xml_file  # Update the module name if needed

def compile_path(path: str) -> str:
    """Return an absolute path by joining current working directory with given path."""
    return os.path.join(os.getcwd(), path)


def load_config_file(yaml_path: str) -> dict:
    """Load YAML configuration file and return as a dictionary."""
    logger.info(f"Loading YAML configuration from {yaml_path}.")
    return load_yaml(yaml_path)


def generate_output_xlsx_path(csv_path: str) -> str:
    """Generate a new filename based on the csv_path and return the XLSX output path."""
    new_filename = generate_new_filename(csv_path)
    return f"../research_filter/{new_filename}.xlsx"


def create_folder_if_not_exists(folder_path: str) -> None:
    """Create the folder if it does not exist."""
    if not os.path.exists(folder_path):
        os.makedirs(folder_path,exist_ok=True)


def get_role_instruction(config: dict, placeholders: dict, agent_name: str) -> str:
    """Combine role instructions from config based on placeholders and agent name."""
    logger.info(f"Combining role instruction for agent: {agent_name}.")
    return combine_role_instruction(config, placeholders, agent_name)



# Pydantic model for validation using RootModel
class AIOutputModel(RootModel[Union[str, Dict[str, Any]]]):
    pass




def parse_ai_output(ai_output, column_name,model_name):



    status=True
    if isinstance(ai_output, dict):
        # If ai_output is already a dictionary, no need to parse it
        parsed_data = ai_output
    else:
        try:
            # Check for simple JSON-like literals manually (e.g., 'True', 'False', 'null')
            if ai_output in ('True', 'False'):
                parsed_data = {
                    column_name: ai_output
                }

                # parsed_data = json.loads(ai_output.lower())
                return parsed_data,status
            else:
                # Attempt to parse ai_output if it's a JSON string
                parsed_data=extract_json_between_markers(ai_output)
                # parsed_data = json.loads(ai_output)
        except json.JSONDecodeError:
            # Handle JSON decoding errors gracefully
            status=False
            parsed_data = {
                column_name: {
                    "error_msg": f"Error parsing JSON: {ai_output}"
                }
            }
        except Exception as e:
            # Handle unexpected errors gracefully
            status=False
            parsed_data = {
                column_name: {
                    "error_msg": f"Unexpected error: {str(e)}"
                }
            }
    return parsed_data


def get_source_text(row, main_folder,output_folder,process_setup):
    """
    Extracts or processes text from a given source, handling PDF or XML files.

    Parameters:
        row (dict): A dictionary containing metadata, including 'pdf_name', 'bibtex', and 'abstract'.
        output_folder (str): Path where processed JSON files are stored.
        main_folder (str): Root directory containing source XML files.

    Returns:
        tuple: (str or None, bool, str or None, str) ->
               Extracted text (or None if not found),
               status (True if processed, False otherwise),
               bibtex_val (or None if missing),
               json_path (expected path for processed JSON output).
    """
    # use_abstract = process_setup['used_abstract']  # we only use abstract for filtering either the manuscript is suitable for futher processing or not

    pdf_filename = 'no_pdf' if process_setup['used_abstract']  else row.get('pdf_name', '')
    bibtex_val = row.get('bibtex')
    bibtex_data = {"bibtext": bibtex_val}
    if not bibtex_val:  # Ensure bibtex value exists
        logger.warning("Missing 'bibtex' value, skipping processing.")
        return None, False, None, ""

    json_path = os.path.join(output_folder, f"{bibtex_val}.json")

    # Check if JSON output already exists
    if os.path.exists(json_path):
        logger.info(f"Already processed: {json_path}")
        return None, False, bibtex_val, json_path  # No need to process again

    source_filename = f"{bibtex_val}.grobid.tei.xml"
    source_path = os.path.join(main_folder, "xml", source_filename)

    if pdf_filename == 'no_pdf':
        # Use abstract as fallback if no PDF
        source_text = row.get('abstract')
        if source_text:
            source_text = dict(bibtex_data, **{"abstract": source_text})
            logger.info(f"Using abstract text for {bibtex_val}.")
            return source_text, True, bibtex_val, json_path
        else:
            logger.warning(f"No abstract available for {bibtex_val}.")
            return None, False, bibtex_val, json_path

    elif os.path.exists(source_path):
        # Process XML file if available
        source_text = process_xml_file(source_path, save_json=False)
        source_text = OrderedDict({**bibtex_data, **source_text})
        return json.dumps(source_text, indent=2), True, bibtex_val, json_path

    else:
        # If no valid PDF or XML file, log and return failure
        logger.warning(f"Source file missing: {source_path}")
        return None, False, bibtex_val, json_path

def extract_json_between_markers(llm_output):
    # Regular expression pattern to find JSON content between ```json and ```
    json_pattern = r"```json(.*?)```"
    matches = re.findall(json_pattern, llm_output, re.DOTALL)

    if not matches:
        # Fallback: Try to find any JSON-like content in the output
        json_pattern = r"\{.*?\}"
        matches = re.findall(json_pattern, llm_output, re.DOTALL)

    for json_string in matches:
        json_string = json_string.strip()
        try:
            parsed_json = json.loads(json_string)
            return parsed_json
        except json.JSONDecodeError:
            # Attempt to fix common JSON issues
            try:
                # Remove invalid control characters
                json_string_clean = re.sub(r"[\x00-\x1F\x7F]", "", json_string)
                parsed_json = json.loads(json_string_clean)
                return parsed_json
            except json.JSONDecodeError:
                continue  # Try next match

    return None  # No valid JSON found

def get_info_ai_chatgpt(bibtex_val,user_request, system_instruction, client, model_name="gpt-4o-mini"):
    """
    Get AI response for the given abstract using the provided instruction.
    Returns True, False, or 'Uncertain'.
    """

    try:
        completion = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": user_request},

            ],
            response_format= { "type":"json_object" }
        )
    except Exception as e:
        return f"Error when processing {bibtex_val}: {e}"
    try:
        output = completion.choices[0].message.content

        return output
    except Exception as e:
        return f"Error when processing {bibtex_val}: {e}"

def setup_ai_model(model_name="gpt-4o-mini"):


    if model_name in ["gpt-4o-mini", "gpt-4o"]:
        model = ChatOpenAI(model=model_name)
    else:

        if "GOOGLE_API_KEY" not in os.environ:
            GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
            os.environ["GOOGLE_API_KEY"] = GEMINI_API_KEY

        from langchain_google_genai import ChatGoogleGenerativeAI

        model = ChatGoogleGenerativeAI(
            model=model_name,
            temperature=0,
            max_tokens=None,
            timeout=None,
            max_retries=2,
            # other params...
        )
    return model


def get_info_ai(bibtex_val,user_request, system_instruction, client):
    """
    Get AI response for the given abstract using the provided instruction.
    Returns True, False, or 'Uncertain'.
    """
    # model = ChatOpenAI(model=model_name)
    try:
        messages = [
            SystemMessage(system_instruction),
            HumanMessage(user_request),
        ]
    except Exception as e:
        error_trace = traceback.format_exc()
        return f"Error when processing {bibtex_val}:\n{error_trace}"

    try:
        response =client.invoke(messages)

    except Exception as e:
        error_trace = traceback.format_exc()
        return f"Error when processing {bibtex_val}:\n{error_trace}"
    try:
        output = response.content

        return output
    except Exception as e:
        error_trace = traceback.format_exc()
        return f"Error when processing {bibtex_val}:\n{error_trace}"



def validate_json_data(user_json_input, system_prompt):
    """
    Validate the user JSON using Pydantic.
    If validation fails, return (False, error_message or updated_prompt).
    If success, return (True, validated_data).
    """
    try:
        validated_data = parse_ai_output(user_json_input)
        return True, validated_data
    except ValueError as e:
        error_message = str(e)
        # Append error message into the system_prompt to help user correct errors
        updated_prompt = system_prompt + "\n\n" + error_message
        return False, updated_prompt


def load_yaml(file_path):
    """Load a YAML file and return its contents."""
    with open(file_path, "r") as file:
        return yaml.safe_load(file)

def combine_role_instruction(config, placeholders, agent_name):
    """
    Combine role, goal, backstory, evaluation_criteria, expected_output, and additional_notes
    into a single role instruction, dynamically replacing placeholders, and excluding any empty or blank keys.

    Args:
        config (dict): The configuration loaded from YAML.
        placeholders (dict): The placeholders to replace in the templates (e.g., {topic}, {topic_context}).
        agent_name (str): The name of the agent whose configuration to use.

    Returns:
        str: The combined role instruction.
    """

    # Helper function to handle strings and lists
    def process_component(component):
        if isinstance(component, list):
            return "\n".join(item.format(**placeholders) for item in component)
        # Escape curly braces in components that are JSON-like
        if '{' in component and '}' in component:
            return component  # Return as is to avoid formatting errors
        return component.format(**placeholders).strip()

    # Extract and format the components, skipping empty keys
    components = {
        "role": process_component(config[agent_name].get("role", "")),
        "goal": process_component(config[agent_name].get("goal", "")),
        "backstory": process_component(config[agent_name].get("backstory", "")),
        "evaluation_criteria": process_component(config[agent_name].get("evaluation_criteria", [])),
        "expected_output": process_component(config[agent_name].get("expected_output", "")),
        "additional_notes": process_component(config[agent_name].get("additional_notes", "")),
    }

    # Combine non-empty components
    combined_instruction = "\n\n".join(
        f"{key}: {value}" for key, value in components.items() if value
    )

    return combined_instruction


