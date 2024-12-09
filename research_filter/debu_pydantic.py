from pydantic import BaseModel, ValidationError

from research_filter.gui_app import parse_ai_output
import json

class AIOutputModel(BaseModel):
    root: bool | dict
#
# def parse_ai_output(user_json_input: str):
#     """
#     Attempt to parse the user's JSON input into a bool or dict using Pydantic.
#     """
#     try:
#         data = json.loads(user_json_input)
#     except json.JSONDecodeError:
#         raise ValueError("Invalid JSON format. Please ensure valid JSON input.")
#
#     # If data is a string "True"/"False", convert it to boolean
#     if isinstance(data, str):
#         lower_str = data.strip().lower()
#         if lower_str == "true":
#             data = True
#         elif lower_str == "false":
#             data = False
#         else:
#             raise ValueError("String provided is not 'True' or 'False'.")
#
#     # Validate data type (should be a bool or a dict)
#     if not isinstance(data, (bool, dict)):
#         raise ValueError("Input must be either a boolean or a JSON object.")
#
#     # Pydantic validation
#     try:
#         validated = AIOutputModel(root=data)
#         return validated.root  # Return the validated bool or dict
#     except ValidationError as e:
#         raise ValueError(f"Pydantic validation error: {str(e)}")


# Input as JSON string
input_data = '"True"'

try:
    result = parse_ai_output(input_data)
    print("Parsed Result:", result)
except ValueError as e:
    print("Error:", e)