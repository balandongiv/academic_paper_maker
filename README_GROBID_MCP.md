# GROBID Local API Usage Across Repositories

Treat GROBID as an external local service: keep GROBID running in Docker, then call its HTTP API from any repository on the same computer. In MCP terms, GROBID is a local tool provider exposed at `http://localhost:8070`; each project is just a client.

## 1. Start GROBID

Docker must be running first.

```powershell
docker pull grobid/grobid:0.8.1
docker run -d --name academic_paper_maker_grobid -p 8070:8070 grobid/grobid:0.8.1
```

If a container with that name already exists:

```powershell
docker start academic_paper_maker_grobid
```

Check that the API is alive:

```powershell
python -c "import requests; r=requests.get('http://localhost:8070/api/isalive', timeout=10); print(r.status_code, r.text)"
```

Expected output:

```text
200 true
```

You can also open this in a browser on the same computer:

```text
http://localhost:8070/
```

## 2. Python Environment In Another Repository

The calling repository does not need to use the `academic_paper_maker` environment. Any Python environment can call GROBID because the boundary is HTTP.

Minimum dependency for API calls:

```powershell
python -m pip install requests
```

Optional dependency if the other repository will parse TEI XML itself:

```powershell
python -m pip install lxml
```

Example isolated environment in another repository:

```powershell
cd C:\Users\balan\IdeaProjects\some_other_repo
python -m venv .venv
.\.venv\Scripts\activate
python -m pip install requests lxml
```

No `PYTHONPATH` is needed unless that other repository imports code from `academic_paper_maker`.

## 3. API Access From The Same Computer

GROBID exposes REST endpoints under:

```text
http://localhost:8070/api/
```

Use this URL from any repository on the same Windows machine:

```powershell
python -c "import requests; r=requests.get('http://localhost:8070/api/isalive', timeout=10); print(r.status_code, r.text)"
```

Common endpoints:

```text
GET  /api/isalive
POST /api/processFulltextDocument
POST /api/processHeaderDocument
POST /api/processReferences
```

Example: submit one PDF directly to GROBID and save TEI XML from another repository.

```powershell
python -c "import requests; files={'input': open('paper.pdf','rb')}; r=requests.post('http://localhost:8070/api/processFulltextDocument', files=files, timeout=120); r.raise_for_status(); open('paper.grobid.tei.xml','w',encoding='utf-8').write(r.text)"
```

Equivalent reusable Python file:

```python
from pathlib import Path

import requests


GROBID_SERVER = "http://localhost:8070"


def pdf_to_tei_xml(pdf_path: str, output_path: str | None = None) -> Path:
    pdf = Path(pdf_path)
    output = Path(output_path) if output_path else pdf.with_suffix(".grobid.tei.xml")

    with pdf.open("rb") as pdf_file:
        response = requests.post(
            f"{GROBID_SERVER}/api/processFulltextDocument",
            files={"input": (pdf.name, pdf_file, "application/pdf")},
            data={
                "consolidateHeader": "1",
                "consolidateCitations": "0",
            },
            timeout=120,
        )

    response.raise_for_status()
    output.write_text(response.text, encoding="utf-8")
    return output


if __name__ == "__main__":
    print(pdf_to_tei_xml("paper.pdf"))
```

## 4. Optional: Reuse This Repository's Wrapper

If another repository wants to import the wrapper from `academic_paper_maker`, install or expose this repo on `PYTHONPATH`. This couples the other project to this source tree, so use direct HTTP calls when portability matters.

From the other repository:

```powershell
$env:PYTHONPATH = "C:\Users\balan\IdeaProjects\academic_paper_maker\src"
python -c "from grobid_tei_xml.gorbid_client_pdf import run_gorbid_pdf; run_gorbid_pdf('paper.pdf', 'xml')"
```

This writes:

```text
xml/paper.grobid.tei.xml
```

To use this repo's TEI-to-JSON pipeline from the other repository:

```powershell
$env:PYTHONPATH = "C:\Users\balan\IdeaProjects\academic_paper_maker\src"
python -c "from grobid_tei_xml.xml_json import run_pipeline; run_pipeline('xml')"
```

## 5. Use The Project Wrapper Inside This Repository

From the repository root:

```powershell
$env:PYTHONPATH = "src"
python -c "from grobid_tei_xml.gorbid_client_pdf import run_gorbid_pdf; run_gorbid_pdf('AbhijitBhattacharyy2023.pdf', 'xml')"
```

This writes:

```text
xml/AbhijitBhattacharyy2023.grobid.tei.xml
```

Then convert the TEI XML into project JSON:

```powershell
$env:PYTHONPATH = "src"
python -c "from grobid_tei_xml.xml_json import run_pipeline; run_pipeline('xml')"
```

This writes JSON under:

```text
xml/json/
```

## 6. Configuration

This repository's local default is stored in:

```text
setting/config.json
```

Current expected server:

```json
{
  "grobid_server": "http://localhost:8070"
}
```

Use `localhost` when calling from the same computer, even if the code is in a different repository or Python environment.

If a different physical computer needs access, do not use `localhost` from that second computer. Use the host computer's LAN IP address and make sure the firewall allows port `8070`.

## 7. Operational Checks

List the GROBID container:

```powershell
docker ps --filter "name=academic_paper_maker_grobid"
```

View logs:

```powershell
docker logs academic_paper_maker_grobid
```

Stop the service:

```powershell
docker stop academic_paper_maker_grobid
```

Remove the container:

```powershell
docker rm academic_paper_maker_grobid
```

## 8. Troubleshooting

If `localhost:8070` refuses the connection, GROBID is not running or the port is not published. Check:

```powershell
docker ps
docker start academic_paper_maker_grobid
```

If `docker start` fails because the container does not exist, run the `docker run` command from section 1.

If code in another repository cannot import `grobid_tei_xml`, either use direct HTTP calls with `requests`, or set `PYTHONPATH` to this repository's `src` folder:

```powershell
$env:PYTHONPATH = "C:\Users\balan\IdeaProjects\academic_paper_maker\src"
```

If GROBID returns HTTP errors for a PDF, test with `GET /api/isalive` first. If the service is alive, check the PDF path and try a smaller timeout-safe file.
