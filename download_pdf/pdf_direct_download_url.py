import requests

def download_pdf(url, save_path):
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx and 5xx)
        with open(save_path, 'wb') as file:
            file.write(response.content)
        print(f"PDF successfully downloaded and saved to {save_path}")
    except requests.exceptions.RequestException as e:
        print(f"Failed to download the PDF: {e}")

# URL of the PDF
pdf_url = "https://mdpi-res.com/d_attachment/brainsci/brainsci-09-00348/article_deploy/brainsci-09-00348-v2.pdf?version=1575880976"

# Specify the local file name to save the PDF
save_path = "brainsci-09-00348-v2.pdf"

# Call the function to download the PDF
download_pdf(pdf_url, save_path)
