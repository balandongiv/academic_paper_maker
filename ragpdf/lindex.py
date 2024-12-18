import os

# from llama_index import
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader
from llama_index.llms.openai import OpenAI

os.environ["OPENAI_API_KEY"] = "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"
#
llm = OpenAI(
    model="gpt-4o-mini",
    # api_key="some key",  # uses OPENAI_API_KEY env var by default
)

prompt="Identify and extract the exact text describing machine learning-related issues in previous studies that motivate the author to propose the current method. Return the exact text and 10 list of reasons and in json format { 'motivation': 'reason': 'text','how_the_paper_address:'exact text describing the approach'},reason': 'text','how_the_paper_address:'exact text describing the approach'} }"
documents = SimpleDirectoryReader("data").load_data()
index = VectorStoreIndex.from_documents(documents)
query_engine = index.as_query_engine(llm=llm)
response = query_engine.query(prompt)
print(response)

# Access a specific node (e.g., the first one)
specific_node = response.source_nodes[0]
print("\nDetails of the first node:")
print("Text:", specific_node.text)
print("Metadata:", specific_node.metadata)
# print(response.source_nodes)
