import re
import pymupdf4llm

def extract_md_blocks(markdown_text):
    """
    Placeholder function to preprocess or clean markdown blocks.
    """
    return markdown_text

class MarkdownProcessor:
    def __init__(self, markdown_text):
        self.markdown_text = markdown_text
        self.headers = []

    def extract_headers(self):
        """
        Extract headers and subheaders from markdown text.
        """
        pattern = re.compile(r'^(#{1,6})\s+(.*)', re.MULTILINE)
        matches = pattern.findall(self.markdown_text)
        self.headers = [{"level": len(hashes), "title": title} for hashes, title in matches]
        return self.headers

    def display_headers(self):
        """
        Display headers in a structured hierarchical format.
        """
        for header in self.headers:
            indent = "  " * (header['level'] - 1)
            print(f"{indent}- {header['title']}")

    def extract_content_by_headers(self, header_list):
        """
        Extract content under specific headers.
        """
        content_dict = {}
        lines = self.markdown_text.splitlines()
        current_header = None
        collecting = False
        buffer = []

        for line in lines:
            header_match = re.match(r'^(#{1,6})\s+(.*)', line)
            if header_match:
                if collecting and current_header:
                    content_dict[current_header] = "\n".join(buffer).strip()
                    buffer = []
                current_header = header_match.group(2).strip()
                collecting = current_header in header_list
            elif collecting:
                buffer.append(line)

        if collecting and current_header:
            content_dict[current_header] = "\n".join(buffer).strip()
        return content_dict

# File processing and markdown extraction
filename = r'C:\Users\balan\IdeaProjects\academic_paper_maker\ragpdf\test2.pdf'
outname = filename.replace(".pdf", ".md")
md_text = pymupdf4llm.to_markdown(filename, page_chunks=False)
markdown_text = extract_md_blocks(md_text)

# Process markdown
processor = MarkdownProcessor(markdown_text)

# Extract and display headers
print("Extracted Headers:\n")
processor.extract_headers()
processor.display_headers()

# Extract content under specific headers
header_list = [
            "I. INTRODUCTION",
               # "IV. EXPERIMENTAL RESULTS AND DISCUSSION",
               # "B. Limitations"
               ]  # Modify this list as needed
print("\nExtracted Content:\n")
content = processor.extract_content_by_headers(header_list)
for header, body in content.items():
    print(f"### {header}\n{body}\n")
