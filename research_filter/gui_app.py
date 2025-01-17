import json
import os
import shutil
import tkinter as tk
from tkinter import messagebox, ttk
from typing import List, Callable, Dict, Tuple, Any

import pandas as pd
import pyperclip

from abstract_filtering import save_output_abstract_filtering, save_output_analyse_pdf
from config import (
    DEBUG,
    ACTIVITY_NOW,
    DEFAULT_ACTIVITY,
    FILE_PATH,
    YAML_PATH,
    JSON_OUTPUT_DIR,
    validation_functions,
    placeholders
)
from data_processing import load_activity_data, load_row_data
from research_filter.agent_helper import load_yaml

def update_status(message: str, status_message: tk.StringVar):
    """Update the dynamic status message."""
    status_message.set(message)

def display_current_row(
        row_indices: List[int],
        current_index: int,
        df: pd.DataFrame,
        activity_var: tk.StringVar,
        config: Dict,
        placeholders: Dict,
        combined_text_box: tk.Text,
        json_text_box: tk.Text,
        root: tk.Tk,
        status_message: tk.StringVar
) -> Dict[str, Any]:
    """Display the data for the current row and return cached row data."""
    if not row_indices or current_index >= len(row_indices):
        return {}

    idx = row_indices[current_index]
    combined_string, bib_ref, system_prompt = load_row_data(idx, df, activity_var, config, placeholders)

    combined_text_box.delete("1.0", tk.END)
    combined_text_box.insert("1.0", combined_string)
    pyperclip.copy(combined_string)
    root.title(f"Processing: {bib_ref} - Row Index: {current_index + 1} of {len(row_indices)}")

    json_text_box.delete("1.0", tk.END)
    update_status("Ready for JSON input.", status_message)

    return {
        "idx": idx,
        "bib_ref": bib_ref,
        "combined_string": combined_string,
        "system_prompt": system_prompt,
    }

def save_and_next(
        row_indices: List[int],
        current_index: int,
        df: pd.DataFrame,
        activity_var: tk.StringVar,
        json_text_box: tk.Text,
        combined_text_box: tk.Text,
        config: Dict,
        placeholders: Dict,
        status_message: tk.StringVar,
        cached_row_data: Dict[str, Any],
        root: tk.Tk
) -> Tuple[Dict[str, Any], int]:
    """Validate and save the current row data, then move to the next."""
    if not cached_row_data:
        messagebox.showerror("Error", "No row data available to save.")
        return {}, current_index

    if not row_indices or current_index >= len(row_indices):
        messagebox.showinfo("Done", "No more rows to process.")
        update_status("All rows processed.", status_message)
        return {}, current_index

    update_status("Validating and saving data...", status_message)
    user_json_input = json_text_box.get("1.0", tk.END).strip()

    if not user_json_input:
        messagebox.showerror("Error", "No JSON input provided.")
        update_status("Validation failed: No JSON input.", status_message)
        return cached_row_data, current_index

    bib_ref = cached_row_data["bib_ref"]
    system_prompt = cached_row_data["system_prompt"]
    activity_selected = activity_var.get()

    validate_function = validation_functions.get(activity_selected)
    if not validate_function:
        messagebox.showerror("Error", f"No validation function defined for activity: {activity_selected}")
        update_status("Validation failed: Undefined activity.", status_message)
        return cached_row_data, current_index

    valid, result = validate_function(user_json_input, system_prompt)
    if not valid:
        messagebox.showerror("Validation Error", f"Error in JSON:\n\n{result}")
        update_status("Validation failed: Invalid JSON.", status_message)
        return cached_row_data, current_index

    json_file_path = os.path.join(JSON_OUTPUT_DIR, f"{bib_ref}.json")
    os.makedirs(JSON_OUTPUT_DIR, exist_ok=True)
    with open(json_file_path, 'w') as json_file:
        json.dump({activity_selected: result}, json_file, indent=4)

    if activity_selected == "abstract_filtering":
        save_output_abstract_filtering(df, cached_row_data["idx"], result)
    elif activity_selected == "analyse_pdf":
        save_output_analyse_pdf(df, cached_row_data["idx"], result)

    FILE_PATH=os.path.join(FILE_PATH, 'eeg_test_simple_with_bibtex_v1.xlsx')
    df.to_excel(FILE_PATH, index=False)
    update_status(f"Data for {bib_ref} saved successfully.", status_message)
    json_text_box.delete("1.0", tk.END)

    if current_index < len(row_indices) - 1:
        current_index += 1
        new_cached_data = display_current_row(
            row_indices, current_index, df, activity_var, config, placeholders,
            combined_text_box, json_text_box, root, status_message
        )

        return new_cached_data, current_index
    else:
        messagebox.showinfo("Done", "No more rows to process.")
        update_status("All rows processed.", status_message)
        return {}, current_index

def integrate_temp_json_files(df: pd.DataFrame, activity_selected: str):
    """Integrate leftover temp JSON files into the Excel database."""
    TEMP_JSON_DIR = os.path.join(JSON_OUTPUT_DIR, f"{activity_selected}_temp")
    if not os.path.exists(TEMP_JSON_DIR):
        return

    bib_ref_to_idx = {df.at[i, 'bibtex'] if 'bibtex' in df.columns else f"row_{i}": i for i in range(len(df))}

    for filename in os.listdir(TEMP_JSON_DIR):
        if filename.endswith(".json"):
            bib_ref = filename[:-5]
            idx = bib_ref_to_idx.get(bib_ref)
            if idx is None:
                print(f"Warning: bib_ref {bib_ref} not found in DataFrame. Skipping.")
                continue

            json_file_path = os.path.join(TEMP_JSON_DIR, filename)
            try:
                with open(json_file_path, "r") as f:
                    data = json.load(f)

                if activity_selected in data:
                    if activity_selected == "abstract_filtering":
                        save_output_abstract_filtering(df, idx, data[activity_selected])
                    elif activity_selected == "analyse_pdf":
                        save_output_analyse_pdf(df, idx, data[activity_selected])

                os.remove(json_file_path)

            except Exception as e:
                print(f"Error processing {bib_ref}: {e}")

    df.to_excel(FILE_PATH, index=False)
    shutil.rmtree(TEMP_JSON_DIR)

def on_exit(row_indices: List[int], df: pd.DataFrame, activity_var: tk.StringVar, root: tk.Tk, status_message: tk.StringVar):
    """Save all processed data and exit."""
    update_status("Finalizing and saving data...", status_message)
    activity_selected = activity_var.get()

    bib_ref_to_idx = {df.at[i, 'bibtex'] if 'bibtex' in df.columns else f"row_{i}": i for i in row_indices}

    if os.path.exists(JSON_OUTPUT_DIR):
        for filename in os.listdir(JSON_OUTPUT_DIR):
            if filename.endswith(".json"):
                bib_ref = filename[:-5]
                idx = bib_ref_to_idx.get(bib_ref)
                if idx is not None:
                    json_file_path = os.path.join(JSON_OUTPUT_DIR, filename)
                    try:
                        with open(json_file_path, "r") as f:
                            data = json.load(f)
                        if activity_selected in data:
                            if activity_selected == "abstract_filtering":
                                save_output_abstract_filtering(df, idx, data[activity_selected])
                            elif activity_selected == "analyse_pdf":
                                save_output_analyse_pdf(df, idx, data[activity_selected])
                    except Exception as e:
                        print(f"Error processing {bib_ref}: {e}")

    df.to_excel(FILE_PATH, index=False)

    if os.path.exists(JSON_OUTPUT_DIR):
        for filename in os.listdir(JSON_OUTPUT_DIR):
            if filename.endswith(".json"):
                try:
                    os.remove(os.path.join(JSON_OUTPUT_DIR, filename))
                except Exception as e:
                    print(f"Error removing file {filename}: {e}")

    update_status("Data updated and saved. Exiting...", status_message)
    messagebox.showinfo("Exit", "Data updated and saved back to Excel.")
    root.destroy()

def manage_activity_change(
        df: pd.DataFrame,
        activity_var: tk.StringVar,
        row_indices: List[int],
        current_index: int,
        config: Dict,
        placeholders: Dict,
        combined_text_box: tk.Text,
        json_text_box: tk.Text,
        root: tk.Tk,
        status_message: tk.StringVar,
        cached_row_data: Dict[str, Any]
) -> Tuple[List[int], int, Dict[str, Any]]:
    """Handles the change of activity selection."""

    # Save current work before switching
    if cached_row_data:
        save_and_next(
            row_indices, current_index, df, activity_var, json_text_box, combined_text_box,
            config, placeholders, status_message, cached_row_data, root
        )


    new_activity = activity_var.get()
    update_status(f"Activity changed to: {new_activity}", status_message)

    # Re-filter rows based on new activity
    new_row_indices = load_activity_data(df, activity_var, 0, lambda msg: update_status(msg, status_message))

    if not new_row_indices:
        messagebox.showinfo("No Rows", f"No rows to process for {new_activity}. All up-to-date.")
        return [], 0, {}

    # Reset to first row of new activity
    new_current_index = 0
    new_cached_row_data = display_current_row(
        new_row_indices, new_current_index, df, activity_var, config, placeholders,
        combined_text_box, json_text_box, root, status_message
    )

    # Clear the JSON text box to avoid confusion
    json_text_box.delete("1.0", tk.END)

    return new_row_indices, new_current_index, new_cached_row_data



def main():
    df = pd.read_excel(FILE_PATH)
    df['ai_output'] = df.get('ai_output', "")
    df['pdf_analysis_output'] = df.get('pdf_analysis_output', "")

    config = load_yaml(YAML_PATH)
    activity_selected = ACTIVITY_NOW if DEBUG else DEFAULT_ACTIVITY
    integrate_temp_json_files(df, activity_selected)

    df = pd.read_excel(FILE_PATH)
    df = df[df['ai_output'] == 'relevance']
    df.reset_index(drop=True, inplace=True)

    root = tk.Tk()
    root.title("Academic Tool")
    status_message = tk.StringVar(value="Ready to start.")
    activity_var = tk.StringVar(value=activity_selected)
    current_index = 0
    cached_row_data = {}  # Initialize cached_row_data


    # Correct placement of row_indices initialization
    row_indices = load_activity_data(df, activity_var, current_index, lambda msg: update_status(msg, status_message))

    if not row_indices:
        messagebox.showinfo("No Rows", "No rows to process. All up-to-date.")
        root.destroy()
        return

    # Ensure row_indices is defined before this call

    activity_dropdown = ttk.Combobox(root, textvariable=activity_var, values=["abstract_filtering", "analyse_pdf"], state="readonly")
    activity_dropdown.pack(pady=5)

    combined_text_box = tk.Text(root, height=10, width=70, wrap='word')
    combined_text_box.pack(pady=5)

    json_text_box = tk.Text(root, height=10, width=70)
    json_text_box.pack(pady=5)

    status_label = tk.Label(root, textvariable=status_message, fg="blue")
    status_label.pack(pady=10)

    cached_row_data = display_current_row(
        row_indices, current_index, df, activity_var, config, placeholders,
        combined_text_box, json_text_box, root, status_message
    )

    def on_save_and_next():
        nonlocal cached_row_data, current_index, row_indices
        new_data, new_index = save_and_next(
            row_indices, current_index, df, activity_var, json_text_box, combined_text_box,
            config, placeholders, status_message, cached_row_data, root
        )
        cached_row_data = new_data
        current_index = new_index

    def on_exit_app():
        on_exit(row_indices, df, activity_var, root, status_message)


    def on_activity_change():
        nonlocal row_indices, current_index, cached_row_data
        row_indices, current_index, cached_row_data = manage_activity_change(
            df, activity_var, row_indices, current_index, config, placeholders,
            combined_text_box, json_text_box, root, status_message, cached_row_data
        )

    # Bind the activity change event to the dropdown
    activity_dropdown.bind("<<ComboboxSelected>>", lambda event: on_activity_change())

    tk.Button(root, text="Save & Next", command=on_save_and_next).pack(pady=5)
    tk.Button(root, text="Exit", command=on_exit_app).pack(pady=5)

    root.mainloop()

if __name__ == "__main__":
    main()