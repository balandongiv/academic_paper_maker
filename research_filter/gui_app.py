import os
import json
import tkinter as tk
from tkinter import messagebox, ttk
import pandas as pd
import pyperclip
import shutil
from config import (
    DEBUG,
    ACTIVITY_NOW,
    DEFAULT_ACTIVITY,
    AGENT_NAME_MAPPING,
    FILE_PATH,
    YAML_PATH,
    placeholders,
    JSON_OUTPUT_DIR,
    AIOutputModel
)
from research_filter.agent_helper import combine_role_instruction, load_yaml


def parse_ai_output(user_json_input: str):
    """Attempt to parse the user's JSON input into a bool or dict using Pydantic."""
    try:
        data = json.loads(user_json_input)
    except json.JSONDecodeError:
        data = user_json_input.strip().lower()
        # data=f'"{user_json_input}"'
        # raise ValueError("Invalid JSON format. Please ensure valid JSON input.")

    # If data is a string "True"/"False", convert it to boolean
    if isinstance(data, str):
        lower_str = data.strip().lower()
        if lower_str == "true":
            data = True
        elif lower_str == "false":
            data = False
        else:
            raise ValueError("String provided is not 'True' or 'False'.")



    # Now data should be either a bool or a dict
    # Pydantic validation
    try:
        validated = AIOutputModel.parse_obj(data)
        return validated.root  # returns the underlying bool or dict
    except Exception as e:
        # Validation error from Pydantic
        raise ValueError(f"Pydantic validation error: {str(e)}")


def validate_json_data(user_json_input, system_prompt):
    """
    Validate the user JSON using Pydantic.
    If validation fails, return (False, error_message or updated_prompt).
    If success, return (True, validated_data).
    """
    try:
        validated_data = parse_ai_output(user_json_input)
        return True, validated_data
    except ValueError as e:
        error_message = str(e)
        # Append error message into the system_prompt to help user correct errors
        updated_prompt = system_prompt + "\n\n" + error_message
        return False, updated_prompt


def main():
    # Load Excel file
    df = pd.read_excel(FILE_PATH)

    # Ensure 'ai_related' column exists for storing processed JSON data at the end
    if 'ai_related' not in df.columns:
        df['ai_related'] = ""

    # Filter rows for processing (those not processed yet)
    rows_to_process = df[df['ai_related'].isna() | (df['ai_related'] == '')].copy()

    if rows_to_process.empty:
        print("No rows left to process.")
        return

    # Load YAML file and extract system prompt
    config = load_yaml(YAML_PATH)

    # Create main Tkinter window
    root = tk.Tk()
    root.title("Abstract Filtering Tool")

    # State variables
    row_indices = rows_to_process.index.tolist()
    current_index = tk.IntVar(value=0)
    status_message = tk.StringVar(value="Ready to start.")

    def update_status(message):
        """Update the dynamic status message."""
        status_message.set(message)

    def on_activity_change(event):
        pass  # If needed, handle changes in the selection

    activity_var = tk.StringVar(value=ACTIVITY_NOW if DEBUG else DEFAULT_ACTIVITY)
    activity_label = tk.Label(root, text="Select Activity:")
    activity_label.pack(pady=5)
    activity_dropdown = ttk.Combobox(root, textvariable=activity_var, values=["abstract_filtering", "analyse_pdf"], state="readonly")
    activity_dropdown.bind("<<ComboboxSelected>>", on_activity_change)
    activity_dropdown.pack(pady=5)

    # Instructions
    instruction_label = tk.Label(root, text=(
        "Instructions:\n"
        "1. The combined prompt+abstract is copied to the clipboard.\n"
        "2. Process it externally and paste the resulting JSON below.\n"
        "3. Click 'Save & Next' to validate, save, and move to the next row.\n"
        "4. Use 'Exit' to finish."
    ))
    instruction_label.pack(pady=5)

    # Labels and Text boxes
    combined_text_label = tk.Label(root, text="Combined Prompt + Abstract:")
    combined_text_label.pack()

    combined_text_box = tk.Text(root, height=10, width=70, wrap='word')
    combined_text_box.pack(pady=5)

    json_input_label = tk.Label(root, text="Paste JSON here:")
    json_input_label.pack()

    json_text_box = tk.Text(root, height=10, width=70)
    json_text_box.pack(pady=5)

    # Dynamic status section
    status_label = tk.Label(root, textvariable=status_message, fg="blue")
    status_label.pack(pady=10)

    # Helper Functions
    def load_row_data():
        idx = row_indices[current_index.get()]
        row = df.loc[idx]
        abstract = row.get('Abstract', '')
        bib_ref = row.get('bib_ref', f"row_{idx}")

        # Determine agent_name from activity
        activity_selected = activity_var.get()
        agent_name = AGENT_NAME_MAPPING.get(activity_selected, AGENT_NAME_MAPPING["abstract_filtering"])

        # Combine system prompt
        system_prompt = combine_role_instruction(config, placeholders, "abstract_filter")
        combined_string = f"{system_prompt}\n The abstract is as follow: {abstract}"
        return idx, bib_ref, combined_string, system_prompt

    def display_current_row():
        # Display combined prompt+abstract for current row
        update_status("Loading row data...")
        _, bib_ref, combined_string, _ = load_row_data()
        combined_text_box.delete("1.0", tk.END)
        combined_text_box.insert(tk.END, combined_string)
        # Copy to clipboard
        pyperclip.copy(combined_string)
        root.title(f"Processing: {bib_ref}")

        # Clear the JSON box for fresh input
        json_text_box.delete("1.0", tk.END)
        update_status("Ready for JSON input.")

    def save_and_next():
        update_status("Validating and saving data...")
        user_json_input = json_text_box.get("1.0", tk.END).strip()
        if not user_json_input:
            messagebox.showerror("Error", "No JSON input provided.")
            update_status("Validation failed: No JSON input.")
            return

        idx, bib_ref, _, system_prompt = load_row_data()
        valid, result = validate_json_data(user_json_input, system_prompt)
        if not valid:
            # result is the error message or updated prompt with error
            messagebox.showerror("Validation Error", f"Error in JSON:\n\n{result}")
            update_status("Validation failed: Invalid JSON.")
            return

        # Save JSON file
        final_data = result
        json_file_path = os.path.join(JSON_OUTPUT_DIR, f"{bib_ref}.json")
        with open(json_file_path, 'w') as json_file:
            json.dump(final_data, json_file, indent=4)

        update_status("Data saved successfully. Moving to the next row...")

        # Move to the next row if possible
        current_pos = current_index.get()
        if current_pos < len(row_indices) - 1:
            current_index.set(current_pos + 1)
            display_current_row()
        else:
            messagebox.showinfo("Done", "No more rows to process.")
            update_status("All rows processed.")

    def on_exit():
        update_status("Finalizing and saving data...")
        # On exit, update df with processed JSON data
        for idx in row_indices:
            bib_ref = df.at[idx, 'bib_ref'] if 'bib_ref' in df.columns else f"row_{idx}"
            json_file_path = os.path.join(JSON_OUTPUT_DIR, f"{bib_ref}.json")
            if os.path.exists(json_file_path):
                try:
                    with open(json_file_path, 'r') as f:
                        data = json.load(f)
                    if isinstance(data, bool):
                        df.at[idx, 'ai_related'] = data
                    else:
                        df.at[idx, 'ai_related'] = json.dumps(data)
                except Exception as e:
                    print(f"Error reading JSON for {bib_ref}: {e}")

        df.to_excel(FILE_PATH, index=False)

        # Clean up JSON directory
        for file_name in os.listdir(JSON_OUTPUT_DIR):
            file_path = os.path.join(JSON_OUTPUT_DIR, file_name)
            if os.path.isfile(file_path):
                os.remove(file_path)

        # Ensure the directory exists
        if os.path.exists(JSON_OUTPUT_DIR):
            try:
                # Use shutil.rmtree to forcefully remove the directory
                shutil.rmtree(JSON_OUTPUT_DIR)
                print(f"Successfully deleted: {JSON_OUTPUT_DIR}")
            except PermissionError as e:
                print(f"Permission denied: {e}")
            except Exception as e:
                print(f"An error occurred: {e}")
        else:
            print(f"Directory does not exist: {JSON_OUTPUT_DIR}")


        update_status("Data updated and saved. Exiting...")
        messagebox.showinfo("Exit", "Data updated and saved back to Excel.")
        root.destroy()

    # Buttons
    save_next_button = tk.Button(root, text="Save & Next", command=save_and_next)
    save_next_button.pack(pady=5)

    exit_button = tk.Button(root, text="Exit", command=on_exit)
    exit_button.pack(pady=5)

    # Initialize first row display
    display_current_row()

    root.mainloop()

if __name__ == "__main__":
    main()

