import io
import xml.etree.ElementTree as ET
from typing import Any, AnyStr, Dict, List, Optional

from .xml_types import GrobidAddress, GrobidAffiliation, GrobidAuthor, GrobidBiblio, GrobidDocument

xml_ns = "http://www.w3.org/XML/1998/namespace"
ns = "http://www.tei-c.org/ns/1.0"


def _string_to_tree(content: AnyStr) -> ET.ElementTree:
    """
    Helper to consistently parse XML into an ElementTree, whether provided as
    str, bytes, wrapper thereof
    """
    if isinstance(content, str):
        return ET.parse(io.StringIO(content))
    elif isinstance(content, bytes):
        return ET.parse(io.BytesIO(content))
    if isinstance(content, io.StringIO) or isinstance(content, io.BytesIO):
        return ET.parse(content)
    elif isinstance(content, ET.ElementTree):
        return content
    else:
        raise TypeError(f"expected XML as string or bytes, got: {type(content)}")


def _parse_persname(elem: ET.Element, ns: str = ns) -> GrobidAuthor:
    """
    Works on a single persName tag and returns a GrobidAuthor object.

    This is used by both the author and editor parsing code, which insert other
    fields from sibling tags.
    """

    if elem is None:
        return None

    # basic author name stuff
    # create full_name from *all* sub-component text
    full_name = " ".join([t.strip() for t in elem.itertext() if t.strip()]).strip()
    ga = GrobidAuthor(
        full_name=full_name or None,
        given_name=elem.findtext(f'./{{{ns}}}forename[@type="first"]'),
        middle_name=elem.findtext(f'./{{{ns}}}forename[@type="middle"]'),
        surname=elem.findtext(f"./{{{ns}}}surname"),
    )
    return ga


def _parse_affiliation(elem: ET.Element, ns: str = ns) -> Optional[GrobidAffiliation]:

    affiliation_dict: Dict[str, Any] = dict()
    for orgname_tag in elem.findall(f"./{{{ns}}}orgName"):
        orgname_type = orgname_tag.get("type")
        if orgname_type:
            affiliation_dict[orgname_type] = orgname_tag.text or None

    if not affiliation_dict:
        return None

    affiliation = GrobidAffiliation(
        institution=affiliation_dict.get("institution"),
        department=affiliation_dict.get("department"),
        laboratory=affiliation_dict.get("laboratory"),
    )
    address_tag = elem.find(f"./{{{ns}}}address")
    if address_tag is not None:
        address_dict = dict()
        for t in list(address_tag):
            address_dict[t.tag.split("}")[-1]] = t.text or None
        if address_dict:
            affiliation.address = GrobidAddress(
                addr_line=address_dict.get("addrLine"),
                post_code=address_dict.get("postCode"),
                settlement=address_dict.get("settlement"),
                country=address_dict.get("country"),
            )
    return affiliation


def _parse_author(elem: ET.Element, ns: str = ns) -> Optional[GrobidAuthor]:
    """
    Internal helper to parse a single TEI 'author' XML tag into a GrobidAuthor
    objects.

    'author' could appear in document headers or citations.
    """

    persname_tag = elem.find(f"./{{{ns}}}persName")
    if persname_tag is None:
        # should we do something else here? it is possible to have author
        # without persName? need examples for test coverage
        return None

    ga = _parse_persname(persname_tag, ns=ns)
    ga.orcid = elem.findtext(f'.//{{{ns}}}idno[@type="ORCID"]')
    ga.email = elem.findtext(f"./{{{ns}}}email")

    # author affiliation
    affiliation_tag = elem.find(f"./{{{ns}}}affiliation")
    if affiliation_tag is not None:
        ga.affiliation = _parse_affiliation(affiliation_tag, ns=ns)
    return ga


def _parse_editor(elem: ET.Element, ns: str = ns) -> List[GrobidAuthor]:
    """
    Unlike <author>, <editor> sometimes contains multiple persName in the single <editor> tag.

    Also, sometimes there is no persName, only a bare string under the <editor> tag.

    This helper handles all these cases.
    """

    persname_tags = elem.findall(f"./{{{ns}}}persName")
    if len(persname_tags or []) == 0:
        if elem.find("*") is None:
            # sometimes there is a "bare" editor name we can use
            raw_name = elem.text
            if raw_name and len(raw_name.strip()) >= 2:
                return [GrobidAuthor(full_name=raw_name.strip())]
        return []

    persons = []
    for tag in persname_tags:
        ga = _parse_persname(tag, ns=ns)
        # AFAIK editors don't have affiliation; need test coverage if they do
        if ga:
            persons.append(ga)
    return persons


def _clean_url(url: Optional[str]) -> Optional[str]:
    if not url:
        return None
    url = url.strip()
    if url.endswith(".Lastaccessed"):
        url = url.replace(".Lastaccessed", "")
    if url.startswith("<"):
        url = url[1:]
    if ">" in url:
        url = url.split(">")[0]
    return url or None


def test_clean_url() -> None:
    examples: List[dict] = [
        dict(
            dirty="https://archive.org/thing.pdf",
            clean="https://archive.org/thing.pdf",
        ),
        dict(
            dirty="https://archive.org/thing.pdf.Lastaccessed",
            clean="https://archive.org/thing.pdf",
        ),
        dict(
            dirty="<https://archive.org/thing.pdf>",
            clean="https://archive.org/thing.pdf",
        ),
        dict(
            dirty="   https://archive.org/thing.pdf>",
            clean="https://archive.org/thing.pdf",
        ),
        dict(
            dirty="   https://archive.org/thing.pdf>",
            clean="https://archive.org/thing.pdf",
        ),
        dict(dirty="", clean=None),
        dict(dirty=None, clean=None),
    ]

    for row in examples:
        assert row["clean"] == _clean_url(row["dirty"])


def _parse_biblio(elem: ET.Element, ns: str = ns) -> GrobidBiblio:
    """
    Parses an entire TEI 'biblStruct' or 'teiHeader' XML tag

    Could be document header or a citation.
    """

    authors = []
    for ela in elem.findall(f".//{{{ns}}}author"):
        a = _parse_author(ela, ns=ns)
        if a is not None:
            authors.append(a)

    editors = []
    editor_tags = elem.findall(f".//{{{ns}}}editor")
    for elt in editor_tags or []:
        editors.extend(_parse_editor(elt, ns=ns))
    contrib_editor_tags = elem.findall(f'.//{{{ns}}}contributor[@role="editor"]')
    for cet in contrib_editor_tags or []:
        editors.extend(_parse_editor(elt, ns=ns))

    biblio = GrobidBiblio(
        authors=authors,
        editors=editors or None,
        id=elem.attrib.get("{http://www.w3.org/XML/1998/namespace}id"),
        unstructured=elem.findtext(f'.//{{{ns}}}note[@type="raw_reference"]'),
        # date below
        # titles: @level=a for article, @level=m for manuscrupt (book)
        title=elem.findtext(f'.//{{{ns}}}title[@type="main"]'),
        journal=elem.findtext(f'.//{{{ns}}}title[@level="j"]'),
        journal_abbrev=elem.findtext(f'.//{{{ns}}}title[@level="j"][@type="abbrev"]'),
        series_title=elem.findtext(f'.//{{{ns}}}title[@level="s"]'),
        publisher=elem.findtext(f".//{{{ns}}}publicationStmt/{{{ns}}}publisher"),
        institution=elem.findtext(f".//{{{ns}}}respStmt/{{{ns}}}orgName"),
        volume=elem.findtext(f'.//{{{ns}}}biblScope[@unit="volume"]'),
        issue=elem.findtext(f'.//{{{ns}}}biblScope[@unit="issue"]'),
        # pages below
        doi=elem.findtext(f'.//{{{ns}}}idno[@type="DOI"]'),
        pmid=elem.findtext(f'.//{{{ns}}}idno[@type="PMID"]'),
        pmcid=elem.findtext(f'.//{{{ns}}}idno[@type="PMCID"]'),
        arxiv_id=elem.findtext(f'.//{{{ns}}}idno[@type="arXiv"]'),
        pii=elem.findtext(f'.//{{{ns}}}idno[@type="PII"]'),
        ark=elem.findtext(f'.//{{{ns}}}idno[@type="ark"]'),
        istex_id=elem.findtext(f'.//{{{ns}}}idno[@type="istexId"]'),
        issn=elem.findtext(f'.//{{{ns}}}idno[@type="ISSN"]'),
        eissn=elem.findtext(f'.//{{{ns}}}idno[@type="eISSN"]'),
    )

    book_title_tag = elem.find(f'.//{{{ns}}}title[@level="m"]')
    if book_title_tag is not None and book_title_tag.attrib.get("type") is None:
        biblio.book_title = book_title_tag.text
    if biblio.book_title and not biblio.title:
        biblio.title = biblio.book_title
        biblio.book_title = None

    note_tag = elem.find(f".//{{{ns}}}note")
    if note_tag is not None and note_tag.attrib.get("type") is None:
        biblio.note = note_tag.text

    if not biblio.publisher:
        biblio.publisher = elem.findtext(f".//{{{ns}}}imprint/{{{ns}}}publisher")

    date_tag = elem.find(f'.//{{{ns}}}date[@type="published"]')
    if date_tag is not None:
        biblio.date = date_tag.attrib.get("when") or None

    if biblio.arxiv_id and biblio.arxiv_id.startswith("arXiv:"):
        biblio.arxiv_id = biblio.arxiv_id[6:]

    el = elem.find(f'.//{{{ns}}}biblScope[@unit="page"]')
    if el is not None:
        if el.attrib.get("from"):
            biblio.first_page = el.attrib["from"]
        if el.attrib.get("to"):
            biblio.last_page = el.attrib["to"]
        if el.attrib.get("from") and el.attrib.get("to"):
            biblio.pages = "{}-{}".format(el.attrib["from"], el.attrib["to"])
        else:
            biblio.pages = el.text

    el = elem.find(f".//{{{ns}}}ptr[@target]")
    if el is not None:
        biblio.url = _clean_url(el.attrib["target"])

    # having DOI and a DOI URL is redundant
    if biblio.doi and biblio.url:
        if ("://doi.org/" in biblio.url) or ("://dx.doi.org/" in biblio.url):
            biblio.url = None

    return biblio


def parse_document_xml(xml_text: AnyStr) -> GrobidDocument:
    """
    Use this function to parse TEI-XML of a full document or header processed
    by GROBID.

    Eg, the output of '/api/processFulltextDocument' or '/api/processHeader'
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

    refs = []
    for (i, bs) in enumerate(tei.findall(f".//{{{ns}}}listBibl/{{{ns}}}biblStruct")):
        ref = _parse_biblio(bs)
        ref.index = i
        refs.append(ref)
    doc.citations = refs

    text = tei.find(f".//{{{ns}}}text")
    # print(text.attrib)

    if text and text.attrib.get(f"{{{xml_ns}}}lang"):
        # this is the 'body' language
        doc.language_code = text.attrib[f"{{{xml_ns}}}lang"]  # xml:lang

    el = tei.find(f".//{{{ns}}}profileDesc/{{{ns}}}abstract")
    if el is not None:
        doc.abstract = " ".join(el.itertext()).strip() or None
    el = tei.find(f".//{{{ns}}}text/{{{ns}}}body")
    if el is not None:
        doc.body = " ".join(el.itertext()).strip() or None
    el = tei.find(f'.//{{{ns}}}back/{{{ns}}}div[@type="acknowledgement"]')
    if el is not None:
        doc.acknowledgement = " ".join(el.itertext()).strip() or None
    el = tei.find(f'.//{{{ns}}}back/{{{ns}}}div[@type="annex"]')
    if el is not None:
        doc.annex = " ".join(el.itertext()).strip() or None

    return doc


def parse_citation_list_xml(xml_text: AnyStr) -> List[GrobidBiblio]:
    """
    Use this function to parse TEI-XML of one or more references. This should
    work with either /api/processCitation or /api/processCitationList API
    responses from GROBID

    Note that processed citations are usually returned as a bare XML tag, not a
    full XML document, which means that the TEI xmlns is not set. This requires
    a tweak to all downstream parsing code to handle documents with or without
    the namespace.
    """
    if isinstance(xml_text, bytes):
        xml_text = xml_text.replace(b'xmlns="http://www.tei-c.org/ns/1.0"', b"")
    elif isinstance(xml_text, str):
        xml_text = xml_text.replace('xmlns="http://www.tei-c.org/ns/1.0"', "")
    tree = _string_to_tree(xml_text)
    root = tree.getroot()

    if root.tag == "biblStruct":
        ref = _parse_biblio(root, ns="")
        ref.index = 0
        return [ref]

    refs = []
    for (i, bs) in enumerate(tree.findall(".//biblStruct")):
        ref = _parse_biblio(bs, ns="")
        ref.index = i
        refs.append(ref)
    return refs


def parse_citations_xml(xml_text: AnyStr) -> List[GrobidBiblio]:
    """
    Alias for `parse_citation_list_xml()`
    """
    return parse_citation_list_xml(xml_text=xml_text)


def parse_citation_xml(xml_text: AnyStr) -> Optional[GrobidBiblio]:
    """
    Parses a single citation. If the result is empty, or only contains the
    'unstructured' field, returns None.
    """
    # internally, re-uses parse_citation_list_xml()
    citation_list = parse_citation_list_xml(xml_text)
    if not citation_list:
        return None
    citation = citation_list[0]
    citation.index = None
    if citation.is_empty():
        return None
    else:
        return citation
