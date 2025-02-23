import os
from dotenv import load_dotenv
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import OpenAIEmbeddings
from langchain_community.chat_models import ChatOpenAI
from langchain.retrievers.self_query.base import SelfQueryRetriever
from langchain.chains.query_constructor.schema import AttributeInfo

# Load environment variables (Ensure OPENAI_API_KEY is set)
load_dotenv()

# Define the directory containing JSON files
json_directory = r"G:\My Drive\research_related\0 eeg_trend_till24\eeg_review\methodology_gap_extractor\json_output\test"

# Load JSON documents using DirectoryLoader with TextLoader
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

# Process metadata manually (since TextLoader does not extract JSON metadata)
for doc in documents:
    doc.metadata["source"] = doc.metadata.get("source", "Unknown")
    doc.metadata["filename"] = os.path.basename(doc.metadata["source"])

# Initialize OpenAI embeddings
embeddings = OpenAIEmbeddings()

# Create a Chroma vector store from the documents
vectorstore = Chroma.from_documents(documents, embeddings)

# Define metadata fields for SelfQueryRetriever
metadata_field_info = [
    AttributeInfo(name="source", description="The source file of the document.", type="string"),
    AttributeInfo(name="filename", description="The filename of the document.", type="string"),
]

# Initialize the language model
llm = ChatOpenAI(temperature=0)

# Create a SelfQueryRetriever
retriever = SelfQueryRetriever.from_llm(
    llm,
    vectorstore,
    "Research study details",
    metadata_field_info,
)

# Define a query
query = "get filename with bibtext Ahmadi_A_2021 and Ahmed_K_2023"

# Retrieve relevant documents
relevant_docs = retriever.get_relevant_documents(query)

# Display results
print(f"\nQuery: {query}")
print(f"Found {len(relevant_docs)} relevant document(s):\n")

for i, doc in enumerate(relevant_docs, start=1):
    print(f"Document {i}:")
    print(f"Filename: {doc.metadata.get('filename', 'N/A')}")
    print(f"Source: {doc.metadata.get('source', 'N/A')}")
    print(f"Content Snippet: {doc.page_content[:300]}...")
    print("-" * 80)
