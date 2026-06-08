Refactor and extend the existing ChatGPT automation script.

There is currently a script located at:

`tutorial/run_chatgpt_prompt.py`

This script may need to be refactored. Since it is currently inside the `tutorial` folder, move the important reusable logic into a proper application/module folder:

`apm/chatgpt_ui`

The goal is to create a robust script or API that can process a large CSV or database of literature-review entries using Selenium and ChatGPT.

## Development environment

The project root folder on this computer is:

`C:\Users\balan\My Drive (balandong@ums.edu.my)\iterate_literature_review`

The master CSV file is:

`complete_file_available_in_zotero.csv`

The prompt file is:

`promp_check_blink.md`

## Main objective

Create a system that reads entries from the master CSV or database, sends each entry to ChatGPT using Selenium, and saves the ChatGPT response as a JSON file.

There may be around 10,000 entries.

The work will be distributed across 3 different computers. These computers are synced through a shared folder, so the system must prevent multiple computers from processing the same row at the same time.

## Configuration

Create a YAML settings file so that important settings can be changed without modifying the code.

The YAML configuration should include at least:

```yaml
project_root: "C:/Users/balan/My Drive (balandong@ums.edu.my)/iterate_literature_review"

input:
  master_file: "complete_file_available_in_zotero.csv"
  prompt_file: "promp_check_blink.md"

output:
  json_output_folder: "chatgpt_outputs"

processing:
  batch_size: 10
  machine_id: "computer_1"
  status_column: "processing_status"
  lock_column: "processing_lock"
  processed_at_column: "processed_at"
  max_retries: 3

selenium:
  browser: "chrome"
  headless: false
  wait_seconds: 30
```

## Processing status requirements

The master CSV or database must contain a new status column that tracks each row.

Use the following statuses:

* `Yet To Process`
* `Already Processing`
* `In Progress`
* `Completed`
* `Failed`

The system should update the status before, during, and after processing each row.

Because multiple computers may access the same master file, implement a locking mechanism so that one computer does not process a row that is already being processed by another computer.

The system must handle the possibility that the master CSV or database is temporarily locked and cannot be read or written.

## Multi-computer processing requirements

Each computer should:

1. Read the YAML settings.
2. Open the master CSV or database.
3. Find rows with status `Yet To Process` or empty status.
4. Claim only a limited number of rows based on `batch_size`.
5. Mark those rows as `Already Processing` or `In Progress`.
6. Save the machine ID and timestamp.
7. Process each row using Selenium and ChatGPT.
8. Save the ChatGPT output as a JSON file.
9. Mark successfully processed rows as `Completed`.
10. Mark failed rows as `Failed`, with an error message if possible.

The system should avoid processing rows already claimed by another computer.

If possible, use a safer mechanism than directly editing the same CSV from multiple computers. Consider using SQLite instead of CSV for better locking and concurrency. If CSV must be used, implement file-level locking and retry logic.

## Output JSON requirements

For each processed row, save the output as a JSON file.

Use the DOI as the unique identifier, but convert the DOI into a hash before using it as the filename.

Example:

```text
10.1000/example-doi
```

should become something like:

```text
a94f2c8b9f4d3e2c.json
```

The JSON file should include:

```json
{
  "title": "Article title from the row",
  "doi": "Original DOI",
  "doi_hash": "Hashed DOI used as filename",
  "source_row": {
    "row_index": 123,
    "other_relevant_columns": "..."
  },
  "chatgpt_response": {
    "raw_text": "Raw response copied from ChatGPT",
    "parsed_json": {}
  },
  "processing_metadata": {
    "machine_id": "computer_1",
    "processed_at": "2026-06-08T12:00:00",
    "status": "Completed",
    "error": null
  }
}
```

Keep in mind that the ChatGPT response itself is expected to be JSON. The saved output file should still use JSON format, but the ChatGPT response should be stored inside a nested dictionary.

The system should attempt to parse the ChatGPT response as JSON. If parsing succeeds, store it in `chatgpt_response.parsed_json`. If parsing fails, store the original response in `chatgpt_response.raw_text` and record the parsing error in the metadata.

## Suggested module structure

Refactor the code into a maintainable structure such as:

```text
apm/
  chatgpt_ui/
    __init__.py
    config.py
    database.py
    csv_store.py
    locking.py
    selenium_client.py
    processor.py
    output_writer.py
    run_batch.py

tutorial/
  run_chatgpt_prompt.py
```

The tutorial script can remain as a simple example, but the actual reusable implementation should live inside `apm/chatgpt_ui`.

## Expected deliverables

Please implement:

1. A YAML configuration file.
2. Refactored reusable modules under `apm/chatgpt_ui`.
3. A batch processing script or CLI entry point.
4. CSV or database status tracking.
5. Multi-computer locking or row-claiming mechanism.
6. Selenium-based ChatGPT prompt submission.
7. JSON output saving using hashed DOI filenames.
8. Error handling and retry logic.
9. Clear logs showing which rows were processed, skipped, failed, or already claimed by another computer.

## Important design preference

Preferably use SQLite over CSV for the master processing database because SQLite handles locking and concurrent access more safely than a shared CSV file. 

execute the code once complete