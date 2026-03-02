# TO remove this code,to avoid confusion, once we confident the run_gorbid_pdf work like charm

import os

from grobid_client.grobid_client import GrobidClient, ServerUnavailableException

from grobid_tei_xml.parsed_gorbid import parse_document_xml


def main():
    try:
        # Instantiate the client
        client = GrobidClient(
            grobid_server='http://localhost:8070',  # Adapt to your GROBID server endpoint
            batch_size=1000,
            coordinates=["persName", "figure", "ref", "biblStruct", "formula", "s", "note", "title"],
            sleep_time=5,
            timeout=60,
            config_path=None,             # or a path to your config.json if you have one
            check_server=True
        )
    except ServerUnavailableException as e:
        print("GROBID server is not available:", e)
        return

    # Now you can call any of the methods from GrobidClient
    # For example, process a directory of PDFs with 'processFulltextDocument'
    main_folder=r"G:\My Drive\research_related\corona_discharge"
    input_path = os.path.join(main_folder, "pdf")
    output_path =os.path.join(main_folder, "xml")

    # Ensure output_path exists
    if not os.path.isdir(output_path):
        os.makedirs(output_path, exist_ok=True)

    # Let’s call process() for full-text
    client.process(
        service="processFulltextDocument",   # e.g. 'processFulltextDocument'
        input_path=input_path,
        output=output_path,
        n=10,                                 # concurrency
        generateIDs=False,
        consolidate_header=True,
        consolidate_citations=False,
        include_raw_citations=False,
        include_raw_affiliations=False,
        tei_coordinates=False,
        segment_sentences=False,
        force=True,
        verbose=True
    )

def process_xml():

    '''
    This is just example for we are not going to use this approach, but we are going to use the code
    in convert_xml_json.py instead
    :return:
    '''
    xml_path = r"C:\Users\balan\IdeaProjects\academic_paper_maker\Abubakar_MasUd_A_2014.grobid.tei.xml"

    with open(xml_path, 'r') as xml_file:
        doc = parse_document_xml(xml_file.read())

    # print(json.dumps(doc.to_dict(), indent=2))
    print(doc.header)
    print(doc.citations)
    print(doc.language_code)
    print(doc.abstract)
    print(doc.body)
    print(doc.acknowledgement)
    print(doc.annex)
    print(doc.sections)


if __name__ == "__main__":
    main()
    # process_xml()
