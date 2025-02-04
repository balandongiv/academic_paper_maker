# from research_filter.agent_helper import load_config_file
import yaml

# config = load_config_file(yaml_path)
def load_yaml(file_path):
    """Load a YAML file and return its contents."""
    with open(file_path, "r") as file:
        return yaml.safe_load(file)


file_path = r"C:\Users\balan\IdeaProjects\academic_paper_maker\research_filter\agent\agent_ml.yaml"
config=load_yaml(file_path)
gg=config['methodology_gap_extractor']['expected_output']
iterative_agent=config['iterative_validation']
dfhdf=1
for key_agent, instruction_me in iterative_agent.items():  # Use .items() to unpack key-value pairs
    combined_instruction = (
        f"{instruction_me}\n"
        f"The manuscript is as follows:"
    )
    print(combined_instruction)
h=1