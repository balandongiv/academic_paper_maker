import re
import re
import pymupdf4llm

import re

import re

class GeneralizedTextProcessor:
    def __init__(self, text):
        self.text = text
        self.headers = []
        self.content_by_headers = {}

    def normalize_header(self, header):
        """
        Normalize headers to ensure consistency (strip and uppercase).
        """
        return header.strip().upper()

    def extract_headers(self):
        """
        Extract headers and subheaders from the text. It detects:
        1. Roman numeral headers (I., II., etc.).
        2. Alphabetical headers (A., B., etc.).
        3. Fully capitalized section headers like ABSTRACT, REFERENCES, etc.
        """
        header_pattern = r"^(?P<header>([IVXLCDM]+\.)|([A-Z]\.)|([A-Z\s]+(?=:|\n)))\s*(?P<title>.+)?$"
        lines = self.text.split("\n")
        for line in lines:
            match = re.match(header_pattern, line.strip())
            if match:
                header = match.group("header") + (" " + match.group("title") if match.group("title") else "")
                self.headers.append(self.normalize_header(header))

    def extract_content_by_headers(self):
        """
        Extract content under each detected header.
        """
        current_header = None
        content_lines = []
        lines = self.text.split("\n")

        # Combine headers with their content
        for line in lines:
            header_match = re.match(r"^(?P<header>([IVXLCDM]+\.)|([A-Z]\.)|([A-Z\s]+(?=:|\n)))\s*(?P<title>.+)?$", line.strip())
            if header_match:
                # Save the content of the previous header
                if current_header:
                    self.content_by_headers[self.normalize_header(current_header)] = "\n".join(content_lines).strip()
                # Start a new header
                current_header = header_match.group("header") + (" " + header_match.group("title") if header_match.group("title") else "")
                content_lines = []
            elif current_header:
                # Accumulate content under the current header
                content_lines.append(line)

        # Save the final section
        if current_header:
            self.content_by_headers[self.normalize_header(current_header)] = "\n".join(content_lines).strip()

    def display_headers(self):
        """
        Display all extracted headers.
        """
        for header in self.headers:
            print(header)

    def display_content(self, headers_to_display):
        """
        Display the content under specified headers.
        :param headers_to_display: List of headers to display content for.
        """
        for header in headers_to_display:
            normalized_header = self.normalize_header(header)
            print(f"\n### {header}\n")
            print(self.content_by_headers.get(normalized_header, "Content not found under this header."))

# Example Usage



if __name__ == "__main__":
    # Load the markdown text
    # File processing and markdown extraction
    filename = r'C:\Users\balan\IdeaProjects\academic_paper_maker\ragpdf\test3.pdf'
    outname = filename.replace(".pdf", ".md")
    markdown_text = pymupdf4llm.to_markdown(filename, page_chunks=False)
    # Initialize processor
    processor = GeneralizedTextProcessor(markdown_text)

    # Extract headers and content
    processor.extract_headers()
    processor.extract_content_by_headers()

    # Display all headers
    print("Extracted Headers:\n")
    processor.display_headers()

    # Specify headers to display content for
    headers_to_display = [
        "ABSTRACT",
        "I. INTRODUCTION",
        "II. RELATED WORK",
        "III. PROPOSED METHODOLOGY",
        "IV. EXPERIMENTAL RESULTS AND ANALYSIS",
        "V. CONCLUSION",
        "REFERENCES"
    ]

    print("\nExtracted Content:\n")
    processor.display_content(headers_to_display)