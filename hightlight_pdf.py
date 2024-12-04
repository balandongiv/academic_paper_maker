import fitz  # PyMuPDF library

# Input and output file names
input_pdf = "test_highlight.pdf"
output_pdf = "highlighted_testx.pdf"

# Text to highlight
text_to_highlight = "Neurons and synapses in the brain are organized in graph structures, which can be considered a non-Euclidean space and do not satisfy translation invariance."

# Open the PDF file
pdf_document = fitz.open(input_pdf)

# Iterate through each page of the PDF
for page_num in range(len(pdf_document)):
    page = pdf_document[page_num]
    # Search for the text to highlight
    text_instances = page.search_for(text_to_highlight)

    # Highlight all instances of the found text
    for inst in text_instances:
        # Add a highlight annotation
        page.add_highlight_annot(inst)

# Save the modified PDF
pdf_document.save(output_pdf)
pdf_document.close()

print(f"The text has been successfully highlighted and saved to '{output_pdf}'.")
