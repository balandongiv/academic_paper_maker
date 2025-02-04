import json
import time
import os
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI

def initialize_client():
    """Load environment variables and initialize OpenAI client."""
    load_dotenv()
    return OpenAI()

def get_file_paths(file_path):
    """Get paths for batch JSON and results file in the same directory as input JSONL."""
    folder_path = os.path.dirname(file_path)
    return {
        "batch_info": os.path.join(folder_path, "batch_info.json"),
        "result_file": os.path.join(folder_path, "batch_job_results.jsonl")
    }

def save_json(data, file_path):
    """Save a dictionary as a JSON file."""
    with open(file_path, "w") as file:
        json.dump(data, file)
    print(f"Saved: {file_path}")

def load_json(file_path):
    """Load a JSON file if it exists."""
    if os.path.exists(file_path):
        with open(file_path, "r") as file:
            return json.load(file)
    return None

def create_batch(client, file_path, batch_info_path):
    """Create a batch, save its ID, and return it."""
    batch_file = client.files.create(file=open(file_path, "rb"), purpose="batch")

    batch_job = client.batches.create(input_file_id=batch_file.id,
                                      endpoint="/v1/chat/completions",
                                      completion_window="24h")

    save_json({"batch_id": batch_job.id}, batch_info_path)
    print(f"Created Batch ID: {batch_job.id}")
    print(f" The full details of the batch job is: {batch_job}")
    return batch_job.id

def check_batch_status(client, batch_id):
    """Retrieve and return the batch status with timestamp."""
    batch_job = client.batches.retrieve(batch_id)
    status = batch_job.status
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] Batch Status: {status}")
    return batch_job

def retrieve_and_process_results(client, batch_job, result_file_path):
    """Retrieve batch results, save to a JSONL file, and return loaded results."""
    if not batch_job.output_file_id:
        print("No output file found. Batch may not have completed successfully.")
        return []

    result_content = client.files.content(batch_job.output_file_id).content
    with open(result_file_path, 'wb') as file:
        file.write(result_content)
    print(f"Results saved to {result_file_path}")

    return [json.loads(line.strip()) for line in open(result_file_path, 'r', encoding='utf-8')]

def sample_results(results, n=5):
    """Display a sample of batch results."""
    print(f"\nShowing first {n} results:")
    for res in results[:n]:
        task_id = res.get('custom_id', 'Unknown')
        response_text = res.get('response', {}).get('body', {}).get('choices', [{}])[0].get('message', {}).get('content', "No response")
        print(f"Task ID: {task_id} | Response: {response_text[:100]}...\n")

def process_batch(client, file_path):
    """Manages batch creation, status monitoring, and result retrieval."""
    paths = get_file_paths(file_path)
    batch_info = load_json(paths["batch_info"])
    batch_id = batch_info.get("batch_id") if batch_info else None

    if not batch_id:
        print("No existing batch found. Creating a new batch...")
        batch_id = create_batch(client, file_path, paths["batch_info"])
    else:
        print(f"Using existing batch ID: {batch_id}")

    while True:
        batch_job = check_batch_status(client, batch_id)
        if batch_job.status in ["completed", "failed"]:
            if batch_job.status == "completed":
                results = retrieve_and_process_results(client, batch_job, paths["result_file"])
                sample_results(results)
            os.remove(paths["batch_info"])  # Cleanup batch_info.json
            break
        time.sleep(60)

def main():
    client = initialize_client()
    file_path = r'G:\My Drive\research_related\0 eeg_trend_till24\eeg_review\methodology_gap_extractor\json_output\tasks.jsonl'
    process_batch(client, file_path)

if __name__ == "__main__":
    main()
