import json
import os

# File paths
OUTLINE_FILE = r"/outline_eeg/outline_eeg_review.json"
ADDITION_FILE = r"/research_filter/addition_ref.json"
REPORT_FILE = r"/research_filter/migration_report.txt"

def load_json(file_path):
    """Load JSON from a file."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"The file '{file_path}' does not exist.")
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_json(data, file_path):
    """Save JSON to a file with indentation and UTF-8 encoding."""
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def save_report(report, file_path):
    """Save the migration report to a text file."""
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(report)

def merge_nested_json(target, additions):
    """
    Recursively merge 'additions' into 'target'.
    - If both 'target' and 'additions' are dicts, merge keys.
    - If both are lists, extend the target list.
    - Otherwise, override the target with additions.
    """
    if isinstance(target, dict) and isinstance(additions, dict):
        for key, value in additions.items():
            if key in target:
                target[key] = merge_nested_json(target[key], value)
            else:
                target[key] = value
        return target
    elif isinstance(target, list) and isinstance(additions, list):
        # Extend the list with any additional items
        target.extend(additions)
        return target
    else:
        # If they're not both dicts or lists, just replace
        return additions

def collect_references(data, ref_list=None):
    """
    Recursively collect all 'reference' field values
    from the JSON data into a Python set.
    """
    if ref_list is None:
        ref_list = set()

    if isinstance(data, dict):
        # If this dict has a 'reference' field, collect it
        if 'reference' in data:
            ref_list.add(data['reference'])
        # Recursively check all sub-items
        for value in data.values():
            collect_references(value, ref_list)

    elif isinstance(data, list):
        # Recursively collect references from each element
        for item in data:
            collect_references(item, ref_list)

    return ref_list

def generate_report(addition_refs, migrated_refs, left_behind_refs):
    """
    Generate a report as a formatted string.
    """
    report_lines = []
    report_lines.append("====== Migration Report ======\n")
    report_lines.append(f"Total References in 'addition_ref.json': {len(addition_refs)}\n")
    report_lines.append(f"References Successfully Migrated: {len(migrated_refs)}\n")
    if migrated_refs:
        report_lines.append("Migrated References:\n")
        report_lines.extend(f"  - {ref}\n" for ref in sorted(migrated_refs))

    report_lines.append(f"\nReferences Left Behind: {len(left_behind_refs)}\n")
    if left_behind_refs:
        report_lines.append("Left Behind References:\n")
        report_lines.extend(f"  - {ref}\n" for ref in sorted(left_behind_refs))

    return "".join(report_lines)

def main():
    try:
        # Load the existing outline and additional items
        outline_data = load_json(OUTLINE_FILE)
        addition_data = load_json(ADDITION_FILE)

        # Collect references from the addition_data BEFORE merging
        addition_refs = collect_references(addition_data)

        # Merge the additional references into the outline
        merged_data = merge_nested_json(outline_data, addition_data)

        # Collect references from the merged data
        merged_refs = collect_references(merged_data)

        # Determine which references were successfully migrated
        migrated_refs = addition_refs.intersection(merged_refs)

        # Determine which references might be left behind
        left_behind_refs = addition_refs.difference(merged_refs)

        # Save the updated outline back to the file
        save_json(merged_data, OUTLINE_FILE)

        # Generate the migration report
        report = generate_report(addition_refs, migrated_refs, left_behind_refs)

        # Save the report to a file
        save_report(report, REPORT_FILE)

        print(f"Merged additions successfully into '{OUTLINE_FILE}'.")
        print(f"Migration report saved to '{REPORT_FILE}'.")

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()
