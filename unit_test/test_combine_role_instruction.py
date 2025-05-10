"""
Unit tests for the `combine_role_instruction` function.

This test suite validates the behavior of a function that composes structured
instruction text for an agent based on its configuration and placeholder mappings.
The core functionality includes safely formatting strings, preserving JSON-like
values, and allowing customizable ordering of output sections.

Test Cases Covered:
-------------------
1. test_agent1_full_structure:
   - Verifies that all standard fields (role, goal, backstory, evaluation_criteria)
     are correctly populated and placeholder values are replaced accurately.

2. test_agent2_partial_fields:
   - Ensures the function works correctly even when only a subset of standard fields
     is provided, with proper substitution of placeholders.

3. test_agent3_json_passthrough:
   - Confirms that fields containing JSON-formatted strings are preserved and
     not interpreted as placeholders.

4. test_agent4_with_extra_key:
   - Validates the inclusion of non-standard (custom) fields like `extra_tip` in
     the final output, even if they're not part of the default schema.

5. test_custom_standard_sections:
   - Tests support for user-defined `standard_sections` to customize the field
     ordering and inclusion logic. Demonstrates reordering and subset selection
     of fields in the output.

Each test uses the `self.config` and `self.placeholders` dictionaries defined
in the `setUp` method to simulate real-world agent configurations and context.
The tests rely on exact string comparisons to ensure deterministic formatting.

Usage:
------
Run the tests using the standard unittest runner:

    python -m unittest unit_test/test_combine_role_instruction.py
"""


import unittest
import logging
from research_filter.role_instruction_builder import construct_agent_profile

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def checking_with_actual_yaml():
    """
    Testing utility to verify the output of `construct_agent_profile` using a real YAML agent file.

    This function serves as a manual check to validate:
    - That the YAML file is correctly loaded and parsed.
    - That the agent profile is composed as expected using actual data.
    - That the system handles non-GPT model names (like Gemini) gracefully.

    Note:
    - This assumes `load_config_file` correctly reads and parses YAML into a dict.
    - The model_name is set to a non-GPT model ('gemini-1.5-pro') to demonstrate how
      GPT-model specific logic (e.g., special formatting or model instantiation)
      can be bypassed or handled conditionally elsewhere in the app.
    - Make sure the YAML path exists locally when running this test.

    You can use this function during development to spot issues with placeholder
    substitution, missing fields, or unexpected formatting in real scenarios.
    """

    yaml_path = r'C:\Users\balan\IdeaProjects\academic_paper_maker\research_filter\agent\abstract_check.yaml'
    from research_filter.agent_helper import load_config_file

    config = load_config_file(yaml_path)
    agent_name = "abstract_filter"
    model_name = 'gemini-1.5-pro'

    agentic_setting = {
        "agent_name": agent_name,
        "column_name": agent_name,
        "yaml_path": yaml_path,
        "model_name": model_name
    }

    placeholders = {
        "topic": "EEG-based fatigue classification",
        "topic_context": "neurophysiological analysis"
    }

    # Prepare role instructions
    logger.info(f"Preparing role instructions for {agentic_setting['agent_name']}.")
    role_instruction_main = construct_agent_profile(config, placeholders, agentic_setting['agent_name'])

    print(role_instruction_main)




class TestCombineRoleInstruction(unittest.TestCase):
    def setUp(self):
        self.config = {
            "agent1": {
                "role": "Researcher specialized in {RESEARCH_TOPIC}",
                "goal": "Investigate the mechanisms behind {topic_context}",
                "backstory": "Worked on neuroimaging projects.",
                "evaluation_criteria": [
                    "Relevance to {topic_context}",
                    "Scientific rigor"
                ],
                "expected_output": "",
                "additional_notes": ""
            },
            "agent2": {
                "role": "Analyst for {RESEARCH_TOPIC}",
                "expected_output": "Summary report on {TOPIC_CONTEXT}"
            },
            "agent3": {
                "role": "Engineer",
                "goal": "",
                "evaluation_criteria": [],
                "expected_output": "{\"metric\": \"accuracy\"}"
            },
            "agent4": {
                "role": "Coordinator",
                "extra_tip": "Always consider {TOPIC_CONTEXT}",
                "notes": ""
            }
        }

        self.placeholders = {
            "RESEARCH_TOPIC": "EEG-based fatigue classification",
            "TOPIC_CONTEXT": "neurophysiological analysis"
        }

    def test_agent1_full_structure(self):
        logger.info("Running test_agent1_full_structure")
        expected1 = str(
            "role: Researcher specialized in EEG-based fatigue classification\n\n"
            "goal: Investigate the mechanisms behind neurophysiological analysis\n\n"
            "backstory: Worked on neuroimaging projects.\n\n"
            "evaluation_criteria: Relevance to neurophysiological analysis\nScientific rigor"
        )
        result = construct_agent_profile(self.config, self.placeholders, "agent1")
        self.assertEqual(result, expected1)

    def test_agent2_partial_fields(self):
        logger.info("Running test_agent2_partial_fields")
        expected2 = str(
            "role: Analyst for EEG-based fatigue classification\n\n"
            "expected_output: Summary report on neurophysiological analysis"
        )
        result = construct_agent_profile(self.config, self.placeholders, "agent2")
        self.assertEqual(result, expected2)

    def test_agent3_json_passthrough(self):
        logger.info("Running test_agent3_json_passthrough")
        expected3 = str(
            "role: Engineer\n\n"
            "expected_output: {\"metric\": \"accuracy\"}"
        )
        result = construct_agent_profile(self.config, self.placeholders, "agent3")
        self.assertEqual(result, expected3)

    def test_agent4_with_extra_key(self):
        logger.info("Running test_agent4_with_extra_key")
        expected4 = str(
            "role: Coordinator\n\n"
            "extra_tip: Always consider neurophysiological analysis"
        )
        result = construct_agent_profile(self.config, self.placeholders, "agent4")
        self.assertEqual(result, expected4)

    def test_custom_standard_sections(self):
        logger.info("Running test_custom_standard_sections")
        custom_sections = ["expected_output", "role"]
        expected = str(
            "expected_output: Summary report on neurophysiological analysis\n\n"
            "role: Analyst for EEG-based fatigue classification"
        )
        result = construct_agent_profile(
            self.config, self.placeholders, "agent2", standard_sections=custom_sections
        )
        self.assertEqual(result, expected)
def chiking_with_actual_yaml():
    yaml_path=r'C:\Users\balan\IdeaProjects\academic_paper_maker\research_filter\agent\agent_ml.yaml'
    from research_filter.agent_helper import parse_ai_output, load_config_file
    config=load_config_file(yaml_path)
    agent_name="methodology_gap_extractor_partial_discharge"
    model_name='gemini-1.5-pro'
    agentic_setting = {
        "agent_name": agent_name,
        "column_name": agent_name,
        "yaml_path": yaml_path,
        "model_name": model_name
    }
    model_name = agentic_setting['model_name']
    column_name = agentic_setting['column_name']
    placeholders = {
        "topic": "EEG-based fatigue classification",
        "topic_context": "neurophysiological analysis"
    }
    # Prepare role instructions
    logger.info(f"Preparing role instructions for {agentic_setting['agent_name']}.")
    role_instruction_main = construct_agent_profile(config, placeholders, agentic_setting['agent_name'])
    g=1
    print(role_instruction_main)

if __name__ == "__main__":
    unittest.main()
    checking_with_actual_yaml()
    a=1