import requests
from bs4 import BeautifulSoup
import pandas as pd

def extract_journal_data(url):
    """
    Extracts journal names and hrefs from the given URL.

    Args:
        url: The URL of the webpage to scrape.

    Returns:
        A list of dictionaries, where each dictionary contains the name and href of a journal.
    """

    response = requests.get(url)
    response.raise_for_status()  # Raise an exception for bad status codes

    soup = BeautifulSoup(response.content, 'html.parser')

    journal_data = []
    rows = soup.find_all('tr')

    for row in rows:
        name_cell = row.find('td', class_='journal-name-cell')
        if name_cell:
            link = name_cell.find('a', class_='lean')
            if link:
                journal_name = link.find('div').get_text(strip=True)
                journal_href = "https://www.mdpi.com" + link['href']
                journal_data.append({'Journal Name': journal_name, 'Href': journal_href})

    return journal_data

def save_to_xlsx(data, filename):
    """
    Saves the journal data to an XLSX file.

    Args:
        data: A list of dictionaries containing the journal data.
        filename: The name of the output XLSX file.
    """

    df = pd.DataFrame(data)
    df.to_excel(filename, index=False)

if __name__ == "__main__":
    url = "https://www.mdpi.com/about/journals/wos"
    filename = "mdpi_journals.xlsx"

    try:
        journal_data = extract_journal_data(url)
        save_to_xlsx(journal_data, filename)
        print(f"Journal data successfully saved to {filename}")
    except requests.exceptions.RequestException as e:
        print(f"Error during request: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")