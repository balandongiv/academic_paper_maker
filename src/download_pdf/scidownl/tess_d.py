from api.scihub import scihub_download

def do_download_scihub(scihub_dict):
    for bibtex, details in scihub_dict.items():
        urls = details["url"]
        for url in urls:
            scihub_download(url)
            g=scihub_download('A Connectivity-Aware Graph Neural Network for Real-Time Drowsiness Classification')