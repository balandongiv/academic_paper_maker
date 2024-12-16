 import os
import json
import tkinter as tk
from tkinter import messagebox
import pandas as pd
import pyperclip

from config import (
    FILE_PATH,
    JSON_FOLDER,
    DEBUG,
    activity_now,
    agent_name,
    get_system_prompt,
    validate_json_data,
    append_error_to_system_prompt
)

def save_back_to_excel(df):
    # Save back to Excel
    df.to_excel(FILE_PATH, index=False)

class AbstractFilteringTool:
    def __init__(self, master):
        self.master = master
        self.master.title("Abstract Filtering Tool")

        # Load DataFrame
        self.df = pd.read_excel(FILE_PATH)

        # Ensure 'ai_related' column exists for storing processed JSON data at the end
        if 'ai_related' not in self.df.columns:
            self.df['ai_related'] = ""

        # Filter rows for processing (those not processed yet)
        rows_to_process = self.df[self.df['ai_related'].isna() | (self.df['ai_related'] == '')].copy()

        if rows_to_process.empty:
            messagebox.showinfo("Info", "No rows left to process.")
            self.master.destroy()
            return

        self.row_indices = rows_to_process.index.tolist()

        # Obtain the system prompt based on the current activity
        self.system_prompt = get_system_prompt(activity_now)

        self.current_index = 0
        self.user_json_data_cache = {}

        # Build GUI
        self.build_gui()
        self.display_current_row()

    def build_gui(self):
        instruction_text = (
            "Instructions:\n"
            "1. The combined prompt+abstract is copied to the clipboard.\n"
            "2. Process it externally and paste the resulting JSON below.\n"
            "3. Click 'Save JSON' to validate and save for this row.\n"
            "4. Use 'Next Row' to continue or 'Exit' to finish."
        )
        self.instruction_label = tk.Label(self.master, text=instruction_text)
        self.instruction_label.pack(pady=5)

        self.combined_text_label = tk.Label(self.master, text="Combined Prompt + Abstract:")
        self.combined_text_label.pack()

        self.combined_text_box = tk.Text(self.master, height=10, width=70, wrap='word')
        self.combined_text_box.pack(pady=5)

        self.json_input_label = tk.Label(self.master, text="Paste JSON here:")
        self.json_input_label.pack()

        self.json_text_box = tk.Text(self.master, height=10, width=70)
        self.json_text_box.pack(pady=5)

        self.save_button = tk.Button(self.master, text="Save JSON for This Row", command=self.save_user_json)
        self.save_button.pack(pady=5)

        self.next_button = tk.Button(self.master, text="Next Row", command=self.next_row)
        self.next_button.pack(pady=5)

        self.exit_button = tk.Button(self.master, text="Exit", command=self.on_exit)
        self.exit_button.pack(pady=5)

    def load_row_data(self):
        idx = self.row_indices[self.current_index]
        row = self.df.loc[idx]
        abstract = row.get('Abstract', '')
        bib_ref = row.get('bib_ref', f"row_{idx}")
        combined_string = f"{self.system_prompt}\n\n{abstract}"
        return idx, bib_ref, combined_string

    def display_current_row(self):
        idx, bib_ref, combined_string = self.load_row_data()
        self.combined_text_box.delete("1.0", tk.END)
        self.combined_text_box.insert(tk.END, combined_string)
        # Copy to clipboard
        pyperclip.copy(combined_string)
        self.master.title(f"Processing: {bib_ref}")

        # Clear the JSON box for fresh input
        self.json_text_box.delete("1.0", tk.END)

    def save_user_json(self):
        # Save the JSON for the current row after validation
        user_json_input = self.json_text_box.get("1.0", tk.END).strip()
        if not user_json_input:
            messagebox.showerror("Error", "No JSON input provided.")
            return

        # Try to parse JSON
        try:
            user_json_data = json.loads(user_json_input)
        except json.JSONDecodeError:
            messagebox.showerror("Error", "Invalid JSON input. Please try again.")
            return

        # Validate JSON data using Pydantic
        is_valid, errors = validate_json_data(user_json_data)
        if not is_valid:
            # Append error to system prompt so user can copy it into LLM for correction
            error_msg = f"Validation errors: {errors}"
            self.system_prompt = append_error_to_system_prompt(self.system_prompt, error_msg)
            messagebox.showerror("Validation Error", f"JSON validation failed.\n\n{errors}\n\nSystem prompt updated with error message. Please retry.")
            return

        # If valid, save JSON
        idx, bib_ref, _ = self.load_row_data()
        json_file_path = os.path.join(JSON_FOLDER, f"{bib_ref}.json")
        with open(json_file_path, 'w') as json_file:
            json.dump(user_json_data, json_file, indent=4)
        messagebox.showinfo("Success", f"JSON saved for {bib_ref}.")
        # Store in cache
        self.user_json_data_cache[idx] = user_json_data

    def next_row(self):
        # Attempt to save current row JSON before moving on
        # If validation fails, user stays on this row
        current_idx = self.row_indices[self.current_index]
        user_json_input = self.json_text_box.get("1.0", tk.END).strip()
        if user_json_input:
            # Try saving
            # If save fails due to validation, return early
            prev_len = len(self.user_json_data_cache)
            self.save_user_json()
            if len(self.user_json_data_cache) == prev_len:
                # Save didn't happen due to an error, don't move on
                return

        if self.current_index < len(self.row_indices) - 1:
            self.current_index += 1
            self.display_current_row()
        else:
            messagebox.showinfo("Done", "No more rows to process.")

    def on_exit(self):
        # On exit, update df with processed JSON data and remove JSON files
        for idx in self.row_indices:
            bib_ref = self.df.at[idx, 'bib_ref'] if 'bib_ref' in self.df.columns else f"row_{idx}"
            json_file_path = os.path.join(JSON_FOLDER, f"{bib_ref}.json")
            if os.path.exists(json_file_path):
                try:
                    with open(json_file_path, 'r') as f:
                        data = json.load(f)
                    # Convert data to a string or store as-is
                    self.df.at[idx, 'ai_related'] = json.dumps(data)
                    os.remove(json_file_path)
                except Exception as e:
                    print(f"Error reading JSON for {bib_ref}: {e}")

        # Save back to Excel
        save_back_to_excel(self.df)

        # Optionally clean up the JSON folder if empty
        if os.path.exists(JSON_FOLDER) and not os.listdir(JSON_FOLDER):
            os.rmdir(JSON_FOLDER)

        messagebox.showinfo("Exit", "Data updated and saved back to Excel.")
        self.master.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = AbstractFilteringTool(root)
    root.mainloop()
