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
)
from research_filter.agent_helper import combine_role_instruction, load_yaml, validate_json_data
from abstract_filtering import prepare_data_abstract_filtering, save_output_abstract_filtering
from analyse_pdf import prepare_data_analyse_pdf, save_output_analyse_pdf


def main():
    # Load Excel file
    df = pd.read_excel(FILE_PATH)

    # Ensure columns exist for storing processed JSON data
    if 'ai_output' not in df.columns:
        df['ai_output'] = ""
    if 'pdf_analysis_output' not in df.columns:
        df['pdf_analysis_output'] = ""

    # Filter rows for processing depending on the activity
    # The filtering logic is deferred until we know which activity is selected.
    # For now, just load df. We'll filter after activity selection.

    # Load YAML config
    config = load_yaml(YAML_PATH)

    # Create main Tkinter window
    root = tk.Tk()
    root.title("Academic Tool")

    # State variables
    status_message = tk.StringVar(value="Ready to start.")

    def update_status(message):
        """Update the dynamic status message."""
        status_message.set(message)

    def on_activity_change(event):
        # When activity changes, re-load the data.
        load_activity_data()

    activity_var = tk.StringVar(value=ACTIVITY_NOW if DEBUG else DEFAULT_ACTIVITY)
    activity_label = tk.Label(root, text="Select Activity:")
    activity_label.pack(pady=5)
    activity_dropdown = ttk.Combobox(
        root,
        textvariable=activity_var,
        values=["abstract_filtering", "analyse_pdf"],
        state="readonly"
    )
    activity_dropdown.bind("<<ComboboxSelected>>", on_activity_change)
    activity_dropdown.pack(pady=5)

    # Instructions
    instruction_label = tk.Label(root, text=(
        "Instructions:\n"
        "- For 'abstract_filtering', provide JSON output in ai_output format.\n"
        "- For 'analyse_pdf', paste JSON output after analyzing PDF."
    ))
    instruction_label.pack(pady=5)

    combined_text_label = tk.Label(root, text="Combined Prompt + Input:")
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

    # Variables to hold indices for current processing
    row_indices = []
    current_index = tk.IntVar(value=0)

    def load_activity_data():
        nonlocal row_indices
        activity_selected = activity_var.get()
        if activity_selected == "abstract_filtering":
            # Filter rows that have empty or NaN in ai_output
            rows_to_process = df[df['ai_output'].isna() | (df['ai_output'] == '')].copy()
        elif activity_selected == "analyse_pdf":
            # Filter rows that have empty or NaN in pdf_analysis_output
            rows_to_process = df[df['pdf_analysis_output'].isna() | (df['pdf_analysis_output'] == '')].copy()
        else:
            rows_to_process = pd.DataFrame()

        if rows_to_process.empty:
            print("No rows left to process for this activity.")
            update_status("No rows left to process.")
            return

        row_indices = rows_to_process.index.tolist()
        current_index.set(0)
        display_current_row()

    def load_row_data():
        idx = row_indices[current_index.get()]
        row = df.loc[idx]

        activity_selected = activity_var.get()
        agent_name = AGENT_NAME_MAPPING.get(activity_selected, AGENT_NAME_MAPPING["abstract_filtering"])

        # Activity-specific preparation
        if activity_selected == "abstract_filtering":
            combined_string, bib_ref, system_prompt = prepare_data_abstract_filtering(row, config, placeholders, agent_name)
        elif activity_selected == "analyse_pdf":
            combined_string, bib_ref, system_prompt = prepare_data_analyse_pdf(row, config, placeholders, agent_name)
        else:
            # Default fallback (should not happen)
            combined_string, bib_ref, system_prompt = "No activity selected", f"row_{idx}", ""

        return idx, bib_ref, combined_string, system_prompt

    def display_current_row():
        if not row_indices:
            return
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
        if not row_indices:
            return
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
        data = {'ai_output': result}
        json_file_path = os.path.join(JSON_OUTPUT_DIR, f"{bib_ref}.json")
        if not os.path.exists(JSON_OUTPUT_DIR):
            os.makedirs(JSON_OUTPUT_DIR, exist_ok=True)
        with open(json_file_path, 'w') as json_file:
            json.dump(data, json_file, indent=4)

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

        # Update df with processed JSON data based on activity
        activity_selected = activity_var.get()

        for idx in row_indices:
            bib_ref = df.at[idx, 'bib_ref'] if 'bib_ref' in df.columns else f"row_{idx}"
            json_file_path = os.path.join(JSON_OUTPUT_DIR, f"{bib_ref}.json")
            if os.path.exists(json_file_path):
                try:
                    with open(json_file_path, "r") as f:
                        data = json.load(f)
                    # Update the row with the saved ai_output if available
                    if 'ai_output' in data:
                        # Activity-specific saving
                        if activity_selected == "abstract_filtering":
                            save_output_abstract_filtering(df, idx, data['ai_output'])
                        elif activity_selected == "analyse_pdf":
                            save_output_analyse_pdf(df, idx, data['ai_output'])
                except Exception as e:
                    print(f"Error reading JSON for {bib_ref}: {e}")

        df.to_excel(FILE_PATH, index=False)

        # Clean up JSON directory
        if os.path.exists(JSON_OUTPUT_DIR):
            try:
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

    # Initialize data based on the initially selected activity
    load_activity_data()

    root.mainloop()

if __name__ == "__main__":
    main()
