import os

from dotenv import load_dotenv
from langchain.schema import Document
from langchain_community.document_loaders import DirectoryLoader, TextLoader

from langchain_community.vectorstores import Chroma
from langchain_openai import  OpenAIEmbeddings
# Load environment variables
load_dotenv()

# Define the directory containing JSON files
json_directory = r"G:\My Drive\research_related\0 eeg_trend_till24\eeg_review\methodology_gap_extractor\json_output\test"

# Load JSON documents
loader = DirectoryLoader(json_directory, glob="**/*.json", loader_cls=TextLoader)

# Load the documents with error handling
try:
    documents = loader.load()
    print(f"Successfully loaded {len(documents)} documents.")
except Exception as e:
    print(f"An error occurred while loading documents: {e}")
    documents = []

if not documents:
    print("No documents were loaded. Exiting.")
    exit(1)

# Extract and structure metadata manually
processed_docs = []
for doc in documents:
    metadata = doc.metadata or {}
    metadata["source"] = metadata.get("source", "Unknown")
    metadata["filename"] = os.path.basename(metadata["source"])

    # Example: Extract bibtext value from the filename (assuming the filename contains it)
    metadata["bibtext"] = metadata["filename"].replace(".json", "")

    # Recreate the document with metadata
    processed_docs.append(Document(page_content=doc.page_content, metadata=metadata))

# Initialize Chroma VectorStore
embedding_function = OpenAIEmbeddings()
chroma_db = Chroma.from_documents(processed_docs, embedding_function)

# Define a list of `bibtext` values to filter
bibtext_list = ["Ahmadi_A_2021", "Ahn_S_2016"]

# Create a filter dictionary to filter by `bibtext`
filter_dict = {"bibtext": {"$in": bibtext_list}}

# Create retriever with filter applied
base_retriever = chroma_db.as_retriever(search_kwargs={'k': 10, 'filter': filter_dict})

# Example search query
query = "your search query"
results = base_retriever.invoke(query)
print(len(results))
# Print results
for result in results:
    print(result)
