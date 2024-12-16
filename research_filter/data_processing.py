import pandas as pd
from abstract_filtering import prepare_data_abstract_filtering
from analyse_pdf import prepare_data_analyse_pdf
from config import AGENT_NAME_MAPPING


def load_activity_data(df, activity_var, current_index, update_status):
    """Filter rows for the selected activity and update indices."""
    activity_selected = activity_var.get()
    if activity_selected == "abstract_filtering":
        rows_to_process = df[df['ai_output'].isna() | (df['ai_output'] == '')].copy()
    elif activity_selected == "analyse_pdf":
        rows_to_process = df[df['pdf_analysis_output'].isna() | (df['pdf_analysis_output'] == '')].copy()
    else:
        rows_to_process = pd.DataFrame()

    if rows_to_process.empty:
        update_status("No rows left to process.")
        return []

    return rows_to_process.index.tolist()


def load_row_data(idx, df, activity_var, config, placeholders):
    """Prepare data for the current row based on the activity."""
    row = df.loc[idx]
    activity_selected = activity_var.get()
    agent_name = AGENT_NAME_MAPPING.get(activity_selected, AGENT_NAME_MAPPING["abstract_filtering"])

    if activity_selected == "abstract_filtering":
        combined_string, bib_ref, system_prompt = prepare_data_abstract_filtering(row, config, placeholders, agent_name)
    elif activity_selected == "analyse_pdf":
        combined_string, bib_ref, system_prompt = prepare_data_analyse_pdf(row, config, placeholders, agent_name)
    else:
        combined_string, bib_ref, system_prompt = "No activity selected", f"row_{idx}", ""

    return combined_string, bib_ref, system_prompt
