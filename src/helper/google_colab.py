import logging
import logging
import os
import sys
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from openai import OpenAI
from academic_paper_maker.setting.project_path import project_folder
from dotenv import load_dotenv
from openai import AuthenticationError, RateLimitError, APIConnectionError
from openai import OpenAI

from helper.combine_json import combine_json_files  # possible problem with import
from post_code_saviour.excel_to_bib import generate_bibtex
from research_filter.auto_llm import run_pipeline
from setting.project_path import project_folder

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')



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




def combine_methodology_json_colab(cfg: dict, model_name_method_extractor: str) -> None:
    """
    Combine individual JSON files from the methodology gap extractor into a single combined JSON file.

    Parameters:
        cfg (dict): Configuration dictionary with keys:
            - project_review
            - config_file
            - main_folder
            - methodology_gap_extractor_path
        model_name_method_extractor (str): Name of the model used in the methodology gap extractor step.
                                           This determines the subdirectory to read JSONs from.

    Raises:
        FileNotFoundError: If the input directory does not exist.

    Returns:
        None
    """

    # Load paths from registered project
    path_dict = project_folder(
        project_review=cfg['project_review'],
        config_file=cfg['config_file']
    )

    # Define input and output paths
    input_dir = Path(cfg['methodology_gap_extractor_path']) / model_name_method_extractor
    output_file = os.path.join(path_dict['main_folder'], 'combined_output.json')

    # Validate input directory
    if not input_dir.exists():
        raise FileNotFoundError(f"Input directory not found: {input_dir}")

    # Combine JSON files into one
    combine_json_files(
        input_directory=input_dir,
        output_file=output_file
    )

    print(f"✅ Combined JSON saved to: {output_file}")
