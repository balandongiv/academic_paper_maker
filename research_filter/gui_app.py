import json
import os
import shutil
import tkinter as tk
from tkinter import messagebox, ttk

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


def update_status(message, status_message):
    """Update the dynamic status message."""
    status_message.set(message)


def display_current_row(
        row_indices, current_index, df, activity_var, config, placeholders,
        combined_text_box, json_text_box, root, status_message
):
    """Display the data for the current row and return cached row data."""
    if not row_indices or current_index >= len(row_indices):
        return None

    idx = row_indices[current_index]
    combined_string, bib_ref, system_prompt = load_row_data(idx, df, activity_var, config, placeholders)

    combined_text_box.delete("1.0", tk.END)
    combined_text_box.insert("1.0", combined_string)
    pyperclip.copy(combined_string)
    root.title(f"Processing: {bib_ref}")

    json_text_box.delete("1.0", tk.END)
    update_status("Ready for JSON input.", status_message)

    return {
        "idx": idx,
        "bib_ref": bib_ref,
        "combined_string": combined_string,
        "system_prompt": system_prompt,
    }


def save_and_next(
        row_indices, current_index, df, activity_var, json_text_box, combined_text_box,
        config, placeholders, status_message, cached_row_data, root
):
    """Validate and save the current row data, then move to the next."""
    if not row_indices or current_index >= len(row_indices):
        return cached_row_data, current_index

    update_status("Validating and saving data...", status_message)
    user_json_input = json_text_box.get("1.0", tk.END).strip()

    if not user_json_input:
        messagebox.showerror("Error", "No JSON input provided.")
        update_status("Validation failed: No JSON input.", status_message)
        return cached_row_data, current_index

    # Use cached data
    bib_ref = cached_row_data["bib_ref"]
    system_prompt = cached_row_data["system_prompt"]
    activity_selected = activity_var.get()

    # Validate JSON input
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

    # Save JSON file
    json_file_path = os.path.join(JSON_OUTPUT_DIR, f"{bib_ref}.json")
    os.makedirs(JSON_OUTPUT_DIR, exist_ok=True)
    with open(json_file_path, 'w') as json_file:
        json.dump({activity_selected: result}, json_file, indent=4)

    # Apply changes to the DataFrame immediately to avoid reprocessing
    if activity_selected == "abstract_filtering":
        save_output_abstract_filtering(df, cached_row_data["idx"], result)
    elif activity_selected == "analyse_pdf":
        save_output_analyse_pdf(df, cached_row_data["idx"], result)

    # Save DataFrame after updating this row
    df.to_excel(FILE_PATH, index=False)

    update_status(f"Data for {bib_ref} saved successfully. Moving to the next row...", status_message)
    json_text_box.delete("1.0", tk.END)

    # Move to the next row
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
        return None, current_index


def integrate_temp_json_files(df, activity_selected):
    """Integrate leftover temp JSON files (if any) into the Excel database before continuing
       and remove them after integration so they won't affect subsequent processes."""
    # Temporary directory aligned with the activity
    TEMP_JSON_DIR = os.path.join(JSON_OUTPUT_DIR, f"{activity_selected}_temp")
    print(f"Checking for temp JSON directory: {TEMP_JSON_DIR}")

    if not os.path.exists(TEMP_JSON_DIR):
        print("No temp JSON directory found.")
        return  # No leftover temp directory

    # Create a mapping from bib_ref to index for quick lookups
    if 'bibtex' in df.columns:
        bib_ref_to_idx = {df.at[i, 'bibtex']: i for i in range(len(df))}
    else:
        bib_ref_to_idx = {f"row_{i}": i for i in range(len(df))}

    # Iterate over all JSON files in the temp directory
    for filename in os.listdir(TEMP_JSON_DIR):
        if filename.endswith(".json"):
            bib_ref = filename[:-5]  # Remove the .json extension
            idx = bib_ref_to_idx.get(bib_ref)

            if idx is None:
                print(f"Warning: bib_ref {bib_ref} not found in DataFrame. Skipping.")
                continue

            json_file_path = os.path.join(TEMP_JSON_DIR, filename)
            print(f"Integrating {json_file_path} into Excel for {bib_ref}...")

            try:
                with open(json_file_path, "r") as f:
                    data = json.load(f)

                # Determine which save function to use
                if activity_selected == "abstract_filtering" and 'abstract_filtering' in data:
                    save_output_abstract_filtering(df, idx, data['abstract_filtering'])
                elif activity_selected == "analyse_pdf" and 'analyse_pdf' in data:
                    save_output_analyse_pdf(df, idx, data['analyse_pdf'])
                else:
                    print(f"No valid data found in {json_file_path} for activity {activity_selected}. Skipping.")

                # Remove the integrated JSON file immediately
                os.remove(json_file_path)
                print(f"Removed integrated file: {json_file_path}")

            except Exception as e:
                print(f"Error reading JSON for {bib_ref} from temp: {e}")

    # After integrating all, save the updated DataFrame
    df.to_excel(FILE_PATH, index=False)
    print("DataFrame updated and saved after integrating temp files.")

    # Remove the temp directory
    try:
        shutil.rmtree(TEMP_JSON_DIR)
        print(f"Removed temp JSON directory: {TEMP_JSON_DIR}")
    except Exception as e:
        print(f"An error occurred removing temp folder: {e}")


def on_exit(row_indices, df, activity_var, root, status_message):
    """Save all processed data and exit the application."""
    update_status("Finalizing and saving data...", status_message)

    activity_selected = activity_var.get()

    if 'bibtex' in df.columns:
        bib_ref_to_idx = {df.at[i, 'bibtex']: i for i in row_indices}
    else:
        bib_ref_to_idx = {f"row_{i}": i for i in row_indices}

    # Iterate over all JSON files in the output directory (if any remain)
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
                        if activity_selected == "abstract_filtering" and activity_selected in data:
                            save_output_abstract_filtering(df, idx, data[activity_selected])
                        elif activity_selected == "analyse_pdf" and activity_selected in data:
                            save_output_analyse_pdf(df, idx, data[activity_selected])
                    except Exception as e:
                        print(f"Error reading JSON for {bib_ref}: {e}")

    # Save updated DataFrame
    df.to_excel(FILE_PATH, index=False)

    # Remove any leftover JSON files
    if os.path.exists(JSON_OUTPUT_DIR):
        for filename in os.listdir(JSON_OUTPUT_DIR):
            file_path = os.path.join(JSON_OUTPUT_DIR, filename)
            if os.path.isfile(file_path) and filename.endswith(".json"):
                try:
                    os.remove(file_path)
                except Exception as e:
                    print(f"An error occurred: {e}")

    update_status("Data updated and saved. Exiting...", status_message)
    messagebox.showinfo("Exit", "Data updated and saved back to Excel.")
    root.destroy()


def main():
    # Load Excel file
    df = pd.read_excel(FILE_PATH)
    df['ai_output'] = df.get('ai_output', "")
    df['pdf_analysis_output'] = df.get('pdf_analysis_output', "")

    # Load configuration
    config = load_yaml(YAML_PATH)

    # Determine activity before GUI
    activity_selected = ACTIVITY_NOW if DEBUG else DEFAULT_ACTIVITY

    # First, integrate any leftover temp JSON files to ensure database is up-to-date
    integrate_temp_json_files(df, activity_selected)

    # Reload the DataFrame after integration (to reflect updates and ensure row filtering works correctly)
    df = pd.read_excel(FILE_PATH)

    # Initialize GUI
    root = tk.Tk()
    root.title("Academic Tool")
    status_message = tk.StringVar(value="Ready to start.")
    activity_var = tk.StringVar(value=activity_selected)

    current_index = 0

    activity_dropdown = ttk.Combobox(root, textvariable=activity_var, values=["abstract_filtering", "analyse_pdf"], state="readonly")
    activity_dropdown.pack(pady=5)

    combined_text_box = tk.Text(root, height=10, width=70, wrap='word')
    combined_text_box.pack(pady=5)

    json_text_box = tk.Text(root, height=10, width=70)
    json_text_box.pack(pady=5)

    status_label = tk.Label(root, textvariable=status_message, fg="blue")
    status_label.pack(pady=10)

    # Load row indices and initial row data
    # Ensure that load_activity_data is designed such that rows with integrated JSON data are not re-selected.
    row_indices = load_activity_data(df, activity_var, current_index, lambda msg: update_status(msg, status_message))

    if not row_indices:
        # No rows to process
        messagebox.showinfo("No Rows", "No rows to process. All up-to-date.")
        root.destroy()
        return

    cached_row_data = display_current_row(
        row_indices, current_index, df, activity_var, config, placeholders,
        combined_text_box, json_text_box, root, status_message
    )

    def on_save_and_next():
        nonlocal cached_row_data, current_index
        new_data, new_index = save_and_next(
            row_indices, current_index, df, activity_var, json_text_box, combined_text_box,
            config, placeholders, status_message, cached_row_data, root
        )
        cached_row_data = new_data
        current_index = new_index

    def on_exit_app():
        on_exit(row_indices, df, activity_var, root, status_message)

    tk.Button(root, text="Save & Next", command=on_save_and_next).pack(pady=5)
    tk.Button(root, text="Exit", command=on_exit_app).pack(pady=5)

    root.mainloop()


if __name__ == "__main__":
    main()
