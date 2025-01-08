import yaml

import os
from pydantic import RootModel
from typing import Any, Dict, Union
import json
# Pydantic model for validation using RootModel
class AIOutputModel(RootModel[Union[str, Dict[str, Any]]]):
    pass


def parse_ai_output(user_json_input: str):
    """Attempt to parse the user's JSON input into a bool or dict using Pydantic."""
    try:
        data = json.loads(user_json_input)
    except json.JSONDecodeError:
        data = user_json_input.strip().lower()


    # If data is a string "True"/"False", convert it to boolean
    if isinstance(data, str):
        lower_str = data.strip().lower()
        if lower_str == "true":
            data = 'relevance'
        elif lower_str == "false":
            data = 'not_relevance'
        else:
            raise ValueError("String provided is not 'True' or 'False'.")



    # Now data should be either a bool or a dict
    # Pydantic validation
    try:
        validated = AIOutputModel.parse_obj(data)
        return validated.root  # returns the underlying bool or dict
    except Exception as e:
        # Validation error from Pydantic
        raise ValueError(f"Pydantic validation error: {str(e)}")

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



def main():
    import yaml

    # Simulating YAML loading
    yaml_content = """
    abstract_filter:
      role: >
        An expert evaluator specializing in the relevance of research abstracts 
        related to {topic}. 
        You possess advanced knowledge of machine learning applications 
        specifically tailored to {topic_context}.
    
      goal: >
        Determine whether the provided abstract is directly relevant to the 
        research topic: "{topic}". 
        The evaluation should focus on identifying:
        - The use of machine learning techniques.
        - A specific application to {topic}.
    
      backstory: >
        You are a seasoned researcher with extensive expertise in the intersection 
        of machine learning and {topic_context}, particularly in identifying 
        and classifying {topic}. Your task is to filter abstracts, 
        ensuring that only those that contribute significantly to the specified 
        research topic are considered relevant.
    
      evaluation_criteria:
        - The abstract explicitly focuses on {topic}.
        - Machine learning methods or algorithms are clearly applied to the {topic} process.
        - The abstract contributes directly to the stated research focus without excessive divergence.
    
      expected_output: >
        A boolean value:
        - True if the abstract is directly relevant to the specified topic, 
          addressing both {topic} and machine learning techniques.
        - False if the abstract does not meet the criteria or lacks sufficient relevance 
          to the specified topic.
    
      additional_notes: >
        Provide concise and clear justifications for the evaluation decision, if required.
    """

    # Load YAML data
    config = yaml.safe_load(yaml_content)

    # Define placeholders
    placeholders = {
        "topic": "EEG-based fatigue classification",
        "topic_context": "neurophysiological analysis"
    }

    # Call the function
    system_prompt = combine_role_instruction(config, placeholders, "abstract_filter")
    print(system_prompt)

if __name__ == "__main__":
    main()

