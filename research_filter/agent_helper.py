import os
import re
from typing import Any, Dict, Union

import yaml
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import RootModel


# Pydantic model for validation using RootModel
class AIOutputModel(RootModel[Union[str, Dict[str, Any]]]):
    pass


import json

def parse_ai_output(ai_output, column_name):
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
                return parsed_data
            else:
                # Attempt to parse ai_output if it's a JSON string
                parsed_data = json.loads(ai_output)
        except json.JSONDecodeError:
            # Handle JSON decoding errors gracefully
            parsed_data = {
                column_name: {
                    "error_msg": f"Error parsing JSON: {ai_output}"
                }
            }
        except Exception as e:
            # Handle unexpected errors gracefully
            parsed_data = {
                column_name: {
                    "error_msg": f"Unexpected error: {str(e)}"
                }
            }
    return parsed_data


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
            model=model_name,   #"gemini-1.5-pro",
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

    messages = [
        SystemMessage(system_instruction),
        HumanMessage(user_request),
    ]


    try:
        response =client.invoke(messages)

    except Exception as e:
        return f"Error when processing {bibtex_val}: {e}"
    try:
        output = response.content

        return output
    except Exception as e:
        return f"Error when processing {bibtex_val}: {e}"



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


