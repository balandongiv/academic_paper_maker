
'''

When use the agent_name="section_sorter", sometime, the section ID is not matched with the master json file.
This make it difficult to compile the childrent json(i.e., all the json from llm) into master file

This code use different strategy to match the section ID with the master json file.
'''
import os
import json
import re
import logging
import difflib

# Try to import scikit-learn for NLP matching.
try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
except ImportError:
    TfidfVectorizer = None
    cosine_similarity = None
    logging.warning("scikit-learn not found. NLP matching fallback will be disabled.")

# -------------------------
# Setup Logging
# -------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)

# -------------------------
# Utility Functions
# -------------------------
def load_json(file_path):
    """
    Load JSON data from a file.

    :param file_path: Path to the JSON file.
    :return: Parsed JSON data or None if an error occurred.
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"Error loading JSON file {file_path}: {e}")
        return None

def save_json(data, file_path):
    """
    Save data to a JSON file.

    :param data: Data to save.
    :param file_path: Path where the JSON file will be written.
    """
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        logging.info(f"JSON saved to {file_path}")
    except Exception as e:
        logging.error(f"Error saving JSON to {file_path}: {e}")

def ensure_directory(directory):
    """
    Ensure that a directory exists. Create it if necessary.

    :param directory: Directory path.
    """
    if not os.path.exists(directory):
        os.makedirs(directory)
        logging.info(f"Created directory: {directory}")

# -------------------------
# Section Processing Functions
# -------------------------
def normalize_section_id(section_id):
    """
    Normalize a section identifier by removing leading digits, dots, hyphens, and whitespace,
    then converting to lowercase.

    :param section_id: Original section id (e.g., "2.1 Deep Learning").
    :return: Normalized section id (e.g., "deep learning").
    """
    if not section_id:
        return ""
    normalized = re.sub(r'^\s*[\d\.\-\s]*', '', section_id)
    return normalized.strip().lower()

def composite_section_text(section):
    """
    Create a composite text from a section's "section_id", "title", and "description".
    This helps with robust matching.

    :param section: Section dictionary.
    :return: Composite text string.
    """
    parts = []
    if "section_id" in section:
        parts.append(section["section_id"])
    if "title" in section:
        parts.append(section["title"])
    if "description" in section:
        if isinstance(section["description"], list):
            parts.extend(section["description"])
        elif isinstance(section["description"], str):
            parts.append(section["description"])
    return " ".join(parts).strip().lower()

def collect_sections(data, collected=None):
    """
    Recursively traverse a nested JSON structure and collect all sections that contain a "section_id".

    :param data: JSON data (dict or list).
    :param collected: List to accumulate sections.
    :return: List of sections (dicts).
    """
    if collected is None:
        collected = []
    if isinstance(data, dict):
        if "section_id" in data:
            collected.append(data)
        for value in data.values():
            if isinstance(value, list):
                for item in value:
                    collect_sections(item, collected)
            elif isinstance(value, dict):
                collect_sections(value, collected)
    elif isinstance(data, list):
        for item in data:
            collect_sections(item, collected)
    return collected

def build_master_mapping(master_sections):
    """
    Build a mapping from normalized section id to a list of master sections.

    :param master_sections: List of sections from the master JSON.
    :return: Dictionary with normalized section ids as keys.
    """
    master_mapping = {}
    for sec in master_sections:
        sec_id = sec.get("section_id", "")
        norm_id = normalize_section_id(sec_id)
        if norm_id:
            master_mapping.setdefault(norm_id, []).append(sec)
    return master_mapping

def fallback_match_section(norm_sec_id, sec, master_mapping, master_sections, nlp_threshold):
    """
    Apply fallback matching strategies to associate an input section with a master section.

    Fallback strategies include:
      1. Fuzzy matching with a lower cutoff.
      2. NLP-based matching using composite texts (if scikit-learn is available).

    :param norm_sec_id: Normalized section id from the input section.
    :param sec: The input section.
    :param master_mapping: Mapping from normalized ids to master sections.
    :param master_sections: List of all master sections.
    :param nlp_threshold: Threshold score for NLP matching.
    :return: Tuple (matched_master_section or None, fallback_info dict).
    """
    fallback_info = {
        "original_section_id": sec.get("section_id", ""),
        "original_title": sec.get("title", ""),
        "fallback_candidates": [],
        "nlp_candidate": None,
        "used_strategy": None
    }

    # Fallback 1: Fuzzy matching with a lower cutoff.
    possible_matches_low = difflib.get_close_matches(norm_sec_id, list(master_mapping.keys()), n=3, cutoff=0.4)
    fallback_info["fallback_candidates"] = possible_matches_low
    if possible_matches_low:
        best_candidate = possible_matches_low[0]
        score = difflib.SequenceMatcher(None, norm_sec_id, best_candidate).ratio()
        if score > 0.8:
            fallback_info["used_strategy"] = f"Low cutoff fuzzy matching with score {score:.2f}"
            logging.info(f"Fallback fuzzy matching: '{sec.get('section_id')}' matched to '{best_candidate}' with score {score:.2f}")
            return master_mapping[best_candidate][0], fallback_info

    # Fallback 2: NLP-based matching (if scikit-learn is available).
    if TfidfVectorizer and cosine_similarity:
        query_text = composite_section_text(sec)
        candidate_texts = []
        candidate_mapping = {}
        for m_sec in master_sections:
            candidate_text = composite_section_text(m_sec)
            candidate_texts.append(candidate_text)
            candidate_mapping[candidate_text] = m_sec

        if candidate_texts:
            try:
                vectorizer = TfidfVectorizer().fit([query_text] + candidate_texts)
                query_vec = vectorizer.transform([query_text])
                candidate_vecs = vectorizer.transform(candidate_texts)
                scores = cosine_similarity(query_vec, candidate_vecs)[0]
                best_index = scores.argmax()
                best_score = scores[best_index]
                if best_score > nlp_threshold:
                    best_candidate_text = candidate_texts[best_index]
                    fallback_info["nlp_candidate"] = {"candidate_text": best_candidate_text, "score": best_score}
                    fallback_info["used_strategy"] = f"NLP cosine similarity matching with score {best_score:.2f}"
                    logging.info(f"Fallback NLP matching: '{sec.get('section_id')}' matched with score {best_score:.2f}")
                    return candidate_mapping[best_candidate_text], fallback_info
            except Exception as e:
                logging.error("Error during NLP matching: " + str(e))

    fallback_info["used_strategy"] = "No candidate found via fallback strategies"
    return None, fallback_info

def match_and_update_section(sec, master_mapping, master_sections, unmatched_sections, disambig_threshold, nlp_threshold):
    """
    Match an input section to a master section and update its references.

    The function first tries direct mapping using the normalized section id. If multiple
    candidates are found, composite text similarity is used for disambiguation. If no match
    is found, fallback matching strategies are applied. Unmatched sections are recorded.

    :param sec: Input section from an input JSON.
    :param master_mapping: Mapping of normalized section ids to master sections.
    :param master_sections: List of all master sections.
    :param unmatched_sections: List to record sections that could not be matched.
    :param disambig_threshold: Similarity threshold for disambiguation.
    :param nlp_threshold: Score threshold for NLP-based matching.
    :return: Number of references added.
    """
    refs_added = 0
    if "references" in sec and isinstance(sec["references"], list) and sec["references"]:
        original_sec_id = sec.get("section_id", "")
        norm_sec_id = normalize_section_id(original_sec_id)
        master_sec = None
        fallback_details = None

        # Direct mapping by normalized section id.
        candidates = master_mapping.get(norm_sec_id, [])
        if candidates:
            if len(candidates) == 1:
                master_sec = candidates[0]
            else:
                # Use composite text to disambiguate among multiple candidates.
                input_comp_text = composite_section_text(sec)
                best_candidate = None
                best_score = 0
                for candidate in candidates:
                    candidate_text = composite_section_text(candidate)
                    score = difflib.SequenceMatcher(None, input_comp_text, candidate_text).ratio()
                    if score > best_score:
                        best_score = score
                        best_candidate = candidate
                if best_score > disambig_threshold:
                    master_sec = best_candidate
                    logging.info(f"Disambiguated multiple master sections for '{original_sec_id}' with score {best_score:.2f}")

        # Apply fallback matching strategies if no direct match.
        if master_sec is None:
            master_sec, fallback_details = fallback_match_section(norm_sec_id, sec, master_mapping, master_sections, nlp_threshold)

        if master_sec:
            # Ensure the master section has a references list.
            if "references" not in master_sec or not isinstance(master_sec["references"], list):
                master_sec["references"] = []
            # Append new references if not already present.
            for ref in sec["references"]:
                if isinstance(ref, dict):
                    bibtext = ref.get("bibtext")
                    exists = any(
                        isinstance(existing, dict) and existing.get("bibtext") == bibtext
                        for existing in master_sec["references"]
                    )
                    if not exists:
                        master_sec["references"].append(ref)
                        refs_added += 1
                else:
                    logging.warning(f"Reference is not a dict in section '{original_sec_id}': {ref}")
        else:
            # Record unmatched section with detailed fallback info.
            unmatched_sections.append({
                "source_file": sec.get("source_file", "unknown"),
                "original_section_id": original_sec_id,
                "original_title": sec.get("title", ""),
                "composite_text": composite_section_text(sec),
                "references": sec["references"],
                "fallback_info": fallback_details or {"used_strategy": "No candidate found", "fallback_candidates": []}
            })
    return refs_added

def process_input_file(json_file, master_mapping, master_sections, unmatched_sections, disambig_threshold, nlp_threshold):
    """
    Process a single JSON file by scanning for sections and updating master references.

    :param json_file: Path to the input JSON file.
    :param master_mapping: Mapping of normalized section ids to master sections.
    :param master_sections: List of all master sections.
    :param unmatched_sections: List to record unmatched sections.
    :param disambig_threshold: Similarity threshold for disambiguation.
    :param nlp_threshold: Threshold for NLP-based matching.
    :return: Number of references added from this file.
    """
    refs_added = 0
    logging.info(f"Processing file: {json_file}")
    data = load_json(json_file)
    if data is None:
        return 0
    sections = collect_sections(data)
    # Add source file information to each section (for debugging purposes).
    for sec in sections:
        sec["source_file"] = json_file
        refs_added += match_and_update_section(sec, master_mapping, master_sections, unmatched_sections, disambig_threshold, nlp_threshold)
    return refs_added

def process_all_files(input_folder, master_mapping, master_sections, disambig_threshold, nlp_threshold):
    """
    Process all JSON files in the input folder.

    :param input_folder: Folder containing input JSON files.
    :param master_mapping: Mapping of normalized section ids to master sections.
    :param master_sections: List of all master sections.
    :param disambig_threshold: Similarity threshold for disambiguation.
    :param nlp_threshold: Threshold for NLP-based matching.
    :return: Tuple (total references added, list of unmatched sections).
    """
    total_refs_added = 0
    unmatched_sections = []
    json_files = [
        os.path.join(input_folder, f)
        for f in os.listdir(input_folder)
        if f.lower().endswith('.json')
    ]
    logging.info(f"Found {len(json_files)} JSON files in folder '{input_folder}'.")
    for json_file in json_files:
        total_refs_added += process_input_file(json_file, master_mapping, master_sections, unmatched_sections, disambig_threshold, nlp_threshold)
    return total_refs_added, unmatched_sections

def update_master_json(master_json_path, input_folder, output_json_path, unmatched_output_path, disambig_threshold, nlp_threshold):
    """
    Update the master JSON with new references from input JSON files.

    This function loads the master JSON, collects and maps its sections,
    processes each input file to update references, and then writes the updated
    master JSON and unmatched sections to disk.

    :param master_json_path: Path to the master JSON file.
    :param input_folder: Folder containing input JSON files.
    :param output_json_path: File path where the updated master JSON will be saved.
    :param unmatched_output_path: File path for saving unmatched section details.
    :param disambig_threshold: Similarity threshold for disambiguation.
    :param nlp_threshold: Threshold for NLP-based matching.
    """
    master_data = load_json(master_json_path)
    if master_data is None:
        logging.error("Master JSON could not be loaded.")
        return

    master_sections = collect_sections(master_data)
    master_mapping = build_master_mapping(master_sections)
    total_master = sum(len(v) for v in master_mapping.values())
    logging.info(f"Collected {total_master} master sections across {len(master_mapping)} normalized keys.")

    total_refs_added, unmatched_sections = process_all_files(input_folder, master_mapping, master_sections, disambig_threshold, nlp_threshold)
    logging.info(f"Total references added: {total_refs_added}")

    # Save unmatched sections if any.
    if unmatched_sections:
        save_json(unmatched_sections, unmatched_output_path)
        logging.warning(f"{len(unmatched_sections)} section(s) could not be matched. Details saved to {unmatched_output_path}.")

    # Save updated master JSON.
    save_json(master_data, output_json_path)

# -------------------------
# Main Execution
# -------------------------
if __name__ == "__main__":
    # Define constants and configuration.
    INPUT_FOLDER = r"G:\My Drive\research_related\0 eeg_trend_till24\eeg_review\section_sorter\json_output\gemini-2.0-flash-thinking-exp-01-21"
    MASTER_JSON_PATH = r"/outline_eeg/outline_eeg_bare.json"

    # Output folder (both final JSON and unmatched sections will be saved here)
    OUTPUT_FOLDER = os.path.join(INPUT_FOLDER ,"process_combine")
    ensure_directory(OUTPUT_FOLDER)

    OUTPUT_JSON_FILENAME = "outline_eeg_appended.json"
    UNMATCHED_JSON_FILENAME = "unmatched_references.json"
    OUTPUT_JSON_PATH = os.path.join(OUTPUT_FOLDER, OUTPUT_JSON_FILENAME)
    UNMATCHED_OUTPUT_PATH = os.path.join(OUTPUT_FOLDER, UNMATCHED_JSON_FILENAME)

    # Matching thresholds (adjust these values as needed)
    DISAMBIGUATION_THRESHOLD = 0.9 # For composite text matching when multiple candidates exist.
    NLP_THRESHOLD = 0.9          # For NLP cosine similarity matching (only used if scikit-learn is available).

    update_master_json(
        MASTER_JSON_PATH,
        INPUT_FOLDER,
        OUTPUT_JSON_PATH,
        UNMATCHED_OUTPUT_PATH,
        DISAMBIGUATION_THRESHOLD,
        NLP_THRESHOLD
    )
