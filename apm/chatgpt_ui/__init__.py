"""apm.chatgpt_ui — batch-process literature entries through ChatGPT via Selenium.

Public API
----------
config       : load_config, Config
database     : open_db, init_db, import_csv, claim_rows, update_status, get_stats
csv_store    : inspect_csv, validate_csv
locking      : file_lock
selenium_client : build_driver, ensure_logged_in, send_prompt_and_wait
processor    : process_row
output_writer: build_output, save_output

Entry point
-----------
python -m apm.chatgpt_ui.run_batch [--config PATH] [--import-only] [--stats]
"""
