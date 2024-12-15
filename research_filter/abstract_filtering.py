from research_filter.agent_helper import combine_role_instruction

def prepare_data_abstract_filtering(row, config, placeholders, agent_name):
    abstract = row.get('abstract', '')
    bib_ref = row.get('bib_ref', f"row_{row.name}")
    # Combine system prompt
    system_prompt = combine_role_instruction(config, placeholders, agent_name)
    combined_string = f"{system_prompt}\n The abstract is as follow: {abstract}"
    return combined_string, bib_ref, system_prompt

def save_output_abstract_filtering(df, idx, ai_output):
    df.at[idx, 'ai_output'] = ai_output
