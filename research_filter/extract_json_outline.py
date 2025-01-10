import json
import os

def convert_section_id_to_filename(section_id: str) -> str:
    """
    Convert a section_id like '2.4.1 Data Augmentation Techniques'
    into '2_4_1__Data_AugmentationTechniques'.
    """
    parts = section_id.split(' ', 1)  # split into numeric vs. text portion
    if len(parts) == 2:
        numeric_part, text_part = parts
        numeric_part = numeric_part.replace('.', '_')  # 2.4.1 -> 2_4_1
        text_part = text_part.replace(' ', '_')        # spaces -> underscores
        return f"{numeric_part}__{text_part}"
    else:
        # If there's no space to split on, just do a global replace
        return section_id.replace('.', '_').replace(' ', '_')


def extract_level_info(d: dict) -> dict:
    """
    Extract only 'title', 'section_id', and 'description' from this dictionary.
    If 'description' is missing, default to 'not available'.
    """
    info = {}
    if "title" in d:
        info["title"] = d["title"]
    if "section_id" in d:
        info["section_id"] = d["section_id"]
    # Default to 'not available' if description is missing
    info["description"] = d.get("description", "not available")
    return info


def save_deepest_sections(
        obj,
        parent_chain=None
):
    """
    Recursively traverse the JSON structure. When a 'deepest' section is found:
      - it has a 'section_id'
      - it does NOT have nested 'subsections', 'sections', or 'methods'
    We save that node, plus all the accumulated parent info in 'parent_chain'.
    """
    if parent_chain is None:
        parent_chain = []

    # Check if obj is a dictionary
    if isinstance(obj, dict):
        sub_keys = ["subsections", "sections", "methods"]
        # Do we have any of these keys?
        has_sublevel = any(key in obj for key in sub_keys)

        if not has_sublevel and "section_id" in obj:
            # This is a deepest section
            leaf_section = dict(obj)  # copy
            # Attach all parent levels
            leaf_section["all_upper_levels"] = parent_chain

            # Convert this section_id to a file name
            filename_root = convert_section_id_to_filename(leaf_section["section_id"])
            filename = f"{filename_root}.json"
            filepath = os.path.join("sub_outline", filename)  # store in sub_outline folder

            # Save
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(leaf_section, f, indent=2, ensure_ascii=False)
            print(f"Saved deepest section to {filepath}")

        else:
            # Not a leaf, so we recurse deeper
            # First, gather info for the current level
            current_info = extract_level_info(obj)
            # Create the updated chain (this level gets appended)
            new_parent_chain = parent_chain + [current_info] if current_info else parent_chain

            # Go through sub-level arrays
            for key in sub_keys:
                if key in obj and isinstance(obj[key], list):
                    for item in obj[key]:
                        save_deepest_sections(item, parent_chain=new_parent_chain)

    # If obj is a list, recurse on each item
    elif isinstance(obj, list):
        for item in obj:
            save_deepest_sections(item, parent_chain=parent_chain)


def main():
    # 1. Set your input JSON path
    input_path = r"C:\Users\rpb\OneDrive - ums.edu.my\Code Development\academic_paper_maker\research_filter\outline_eeg_review.json"

    # 2. Load the JSON
    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 3. Make sure the output folder 'sub_outline' exists
    if not os.path.exists("sub_outline"):
        os.makedirs("sub_outline")

    # 4. Recursively traverse and save the deepest sections
    save_deepest_sections(data)


if __name__ == '__main__':
    main()
