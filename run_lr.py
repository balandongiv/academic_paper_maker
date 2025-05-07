from research_filter.auto_llm import run_pipeline
from setting.project_path import project_folder
import os
# project_review='eeg_review'
project_review='corona_discharge'
path_dic=project_folder(project_review=project_review)
main_folder = path_dic['main_folder']

# Editable variables
# model_name = "gpt-4o"  # or "gpt-4o"
model_name="gpt-4o-mini"
# model_name="gpt-o3-mini"
# model_name='gemini-1.5-pro'

# model_name='gemini-exp-1206'
# model_name='gemini-2.0-flash-thinking-exp-01-21'


agentic_setting = {
    "agent_name": "abstract_wafer_abstract_filter",
    "column_name": "abstract_wafer_abstract_filter",
    "yaml_path": r"C:\Users\balan\IdeaProjects\academic_paper_maker\research_filter\agent\agent_ml.yaml",
    "model_name": model_name
}

methodology_json_folder=os.path.join(main_folder,agentic_setting['agent_name'],'json_output')
multiple_runs_folder =os.path.join(main_folder,agentic_setting['agent_name'],'multiple_runs_folder')
final_cross_check_folder = os.path.join(main_folder,agentic_setting['agent_name'],'final_cross_check_folder')

csv_path = path_dic['csv_path']
# Basic placeholders for roles
placeholders = {} # we just ignore this as im to lazy to generalize things


process_setup={
    'batch_process':False,  # This is for the batch processing which have 50% discount. use with the code research_filter/check_batch_process.py
    'manual_paste_llm':False,       # This is for the manual paste of the LLM
    'iterative_confirmation':False,
    'overwrite_csv':False,      # careful when set to true as this will overwrite the csv file
    'cross_check_enabled':False,
    'cross_check_runs':3,
    'cross_check_agent_name':'agent_cross_check',
    'cleanup_json':False
}

# Run pipeline
run_pipeline(
    agentic_setting ,process_setup,
    placeholders=placeholders,
    csv_path=csv_path,
    main_folder=main_folder,
    methodology_json_folder=methodology_json_folder,
    multiple_runs_folder=multiple_runs_folder,
    final_cross_check_folder=final_cross_check_folder,
)

