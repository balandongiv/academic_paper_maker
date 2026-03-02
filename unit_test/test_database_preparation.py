import unittest
import os
import sys
import pandas as pd
import shutil

# Add 'src' to sys.path to allow running this test directly
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
src_path = os.path.join(project_root, "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from download_pdf.database_preparation import combine_data_to_excel

class TestDatabasePreparation(unittest.TestCase):
    def setUp(self):
        # Setup persistent output directory
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.test_dir = os.path.join(self.base_dir, "test_outputs")
        
        # Clean up previous run artifacts
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
            
        os.makedirs(self.test_dir, exist_ok=True)
        self.output_excel = os.path.join(self.test_dir, "combined_sample_results.xlsx")
        
        # Path to sample files
        self.sample_folder = os.path.join(project_root, "sample_file", "scopus")

    def test_simulate_step_7_with_sample_files(self):
        """
        Simulate Step 7 of the workflow using only the actual files in sample_file/scopus.
        No mock data is used.
        """
        if not os.path.exists(self.sample_folder):
            self.skipTest(f"Sample folder not found at: {self.sample_folder}")
            
        # Run master function using sample files
        combine_data_to_excel(self.sample_folder, self.output_excel)
        
        # Verify output
        self.assertTrue(os.path.exists(self.output_excel), "Excel file was not produced.")
        
        # Load produced Excel to verify content
        df_out = pd.read_excel(self.output_excel)
        
        print(f"\nSimulation complete.")
        print(f"Source folder: {self.sample_folder}")
        print(f"Output produced: {self.output_excel}")
        print(f"Total records combined: {len(df_out)}")
        
        self.assertGreater(len(df_out), 0, "The produced Excel file is empty.")

    def tearDown(self):
        print(f"\nFinal Excel file is available for inspection at: {self.output_excel}")

if __name__ == "__main__":
    unittest.main()