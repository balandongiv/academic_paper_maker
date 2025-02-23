from langchain_community.vectorstores.chroma import Chroma
from langchain_community.vectorstores import Chroma
# Define your lists of metadata
name_list = ['doc1', 'doc2', 'doc3']
author_list = ['Alice', 'Bob']
published_list = [True]

# Create filter dictionaries for each list
name_filter = {"name": {"$in": name_list}}
author_filter = {"author": {"$in": author_list}}
published_filter = {"published": {"$in": published_list}}

# Combine filters using $and or $or operators
combined_filter = {
    "$and": [
        name_filter,
        author_filter,
        published_filter
    ]
}

# Create the retriever with the combined filter
base_retriever = chroma_db.as_retriever(search_kwargs={'k': 10, 'filter': combined_filter})

# Perform the query
query = "your search query"
results = base_retriever.invoke(query)

# Print the results
for result in results:
    print(result)