import pandas as pd

def save_journals_to_xlsx(journal_list, filename):
    """
    Saves a list of journal titles to an XLSX file.

    Args:
        journal_list: A list of strings, where each string is a journal title.
        filename: The name of the output XLSX file.
    """

    df = pd.DataFrame({'Journal Title': journal_list})
    df.to_excel(filename, index=False)

if __name__ == "__main__":
    journal_list = [
        "Advanced Materials",
        "Advanced Functional Materials",
        "Chemistry: A European Journal",
        "Advanced Energy Materials",
        "Angewandte Chemie",
        "Advanced Optical Materials",
        "Chemistry: An Asian Journal",
        "ChemPlusChem",
        "European Journal of Organic Chemistry",
        "Molecular Informatics",
        "Journal of Separation Science",
        "Batteries & Supercaps",
        "ChemPhotoChem",
        "European Journal of Lipid Science and Technology",
        "ChemCatChem",
        "ChemSusChem",
        "Archiv der Pharmazie - Chemistry in Life Sciences",
        "Biotechnology Journal",
        "Molecular Nutrition & Food Research",
        "Energy Technology",
        "Journal of Peptide Science",
        "European Journal of Inorganic Chemistry",
        "Astronomische Nachrichten",
        "ChemMedChem",
        "Annalen der Physik",
        "ChemPhysChem",
        "Laser & Photonics Reviews",
        "ChemBioChem",
        "Advanced Engineering Materials",
        "European Journal of Immunology",
        "Macromolecular Rapid Communications",
        "Journal of Biophotonics",
        "Macromolecular Chemistry and Physics",
        "Mathematische Nachrichten",
        "Macromolecular Bioscience",
        "Macromolecular Reaction Engineering",
        "Macromolecular Theory and Simulations",
        "Biometrical Journal",
        "Helvetica Chimica Acta",
        "Journal of Basic Microbiology",
        "Feddes Repertorium",
        "Acta Crystallographica Section F",
        "Acta Crystallographica Section D",
        "Acta Crystallographica Section A",
        "Acta Crystallographica Section B",
        "Acta Crystallographica Section C",
        "Academic Emergency Medicine",
        "Acta Anaesthesiologica Scandinavica",
        "Accounting Perspectives",
        "BioEssays",
        "Advanced Synthesis & Catalysis"
    ]

    filename = r"/research_filter/database/wiley_journal.xlsx"

    save_journals_to_xlsx(journal_list, filename)
    print(f"Journal list saved to {filename}")