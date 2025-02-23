import argparse
import json
import os
import nltk

from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_community.retrievers import BM25Retriever
from langchain_core.documents import Document
from nltk.tokenize import word_tokenize

def str_to_bool(value):
    """Convert a string to a boolean (case insensitive)."""
    if isinstance(value, bool):
        return value
    if value.lower() in {"true", "yes", "1"}:
        return True
    elif value.lower() in {"false", "no", "0"}:
        return False
    else:
        raise argparse.ArgumentTypeError("Boolean value expected (true/false).")

def load_documents(directory):
    """Loads JSON documents from a specified directory."""
    loader = DirectoryLoader(directory, glob="**/*.json", loader_cls=TextLoader)
    try:
        documents = loader.load()
        print(f"Successfully loaded {len(documents)} documents.")
        return documents
    except Exception as e:
        print(f"An error occurred while loading documents: {e}")
        return []

def process_documents(documents):
    """Processes the loaded documents by extracting filename and bibtex metadata."""
    processed_documents = []
    for doc in documents:
        source = doc.metadata.get("source", "Unknown")
        filename = os.path.basename(source)
        doc.metadata["filename"] = filename

        # Convert page content to JSON and extract bibtex if available
        try:
            content_dict = json.loads(doc.page_content)
            bibtex = content_dict.get("bibtex", "")
        except json.JSONDecodeError:
            bibtex = ""
        doc.metadata["bibtex"] = bibtex

        processed_documents.append(Document(page_content=doc.page_content, metadata=doc.metadata))
    return processed_documents

def create_retriever(documents, k):
    """Creates a BM25Retriever from the processed documents using the provided k."""
    return BM25Retriever.from_documents(documents, k=k, preprocess_func=word_tokenize)

def retrieve_documents(retriever, query, manual_filtering, required_bibtex):
    """
    Retrieves documents for the given query and applies optional manual filtering.

    Parameters:
        retriever: The BM25Retriever instance.
        query (str): The query string.
        manual_filtering (bool): If True, perform additional filtering.
        required_bibtex (set): Set of bibtex values to filter by if manual_filtering is enabled.

    Returns:
        List of Document objects.
    """
    retrieved_docs = retriever.invoke(query)
    if manual_filtering:
        retrieved_docs = [
            doc for doc in retrieved_docs
            if doc.metadata.get("bibtex") in required_bibtex
        ]
    return retrieved_docs

def display_results(query, docs):
    """Displays the query and the details of each document found."""
    print(f"\nQuery: {query}")
    print(f"Found {len(docs)} relevant document(s):\n")
    for i, doc in enumerate(docs, start=1):
        print(f"Document {i}:")
        print(f"Filename: {doc.metadata.get('filename', 'N/A')}")
        print(f"Source: {doc.metadata.get('source', 'N/A')}")
        print(f"BibTeX: {doc.metadata.get('bibtex', 'N/A')}")
        snippet = doc.page_content[:300].replace("\n", " ")
        print(f"Content Snippet: {snippet}...")
        print("-" * 80)

def main(k, json_directory, manual_filtering, required_bibtex):
    """Main function to run the document retrieval and filtering."""
    nltk.download("punkt")

    # Load and process documents
    documents = load_documents(json_directory)
    if not documents:
        print("No documents were loaded. Exiting.")
        return
    processed_docs = process_documents(documents)

    # Create the BM25 retriever
    retriever = create_retriever(processed_docs, k)

    # Define a query
    query = "get filename with bibtext Ahmadi_A_2021 and Ahn_S_2016"

    # Retrieve and manually filter documents if needed
    retrieved_docs = retrieve_documents(retriever, query, manual_filtering, required_bibtex)

    # Display the results
    display_results(query, retrieved_docs)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="BM25 retrieval script with optional manual filtering."
    )
    parser.add_argument(
        "--k", type=int, default=2,
        help="BM25 parameter: the number of documents to consider."
    )
    parser.add_argument(
        "--json_dir", type=str,
        default=r"G:\My Drive\research_related\0 eeg_trend_till24\eeg_review\methodology_gap_extractor\json_output\test",
        help="Directory containing JSON documents."
    )
    parser.add_argument(
        "--manual_filter", type=str_to_bool, default=False,
        help="Enable manual filtering by bibtex (true/false)."
    )
    parser.add_argument(
        "--required_bibtex", type=str,
        default="Ahmadi_A_2021,Ahmed_K_2023",
        help="Comma-separated list of bibtex identifiers for manual filtering."
    )

    args = parser.parse_args()

    required_bibtex_set = {bib.strip() for bib in args.required_bibtex.split(",")}

    main(
        k=args.k,
        json_directory=args.json_dir,
        manual_filtering=args.manual_filter,
        required_bibtex=required_bibtex_set
    )
