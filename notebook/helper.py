import logging
import os
import sys
import warnings
from os.path import join
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from openai import OpenAI, AuthenticationError, RateLimitError, APIConnectionError

from helper.combine_json import combine_json_files
# from execution_guide_colab import main_folder
from post_code_saviour.excel_to_bib import generate_bibtex
from research_filter.auto_llm import run_pipeline
from setting.project_path import project_folder


# Path to the directory where "research_filter" lives



def build_project_config(
        project_name,
        yaml_path_abstract=None,
        yaml_path_methodology=None,
        base_dir=None
):
    """
    Constructs a configuration dictionary for initializing a research project.

    In this step, you'll register the **main project folder**, so the system knows
    where to store and retrieve all files related to your project.

    This setup automatically creates a structured folder system under your specified
    `main_folder`, and stores the configuration in a central JSON file. This ensures
    your projects remain organized, especially when working with multiple studies or datasets.

    Parameters
    ----------
    project_name : str
        The name of the project or review (e.g., "wafer"). Used to organize files and folders.

    yaml_path_abstract : str, optional
        Optional path to the YAML file for abstract filtering logic.
        Defaults to: ./research_filter/agent/abstract_check.yaml

    yaml_path_methodology : str, optional
        Optional path to the YAML file for methodology filtering logic.
        Defaults to: ./research_filter/agent/agent_ml.yaml

    base_dir : str, optional
        Base directory where the project folder structure will be created.
        **Warning:** If not provided, the current working directory is used. This can lead
        to confusion when running notebooks from different locations. It is strongly
        recommended to explicitly define this value to ensure consistent file paths.

    Returns
    -------
    dict
        A configuration dictionary containing resolved paths and project metadata. Keys include:

        - 'project_review'
        - 'env_path'
        - 'main_folder'
        - 'project_root'
        - 'yaml_path_abstract'
        - 'yaml_path_methodology'
        - 'config_file'
        - 'methodology_gap_extractor_path'

    Examples
    --------
    >>> cfg = build_project_config("wafer")

    >>> cfg = build_project_config(
            "wafer",
            yaml_path_abstract="D:/configs/my_abstract.yaml",
            yaml_path_methodology="D:/configs/my_method.yaml",
            base_dir="D:/my_projects"
        )
    """

    if base_dir is None:
        warnings.warn(
            "No 'base_dir' provided. Falling back to the current working directory.\n"
            "This may lead to inconsistent paths if notebooks are run from different locations.\n"
            "It is highly recommended to explicitly provide a base_dir.",
            stacklevel=2
        )
        base_dir = os.getcwd()

    main_folder = join(base_dir, "project_files")
    default_yaml_path = join(base_dir, "research_filter", "agent")

    yaml_path_abstract = yaml_path_abstract or join(default_yaml_path, "abstract_check.yaml")
    yaml_path_methodology = yaml_path_methodology or join(default_yaml_path, "agent_ml.yaml")

    return {
        "project_review": project_name,
        "env_path": join(main_folder, ".env"),
        "main_folder": main_folder,
        "project_root": join(main_folder, "database"),
        "yaml_path_abstract": yaml_path_abstract,
        "yaml_path_methodology": yaml_path_methodology,
        "config_file": join(main_folder, "project_folders.json"),
        "methodology_gap_extractor_path": join(main_folder, "methodology_gap_extractor", "json_output"),
    }


def generate_bibtex_from_excel_colab(cfg: dict) -> None:
    """
    Generate a BibTeX file from a filtered Excel database.

    Parameters:
        cfg (dict): Configuration dictionary containing at least:
            - project_review (str)

    Returns:
        None
    """
    # Load project paths
    path_dic = project_folder(project_review=cfg['project_review'])
    main_folder = path_dic['main_folder']

    # Define input and output paths
    input_excel = os.path.join(main_folder, 'database', 'combined_filtered.xlsx')
    output_bib = os.path.join(main_folder, 'database', 'filtered_output.bib')

    # Load the filtered Excel file
    df = pd.read_excel(input_excel)

    # Generate BibTeX file
    generate_bibtex(df, output_file=output_bib)

    print(f"✅ BibTeX file saved to: {output_bib}")


def create_env_file(env_path, openai_api_key=None, gemini_api_key=None):
    """
    Creates a .env file with placeholders or provided API keys.

    Parameters:
    - env_path (str): Full path to the .env file (e.g., "/content/my_project/.env").
    - openai_api_key (str, optional): OpenAI API key (e.g., "sk-...").
    - gemini_api_key (str, optional): Gemini (Google AI) API key.
    """
    lines = [
        "# Paste your API keys below.",
        "# OpenAI example: OPENAI_API_KEY=sk-...",
        "# Gemini (Google AI) example: GEMINI_API_KEY=your-google-api-key",
        "",
    ]

    lines.append(f"OPENAI_API_KEY={openai_api_key}" if openai_api_key else "# OPENAI_API_KEY=")
    lines.append(f"GEMINI_API_KEY={gemini_api_key}" if gemini_api_key else "# GEMINI_API_KEY=")

    try:
        with open(env_path, "w") as f:
            f.write("\n".join(lines) + "\n")
        print(f"✅ `.env` file created at: {env_path}")
        print("👉 In Colab, click the folder icon on the left, go to the appropriate folder, right-click `.env`, and choose 'Edit' to enter your keys.")
    except Exception as e:
        print(f"❌ Failed to create `.env`: {e}")




def test_openai_connection(model: str = "gpt-4o") -> None:
    """
    Loads the OpenAI API key from a .env file and sends a test message
    to verify the connection to the OpenAI Chat Completion API.

    Parameters:
        model (str): The model name to test (default: "gpt-4o")

    Expected Output:
        - ✅ Confirmation that the API call succeeded
        - 🤖 The assistant's response to "Hello, what is 2 + 2?"
    """

    # 🔄 Load environment variables from the .env file
    load_dotenv()

    # 🔑 Fetch the OpenAI API key
    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        raise ValueError("❌ OPENAI_API_KEY not found. Please make sure it is set in your .env file.")

    # ✅ Initialize the OpenAI client
    client = OpenAI(api_key=api_key)

    try:
        # 📤 Send a test prompt to the model
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Hello, what is 2 + 2?"}
            ]
        )

        # 🟢 Print the result if successful
        print("✅ API call successful!")
        print("🤖 Response:", response.choices[0].message.content)

    except AuthenticationError:
        print("❌ Authentication failed. Please check your OPENAI_API_KEY.")
    except RateLimitError:
        print("⚠️ Rate limit exceeded. Wait and try again later.")
    except APIConnectionError:
        print("📡 Network issue or OpenAI server unavailable. Check your connection.")
    # except InvalidRequestError as e:
    #     print(f"🚫 Invalid request to the API: {e}")
    except Exception as e:
        print(f"❗ An unexpected error occurred: {e}")




def run_llm_filtering_pipeline_colab(
        model_name: str,
        cfg: dict,
        placeholders: dict
) -> None:
    """
    Run the LLM-based abstract filtering pipeline in Google Colab.

    Parameters:
        model_name (str): The LLM to use (e.g., "gpt-4o", "gpt-4o-mini")
        cfg (dict): Configuration dictionary with keys:
            - project_review
            - config_file
            - project_root
            - yaml_path
            - main_folder
        placeholders (dict): Dictionary with placeholder text for the LLM (e.g., topic and context)

    Returns:
        None
    """
    try:
        logging.info("Initializing LLM filtering pipeline...")

        # Ensure project_root is in sys.path
        if cfg['project_root'] not in sys.path:
            sys.path.append(cfg['project_root'])

        # Get project paths
        path_dic = project_folder(
            project_review=cfg['project_review'],
            config_file=cfg['config_file']
        )
        main_folder = path_dic['main_folder']
        csv_path = path_dic['database_path']

        # Agent configuration
        agentic_setting = {
            "agent_name": "abstract_filter",
            "column_name": "abstract_filter",
            "yaml_path": cfg['yaml_path'],
            "model_name": model_name
        }

        # Output folders
        methodology_json_folder = os.path.join(main_folder, agentic_setting['agent_name'], 'json_output')
        multiple_runs_folder = os.path.join(main_folder, agentic_setting['agent_name'], 'multiple_runs_folder')
        final_cross_check_folder = os.path.join(main_folder, agentic_setting['agent_name'], 'final_cross_check_folder')

        # Processing configuration
        process_setup = {
            'batch_process': False,
            'manual_paste_llm': False,
            'iterative_confirmation': False,
            'overwrite_csv': True,
            'cross_check_enabled': False,
            'cross_check_runs': 3,
            'cross_check_agent_name': 'agent_cross_check',
            'cleanup_json': False
        }

        # Run the LLM-based filtering
        run_pipeline(
            agentic_setting,
            process_setup,
            placeholders=placeholders,
            csv_path=csv_path,
            main_folder=main_folder,
            methodology_json_folder=methodology_json_folder,
            multiple_runs_folder=multiple_runs_folder,
            final_cross_check_folder=final_cross_check_folder,
        )

        logging.info("✅ LLM filtering pipeline completed successfully.")

    except Exception as e:
        logging.error(f"❌ An error occurred while running the LLM filtering pipeline: {e}")



def run_abstract_filtering_colab(model_name: str, placeholders: dict, cfg: dict) -> None:
    """
    Run the abstract filtering pipeline using a specified LLM in a Colab environment.

    Parameters:
        model_name (str): The LLM to use (e.g., "gpt-4o", "gpt-4o-mini")
        placeholders (dict): Dictionary with keys like "topic" and "topic_context"
        cfg (dict): Configuration dictionary containing:
            - project_review
            - config_file
            - project_root
            - yaml_path

    Returns:
        None
    """
    try:
        logging.info("🚀 Starting abstract filtering pipeline...")

        # Ensure project root is available
        if cfg['project_root'] not in sys.path:
            sys.path.append(cfg['project_root'])

        # Load project folder structure
        path_dic = project_folder(
            project_review=cfg['project_review'],
            config_file=cfg['config_file']
        )
        main_folder = path_dic['main_folder']
        csv_path = path_dic['database_path']

        # Agent configuration
        agentic_setting = {
            "agent_name": "abstract_filter",
            "column_name": "abstract_filter",
            "yaml_path": cfg['yaml_path_abstract'],
            "model_name": model_name
        }

        # Define output folders
        methodology_json_folder = os.path.join(main_folder, agentic_setting['agent_name'], 'json_output')
        multiple_runs_folder = os.path.join(main_folder, agentic_setting['agent_name'], 'multiple_runs_folder')
        final_cross_check_folder = os.path.join(main_folder, agentic_setting['agent_name'], 'final_cross_check_folder')

        # Runtime options
        process_setup = {
            'batch_process': False,
            'manual_paste_llm': False,
            'iterative_confirmation': False,
            'overwrite_csv': True,
            'cross_check_enabled': False,
            'cross_check_runs': 3,
            'cross_check_agent_name': 'agent_cross_check',
            'cleanup_json': False
        }

        # Run the pipeline
        run_pipeline(
            agentic_setting,
            process_setup,
            placeholders=placeholders,
            csv_path=csv_path,
            main_folder=main_folder,
            methodology_json_folder=methodology_json_folder,
            multiple_runs_folder=multiple_runs_folder,
            final_cross_check_folder=final_cross_check_folder,
        )

        logging.info("✅ Abstract filtering completed successfully.")

    except Exception as e:
        logging.error(f"❌ An error occurred during the abstract filtering process: {e}")



def run_methodology_extraction_colab(
        model_name_method_extractor: str,
        agent_name: str,
        placeholders: dict,
        cfg: dict
) -> None:
    """
    Run the methodology gap extraction pipeline using a specified model and agent in Colab.

    Parameters:
        model_name_method_extractor (str): LLM model to use (e.g., "gpt-4o-mini")
        agent_name (str): Name of the agent configuration (e.g., "methodology_gap_extractor")
        placeholders (dict): Dictionary with keys like "topic" and "topic_context"
        cfg (dict): Configuration dictionary with keys:
            - project_review
            - config_file
            - yaml_path

    Returns:
        None
    """
    try:
        logging.info("🚀 Starting methodology gap extraction pipeline...")

        # Load project folder paths
        path_dic = project_folder(
            project_review=cfg['project_review'],
            config_file=cfg['config_file']
        )
        main_folder = path_dic['main_folder']
        csv_path = path_dic['database_path']

        # Set up the agent
        agentic_setting = {
            "agent_name": agent_name,
            "column_name": "methodology_gap",
            "yaml_path": cfg['yaml_path_methodology'],
            # "yaml_path": r"C:\Users\balan\IdeaProjects\academic_paper_maker\research_filter\agent\agent_ml.yaml",
            "model_name": model_name_method_extractor
        }

        # Define output folders
        methodology_json_folder = os.path.join(
            main_folder, agent_name, 'json_output', model_name_method_extractor
        )
        multiple_runs_folder = os.path.join(main_folder, agent_name, 'multiple_runs_folder')
        final_cross_check_folder = os.path.join(main_folder, agent_name, 'final_cross_check_folder')

        # Runtime options
        process_setup = {
            'batch_process': False,
            'manual_paste_llm': False,
            'iterative_confirmation': False,
            'overwrite_csv': True,
            'cross_check_enabled': False,
            'cross_check_runs': 3,
            'cross_check_agent_name': 'agent_cross_check',
            'cleanup_json': False,
            'used_abstract': True  # Always enable abstract fallback
        }

        # Run the pipeline
        run_pipeline(
            agentic_setting,
            process_setup,
            placeholders=placeholders,
            csv_path=csv_path,
            main_folder=main_folder,
            methodology_json_folder=methodology_json_folder,
            multiple_runs_folder=multiple_runs_folder,
            final_cross_check_folder=final_cross_check_folder,
        )

        logging.info("✅ Methodology extraction completed successfully.")

    except Exception as e:
        logging.error(f"❌ An error occurred during the methodology extraction: {e}")


def sanitize_filename(name):
    """
    Sanitizes a string to be safe for use as a filename on all OSes, especially Windows.
    Removes or replaces invalid characters.
    """
    # Replace any invalid Windows filename character with underscore
    import re

    return re.sub(r'[<>:"/\\|?*]', '_', name)

def combine_methodology_output_colab(model_name_method_extractor: str, cfg: dict) -> None:
    """
    Combine individual JSON files from the methodology gap extractor into a single combined JSON.

    Parameters:
        model_name_method_extractor (str): Name of the model used in the methodology gap extractor step
        cfg (dict): Configuration dictionary containing:
            - project_review
            - config_file
            - methodology_gap_extractor_path

    Returns:
        None
    """
    try:
        logging.info("🔄 Starting to combine methodology gap JSON files...")

        # Load project paths
        path_dict = project_folder(
            project_review=cfg['project_review'],
            config_file=cfg['config_file']
        )

        # Define input and output paths
        input_dir = Path(cfg['methodology_gap_extractor_path']) / model_name_method_extractor
        # output_file = os.path.join(path_dict['main_folder'], f'methodology_extraction_{model_name_method_extractor}_combined.json')
        safe_model_name = sanitize_filename(model_name_method_extractor)

        output_file = os.path.join(
            path_dict['main_folder'],
            f"methodology_extraction_{safe_model_name}_combined.json"
        )

        # Validate input directory
        if not input_dir.exists():
            raise FileNotFoundError(f"❌ Input directory not found: {input_dir}")

        # Combine JSONs into one file
        combine_json_files(
            input_directory=input_dir,
            output_file=output_file
        )

        logging.info(f"✅ Combined JSON saved to: {output_file}")

    except Exception as e:
        logging.error(f"❌ Failed to combine JSON files: {e}")
