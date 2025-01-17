import json
import re
from typing import Any, Dict, Union

import yaml
from pydantic import RootModel


# Pydantic model for validation using RootModel
class AIOutputModel(RootModel[Union[str, Dict[str, Any]]]):
    pass


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


def get_info_ai(bibtex_val,abstract, instruction, client, model_name="gpt-4o-mini"):
    """
    Get AI response for the given abstract using the provided instruction.
    Returns True, False, or 'Uncertain'.
    """
    # mock_data={
    #     "technical_gaps": [
    #         {
    #             "issue": "Computer vision-based methods for drowsiness detection are highly sensitive to external conditions such as occlusion, illumination, and clothing.",
    #             "consequence": "These methods produce unreliable results in varying environmental conditions, compromising the robustness of the detection system.",
    #             "proposed_solution": {
    #                 "strategy": "Shift focus to physiological signal-based methods, particularly EEG signals, which reflect brain dynamics and are less impacted by external conditions.",
    #                 "advantages": "EEG signals offer higher reliability and robustness in detecting driver drowsiness, unaffected by external physical conditions."
    #             }
    #         },
    #         {
    #             "issue": "Traditional EEG-based machine learning methods rely on handcrafted feature extraction, which demands significant domain expertise and often yields suboptimal performance.",
    #             "consequence": "The reliance on handcrafted features limits the scalability and adaptability of these systems to diverse and dynamic scenarios.",
    #             "proposed_solution": {
    #                 "strategy": "Adopt deep learning methods, specifically CNNs, to enable end-to-end learning of task-relevant features directly from raw EEG data.",
    #                 "advantages": "Improved feature representation, reduced dependency on domain expertise, and enhanced classification performance."
    #             }
    #         },
    #         {
    #             "issue": "CNN architectures struggle with cross-subject classification due to inter-subject variability in EEG signals.",
    #             "consequence": "This limitation reduces the generalizability of the model, making it less effective for real-world applications where subject-specific variations are common.",
    #             "proposed_solution": {
    #                 "strategy": "Introduce the Gumbel-Softmax trick to optimize EEG channel selection and minimize inter-subject variability in an end-to-end framework.",
    #                 "advantages": "Improved cross-subject classification accuracy, reduced computational burden, and enhanced generalizability of the detection model."
    #             }
    #         },
    #         {
    #             "issue": "Processing all EEG channels increases model complexity and computational burden, making real-time detection challenging.",
    #             "consequence": "This hampers the feasibility of deploying EEG-based drowsiness detection systems in real-time applications.",
    #             "proposed_solution": {
    #                 "strategy": "Implement channel selection using Gumbel-Softmax discrete sampling to reduce data dimensionality and focus on relevant EEG channels.",
    #                 "advantages": "Lower computational cost, reduced model complexity, and improved efficiency suitable for real-time applications."
    #             }
    #         },
    #         {
    #             "issue": "Deep learning models often lack interpretability and are affected by extraneous EEG channels.",
    #             "consequence": "The presence of redundant information reduces the model's interpretability and efficiency, leading to suboptimal performance.",
    #             "proposed_solution": {
    #                 "strategy": "Incorporate penalties on weight matrix row sums to prevent the selection of duplicate channels and enhance model interpretability.",
    #                 "advantages": "Improved interpretability, reduced redundancy, and better optimization of network parameters for practical applications."
    #             }
    #         },
    #         {
    #             "issue": "Few studies simulate real-time EEG-based driver drowsiness detection systems.",
    #             "consequence": "The lack of real-time application frameworks limits the practical utility of these methodologies in the transportation industry.",
    #             "proposed_solution": {
    #                 "strategy": "Develop a graphical user interface (GUI) for real-time simulation of driver drowsiness detection using the proposed model.",
    #                 "advantages": "Provides a practical and user-friendly solution for real-time driver monitoring, bridging the gap between research and application."
    #             }
    #         }
    #     ]
    # }
    # return mock_data
    try:
        completion = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": instruction},
                {"role": "user", "content": abstract},

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

