import json


class SafeDict(dict):
    """
    A dict that returns an unresolved placeholder '{key}' when key is missing.
    """
    def __missing__(self, key):
        return '{' + key + '}'


def construct_agent_profile(
        config,
        placeholders,
        agent_name,
        standard_sections=None
):
    """
    Combine an agent's defined fields into a formatted instruction string,
    safely substituting placeholders and preserving JSON literals.

    This function builds a structured prompt or instruction from an agent's configuration,
    applying placeholder substitution in fields like 'role', 'goal', etc. It supports
    default formatting behavior but also allows users to override the section order and
    composition.

    :param config: Dict mapping agent names to their respective configurations.
                  Each configuration may include keys like 'role', 'goal',
                  'backstory', etc., and arbitrary custom keys.

    :param placeholders: Dict of placeholder values to substitute into the agent
                         configuration fields. Supports case-insensitive keys.
                         E.g., {"RESEARCH_TOPIC": "EEG", "TOPIC_CONTEXT": "brain signals"}

    :param agent_name: The key for the agent configuration within the `config` dict.

    :param standard_sections: Optional list of section keys in desired order which
                              users can override. This controls which keys are treated
                              as standard sections (processed in order and grouped first).

                              - If not provided, defaults to:
                                ["role", "goal", "backstory", "evaluation_criteria",
                                 "expected_output", "additional_notes"]

                              - Any keys not in `standard_sections` are considered "extras"
                                and are included alphabetically after the main sections.

                              - You can use this to:
                                • Limit which sections are shown
                                • Reorder output (e.g., show 'expected_output' first)
                                • Skip defaults entirely and provide your own list

    :return: A single instruction string with sections formatted like:
             "role: ...\\n\\ngoal: ...\\n\\nextra_key: ..."
             Fields with empty or null values are omitted.
    """

    agent_cfg = config.get(agent_name, {})
    placeholders = placeholders or {}

    # Build a format mapping with both original and lowercase keys
    mapping = SafeDict({**placeholders, **{k.lower(): v for k, v in placeholders.items()}})

    def is_json_literal(s):
        if not isinstance(s, str):
            return False
        text = s.strip()
        if not (text.startswith('{') and text.endswith('}')):
            return False
        try:
            json.loads(text)
            return True
        except json.JSONDecodeError:
            return False

    def process(value):
        if not value:
            return ''
        if isinstance(value, list):
            return '\n'.join(process(item) for item in value if item)
        if is_json_literal(value):
            return value
        if isinstance(value, str):
            try:
                return value.format_map(mapping).strip()
            except Exception:
                return value
        return str(value)

    # Default standard sections if not provided by user. User can override by supplying their own.
    default_sections = [
        "role",
        "goal",
        "backstory",
        "evaluation_criteria",
        "expected_output",
        "additional_notes",
    ]
    sections = standard_sections or default_sections

    parts = []
    # First, process standard sections in order
    for key in sections:
        text = process(agent_cfg.get(key))
        if text:
            parts.append(f"{key}: {text}")

    # Then include any extra fields alphabetically
    extra = sorted(set(agent_cfg) - set(sections))
    for key in extra:
        text = process(agent_cfg.get(key))
        if text:
            parts.append(f"{key}: {text}")

    return '\n\n'.join(parts)
