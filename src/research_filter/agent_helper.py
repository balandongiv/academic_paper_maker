import json
import logging
import os
import re
import traceback
from collections import OrderedDict
from typing import Any, Dict, Tuple
from typing import Union

import yaml
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import RootModel

from grobid_tei_xml.xml_json import process_xml_file  # Update the module name if needed

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

def compile_path(path: str) -> str:
    """Return an absolute path by joining current working directory with given path."""
    return os.path.join(os.getcwd(), path)


def load_config_file(yaml_path: str) -> dict:
    """Load YAML configuration file and return as a dictionary."""
    logger.info(f"Loading YAML configuration from {yaml_path}.")
    return load_yaml(yaml_path)


# Pydantic model for validation using RootModel
class AIOutputModel(RootModel[Union[str, Dict[str, Any]]]):
    pass


def parse_ai_output(ai_output: Any, column_name: str, model_name: str) -> Tuple[Dict, bool]:
    """
    Parses the AI output and returns a tuple of (parsed_data, status).

    Parameters:
        ai_output (Any): The output from the AI, which may be a dictionary or a JSON string.
        column_name (str): The key to use in the resulting dictionary.
        model_name (str): The name of the model (currently unused, but kept for future use).

    Returns:
        Tuple[Dict, bool]: A tuple where the first element is the parsed data as a dictionary,
                           and the second element is a boolean status (True if parsing succeeded, False otherwise).
    """
    status = True

    # If ai_output is already a dictionary, return it immediately.
    if isinstance(ai_output, dict):
        return ai_output, status

    try:
        # Check for simple JSON-like literals.
        if ai_output in ('True', 'False'):
            parsed_data = {column_name: ai_output}
            return parsed_data, status

        # Attempt to extract JSON content between markers.
        parsed_data = extract_json_between_markers(ai_output)

    except json.JSONDecodeError:
        status = False
        parsed_data = {
            column_name: {
                "error_msg": f"Error parsing JSON: {ai_output}"
            }
        }
    except Exception as e:
        status = False
        parsed_data = {
            column_name: {
                "error_msg": f"Unexpected error: {str(e)}"
            }
        }

    return parsed_data, status


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

    bibtex_val = row.get('bibtex')
    bibtex_data = {"bibtext": bibtex_val}
    if not bibtex_val:  # Ensure bibtex value exists
        logger.warning("Missing 'bibtex' value, skipping processing.")
        return None, False, None, ""

    json_path = os.path.join(output_folder, f"{bibtex_val}.json")

    source_filename = f"{bibtex_val}.grobid.tei.xml"
    source_path = os.path.join(main_folder, "xml", source_filename)


    if os.path.exists(source_path):
        # Process XML file if available
        source_text = process_xml_file(source_path, save_json=False)
        source_text = OrderedDict({**bibtex_data, **source_text})
        return json.dumps(source_text, indent=2), True, bibtex_val, json_path

    else:
        logger.info(f"Using abstract text for {bibtex_val}.")
        source_text = dict(bibtex_data, **{"abstract": row.get('abstract')})
        return json.dumps(source_text, indent=2), True, bibtex_val, json_path

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


    if "gpt" in model_name.lower():
        from langchain_openai import ChatOpenAI
        model = ChatOpenAI(model=model_name)
    elif "gemini" in model_name.lower():

        from langchain_google_genai import ChatGoogleGenerativeAI

        model = ChatGoogleGenerativeAI(
            model=model_name,
            temperature=0,
            max_tokens=None,
            timeout=None,
            max_retries=2,
            # other params...
        )
    else:
        raise ValueError(f"Unsupported model name: {model_name}")
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
