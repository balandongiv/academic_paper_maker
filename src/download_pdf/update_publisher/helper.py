import os
import time
import logging

logger = logging.getLogger()

def is_file_stable(filepath, interval=2):
    size1 = os.path.getsize(filepath)
    time.sleep(interval)
    size2 = os.path.getsize(filepath)
    return size1 == size2

def wait_for_download_complete(download_folder, timeout=120):
    """
    Waits for a download to complete by monitoring the download folder for the absence of .part files.
    """
    end_time = time.time() + timeout
    start_time = time.time()

    while time.time() < end_time:
        elapsed_time = int(time.time() - start_time)
        remaining_time = int(timeout - elapsed_time)
        logger.debug(f"Waiting for download... Elapsed: {elapsed_time}s | Remaining: {remaining_time}s")

        # If no .part files found and at least one stable PDF exists, consider download done
        part_files = [f for f in os.listdir(download_folder) if f.endswith('.part')]
        files = os.listdir(download_folder)
        pdf_files = [os.path.join(download_folder, f) for f in files if f.endswith('.pdf')]

        if not part_files and pdf_files:
            if all(is_file_stable(f) for f in pdf_files):
                return True

        time.sleep(1)

    logger.warning("Download timeout or no matching file found.")
    return False
