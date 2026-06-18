
import os

from grobid_clientv.grobid_client import GrobidClient, ServerUnavailableException


def run_gorbid_pdf(input_path, output_path, grobid_server="http://localhost:8070"):
    try:
        client = GrobidClient(
            grobid_server=grobid_server,
            batch_size=1000,
            coordinates=["persName", "figure", "ref", "biblStruct", "formula", "s", "note", "title"],
            sleep_time=5,
            timeout=120,
            config_path=None,
            check_server=True,
        )
    except ServerUnavailableException as e:
        print("GROBID server is not available:", e)
        return []

    os.makedirs(output_path, exist_ok=True)

    return client.process(
        service="processFulltextDocument",
        input_path=input_path,
        output=output_path,
        n=10,
        generateIDs=False,
        consolidate_header=True,
        consolidate_citations=False,
        include_raw_citations=False,
        include_raw_affiliations=False,
        tei_coordinates=False,
        segment_sentences=False,
        force=True,
        verbose=True,
    )


def main():
    input_path = r"G:\My Drive\research_related\0 eeg_trend_till24\eeg_review\pdf"
    output_path = r"G:\My Drive\research_related\0 eeg_trend_till24\eeg_review\xml"
    run_gorbid_pdf(input_path, output_path)


if __name__ == "__main__":
    main()
