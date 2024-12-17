import os
from PyPDF2 import PdfReader
from research_filter.agent_helper import combine_role_instruction

def prepare_data_analyse_pdf(row, config, placeholders, agent_name):
    pdf_path = row.get('attachments', '')
    bib_ref = row.get('bibtex')
    pathss=r'C:\Users\rpb\OneDrive - ums.edu.my\research_related\0 eeg_trend_till24\eeg_review'
    pdf_name= "Dynamic_Threshold_Distribution_Domain_Adaptation_Network_A_Cross-Subject_Fatigue_Recognition_Method_Based_on_EEG_Signals.pdf"

    pdf_path=os.path.join(pathss,pdf_name)
    # Extract text from PDF
    pdf_text = f"This is the  pdf text extracted from the PDF file:"
    # pdf_path=r'file:///C:/Users/rpb/OneDrive%20-%20ums.edu.my/research_related/0%20eeg_trend_till24/eeg_review/Drowsiness_Detection_Using_Adaptive_Hermite_Decomposition_and_Extreme_Learning_Machine_for_Electroencephalogram_Signals.pdf'
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
