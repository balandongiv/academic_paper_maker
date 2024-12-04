from pdftitle import GetTitleParameters, get_title_from_file
from pdfminer.pdfparser import PDFParser
from pdfminer.pdfdocument import PDFDocument

def extract_title_from_pdf(pdf_path):
    """
    Extracts the title from a PDF file.

    :param pdf_path: Path to the PDF file.
    :return: Extracted title or an error message if extraction fails.
    """
    try:
        # Verify if the PDF is valid and accessible
        with open(pdf_path, "rb") as pdf_file:
            parser = PDFParser(pdf_file)
            document = PDFDocument(parser)
            if not document.is_extractable:
                raise Exception("PDF does not allow text extraction.")

        # Set up parameters for title extraction
        params = GetTitleParameters(
            use_document_information_dictionary=False,  # Use Document Info Dictionary
            use_metadata_stream=False,  # Prefer Metadata Stream
            page_number=1,  # Extract from the first page
            replace_missing_char=None,  # Handle missing characters
            translation_heuristic=False,  # No translation heuristic
            algorithm="max2",  # Use 'original' algorithm
            eliot_tfs="1"  # Not applicable to original algorithm
        )

        # Extract the title using pdftitle
        title = get_title_from_file(pdf_path, params)

        if title:
            return title
        else:
            return "No title found in the PDF."
    except Exception as e:
        return f"An error occurred: {e}"

if __name__ == "__main__":
    # Example usage: replace the path with the actual PDF file path for testing
    pdf_path = r"C:\Users\balan\IdeaProjects\academic_paper_maker\research_filter\pdf_store\A_new_hybrid_feature_extraction_method_for_partial_discharge_signals_classification.pdf"
    title_found = extract_title_from_pdf(pdf_path)
    print(title_found)
