from langchain_community.document_loaders.generic import GenericLoader
from langchain_community.document_loaders.parsers import GrobidParser

def load_and_print_metadata():
    loader = GenericLoader.from_filesystem(
        # "/Users/31treehaus/Desktop/Papers/",
        # glob="*",
        path=r'C:\Users\balan\IdeaProjects\academic_paper_maker\research_filter\Abdel_Galil_T_K_2005.pdf',
        suffixes=[".pdf"],
        parser=GrobidParser(segment_sentences=True)
    )
    docs = loader.load()
    print(docs[0].metadata)
    hh = 1

if __name__ == "__main__":
    load_and_print_metadata()