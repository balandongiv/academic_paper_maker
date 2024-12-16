import os
from PyPDF2 import PdfReader
from research_filter.agent_helper import combine_role_instruction

def prepare_data_analyse_pdf(row, config, placeholders, agent_name):
    pdf_path = row.get('attachments', '')
    bib_ref = row.get('bibtex')

    # Extract text from PDF
    pdf_text = f"This is test pdf text for {bib_ref}"
    if pdf_path and os.path.exists(pdf_path):
        try:
            reader = PdfReader(pdf_path)
            for page in reader.pages:
                pdf_text += page.extract_text() + "\n"
        except Exception as e:
            pdf_text = f"Error reading PDF: {e}"

    # Combine system prompt
    system_prompt = combine_role_instruction(config, placeholders, agent_name)
    combined_string = f"{system_prompt}\n The PDF text is as follows:\n{pdf_text}"

    return combined_string, bib_ref, system_prompt

def save_output_analyse_pdf(df, idx, ai_output):
    df.at[idx, 'pdf_analysis_output'] = ai_output
