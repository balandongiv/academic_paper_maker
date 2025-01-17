'''
gemini-1.5-pro-latest
gemini-1.5-pro-001

'Gemini 1.5 Pro
'''

import google.generativeai as genai

from research_filter.agent_helper import extract_json_between_markers

genai.configure(api_key="AIzaSyB3I9SDP83-CZSdUsQsTIPum6FhY61NXkk")

# import pprint
# for model in genai.list_models():
#     pprint.pprint(model)

# model = genai.GenerativeModel("gemini-1.5-flash")
# response = model.generate_content("Explain how AI works")
# print(response.text)

def get_info_gemini(bibtex_val,user_request, instruction, model_name='gemini-1.5-pro-latest'):
    # Create the model
    generation_config = {
        "temperature": 1,
        "top_p": 0.95,
        "top_k": 40,
        "max_output_tokens": 8192,
        "response_mime_type": "text/plain",
    }

    model = genai.GenerativeModel(
        # model_name="gemini-2.0-flash-exp",
        model_name=model_name,
        generation_config=generation_config,
        system_instruction=instruction

        )



    chat_session = model.start_chat()
    try:
        response = chat_session.send_message(user_request)


        final_opt=extract_json_between_markers(response.text)
        # print(final_opt)
        return final_opt
    except Exception as e:
        return f"Error when processing {bibtex_val}: {e}"
