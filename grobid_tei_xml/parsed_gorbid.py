from typing import AnyStr, List
from xml.etree import ElementTree

from grobid_tei_xml.parse import _string_to_tree
from grobid_tei_xml.xml_types import GrobidCitation, GrobidDocument

ns = "http://www.tei-c.org/ns/1.0"
xml_ns = "http://www.w3.org/XML/1998/namespace"



def _parse_biblio(biblio: ElementTree.Element) -> GrobidCitation:
    """
    Parses a biblioStruct or fileDesc element into a GrobidCitation.
    """
    title_el = biblio.find(
        f".//{{{ns}}}title[@level='a'] | .//{{{ns}}}title[@level='m']"
    )
    journal_el = biblio.find(f".//{{{ns}}}title[@level='j']")
    date_el = biblio.find(f".//{{{ns}}}date")
    authors: List[str] = []
    for author_el in biblio.findall(f".//{{{ns}}}author"):
        persname_el = author_el.find(f".//{{{ns}}}persName")
        if persname_el is not None:
            firstname_el = persname_el.find(f".//{{{ns}}}forename[@type='first']")
            middlename_el = persname_el.find(f".//{{{ns}}}forename[@type='middle']")
            surname_el = persname_el.find(f".//{{{ns}}}surname")

            name_parts = [
                part.text
                for part in [firstname_el, middlename_el, surname_el]
                if part is not None and part.text
            ]
            authors.append(" ".join(name_parts))

    return GrobidCitation(
        title=title_el.text if title_el is not None else None,
        journal=journal_el.text if journal_el is not None else None,
        date=date_el.attrib.get("when") if date_el is not None else None,
        authors=authors,
    )

def parse_document_xml(xml_text: AnyStr) -> GrobidDocument:
    """
    Use this function to parse TEI-XML of a full document or header processed
    by GROBID.

    E.g., the output of '/api/processFulltextDocument' or '/api/processHeader'
    """

    tree = _string_to_tree(xml_text)
    tei = tree.getroot()

    header = tei.find(f".//{{{ns}}}teiHeader")
    if header is None:
        raise ValueError("XML does not look like TEI format")

    application_tag = header.findall(f".//{{{ns}}}appInfo/{{{ns}}}application")[0]

    doc = GrobidDocument(
        grobid_version=application_tag.attrib["version"].strip(),
        grobid_timestamp=application_tag.attrib["when"].strip(),
        header=_parse_biblio(header),
        pdf_md5=header.findtext(f'.//{{{ns}}}idno[@type="MD5"]'),
    )

    # Collect references/citations:
    refs = []
    for (i, bs) in enumerate(tei.findall(f".//{{{ns}}}listBibl/{{{ns}}}biblStruct")):
        ref = _parse_biblio(bs)
        ref.index = i
        refs.append(ref)
    doc.citations = refs

    # Extract body language code if available
    text = tei.find(f".//{{{ns}}}text")
    if text is not None and text.attrib.get(f"{{{xml_ns}}}lang"):
        doc.language_code = text.attrib[f"{{{xml_ns}}}lang"]

    # Extract abstract text
    el = tei.find(f".//{{{ns}}}profileDesc/{{{ns}}}abstract")
    if el is not None:
        doc.abstract = " ".join(el.itertext()).strip() or None

    # Extract body sections/paragraphs
    el = tei.find(f".//{{{ns}}}text/{{{ns}}}body")
    if el is not None:
        # We will keep count of 'untitled' sections
        untitled_section_count = 0

        for div in el.findall(f".//{{{ns}}}div"):
            # Gather all paragraphs in this <div>
            paragraphs = [
                " ".join(p.itertext()).strip()
                for p in div.findall(f".//{{{ns}}}p")
            ]
            # If there are no <p> elements, skip
            if not paragraphs:
                continue

            # Try to find a <head>
            head = div.find(f".//{{{ns}}}head")
            if head is not None:
                head_text = head.text or ""
                head_n = head.attrib.get("n")
                title = (f"{head_n} {head_text}".strip()
                         if head_n else head_text.strip())
            else:
                # No head, use fallback
                untitled_section_count += 1
                title = f"Untitled Section {untitled_section_count}"

            # Store the paragraphs under this title
            doc.sections[title] = paragraphs

        # Optionally store the entire body text
        doc.body = " ".join(el.itertext()).strip() or None

    # Acknowledgement
    el = tei.find(f'.//{{{ns}}}back/{{{ns}}}div[@type="acknowledgement"]')
    if el is not None:
        doc.acknowledgement = " ".join(el.itertext()).strip() or None

    # Annex
    el = tei.find(f'.//{{{ns}}}back/{{{ns}}}div[@type="annex"]')
    if el is not None:
        doc.annex = " ".join(el.itertext()).strip() or None

    return doc


if __name__ == "__main__":

    xml_path = r"G:\My Drive\research_related\0 eeg_trend_till24\eeg_review\xml/Ahmadi_A_2021.grobid.tei.xml"
    # Example usage (assuming you have the XML content in a variable called `xml_content`)

    with open(xml_path, 'r') as xml_file:
        doc = parse_document_xml(xml_file.read())

    print(doc.header)
    print(doc.citations)
    print(doc.language_code)
    print(doc.abstract)
    print(doc.body)
    print(doc.acknowledgement)
    print(doc.annex)
    print(doc.sections)
    hh = 1
