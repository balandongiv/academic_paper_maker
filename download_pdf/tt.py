import json
import logging
import os
import shutil
import sys
import time
import tkinter as tk
from tkinter import messagebox
def is_file_stable(filepath, interval=2):
    size1 = os.path.getsize(filepath)
    time.sleep(interval)
    size2 = os.path.getsize(filepath)
    return size1 == size2


download_folder = r'C:\Users\balan\OneDrive - ums.edu.my\research_related\0 eeg_trend_till24\eeg_review\temp_downloads\RamCrez-Moreno_M_2021_1735379147885'
# If no .part files found and at least one stable PDF exists, consider download done
part_files = [f for f in os.listdir(download_folder) if f.endswith('.part')]
files = os.listdir(download_folder)
pdf_files = [os.path.join(download_folder, f) for f in files if f.endswith('.pdf')]

if not part_files and pdf_files:
    if all(is_file_stable(f) for f in pdf_files):
        g=1
