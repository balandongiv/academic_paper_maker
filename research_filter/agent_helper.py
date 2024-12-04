def combine_role_instruction(config, placeholders,agent_name):
    """
    Combine goal, backstory, evaluation_criteria, expected_output, and additional_notes
    into a single role instruction.

    Args:
        config (dict): The configuration loaded from YAML.
        placeholders (dict): The placeholders to replace in the templates.

    Returns:
        str: The combined role instruction.
    """
    # Extract and format the components
    goal = config[agent_name]["goal"].format(**placeholders)
    backstory = config[agent_name]["backstory"].format(**placeholders)
    evaluation_criteria =  config[agent_name]["evaluation_criteria"].format(**placeholders)
    expected_output = config[agent_name]["expected_output"].format(**placeholders)
    additional_notes = config[agent_name]["additional_notes"].format(**placeholders)

    # Combine all components
    combined_instruction = (
        f"goal: {goal}\n\n"
        f"backstory: {backstory}\n\n"
        f"evaluation_criteria:\n{evaluation_criteria}\n\n"
        f"expected_output: {expected_output}\n\n"
        f"additional_notes: {additional_notes}"
    )
    return combined_instruction