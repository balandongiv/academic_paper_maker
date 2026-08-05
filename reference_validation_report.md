# Reference validation report

Date checked: 2026-07-20

Input: `ref.txt` (19 references)

## Important Scopus/API limitation

The repository currently contains Selenium-based Scopus automation, not a Scopus/Elsevier API client. The only configured environment key is `OPENAI_API_KEY`; no Elsevier API key is configured. A direct request to the Elsevier Scopus endpoint was attempted and returned HTTP 401 Unauthorized.

Therefore, the report below verifies existence using DOI/Crossref metadata and public publisher or scholarly web records. It does **not** claim that every item is indexed by Scopus. Scopus inclusion should be rechecked after adding a valid Elsevier API key or using the existing authenticated Scopus browser profile.

## Results

Status meanings:

- **EXISTS**: DOI registration and bibliographic metadata were found; the DOI is a positive existence match.
- **EXISTS - citation correction**: the work exists, but the student citation has a minor bibliographic discrepancy.
- **NON-EXISTING**: no matching DOI or authoritative web record found. None were found in this file.
- **SCOPUS UNVERIFIED**: Scopus API could not authenticate, so Scopus indexing was not asserted.

| # | Student reference / DOI | Website/DOI result | Scopus result | Flag |
|---:|---|---|---|---|
| 1 | Anwary et al. (2021), *Smart-Cover* — [10.1016/j.sna.2020.112451](https://doi.org/10.1016/j.sna.2020.112451) | EXISTS; title, authors, 2021, volume 317/article 112451 match | UNVERIFIED | No |
| 2 | Arshad et al. (2022), *An Intelligent Cost-Efficient System...* — [10.1155/2022/7957148](https://doi.org/10.1155/2022/7957148) | EXISTS; title, authors, 2022 and article ID match | UNVERIFIED | No |
| 3 | Beri et al. (2022), *IoT Based Health Monitoring System Built on ESP32* — [10.1109/ICACITE53722.2022.9823528](https://doi.org/10.1109/ICACITE53722.2022.9823528) | EXISTS; IEEE DOI metadata matches | UNVERIFIED | No |
| 4 | Bowler et al. (2022), *A review of ultrasonic sensing...* — [10.1016/j.ultras.2022.106776](https://doi.org/10.1016/j.ultras.2022.106776) | EXISTS; title, authors, *Ultrasonics* 124, article 106776 match | UNVERIFIED | No |
| 5 | Ferdous et al. (2023), *Implementation of IoT Based Patient Health Monitoring...* — [10.21474/ijar01/17119](https://doi.org/10.21474/ijar01/17119) | EXISTS; DOI metadata matches title and 2023 publication | UNVERIFIED | No |
| 6 | Giovanelli & Farella (2016), *Force Sensing Resistor...* — [10.1155/2016/9391850](https://doi.org/10.1155/2016/9391850) | EXISTS; title, authors, *Journal of Sensors*, 2016 match | UNVERIFIED | No |
| 7 | Helmstetter & Matthiesen (2023), *Human Posture Estimation...* — [10.3390/s23218997](https://doi.org/10.3390/s23218997) | EXISTS; MDPI DOI metadata matches; title punctuation differs slightly | UNVERIFIED | No |
| 8 | Jaffery et al. (2022), *FSR-Based Smart System...* — [10.1155/2022/1901058](https://doi.org/10.1155/2022/1901058) | EXISTS; title, authors and 2022 article ID match | UNVERIFIED | No |
| 9 | Javaid et al. (2023), *Force Sensitive Resistors-Based Real-Time Posture Detection...* — [10.32604/cmc.2023.044140](https://doi.org/10.32604/cmc.2023.044140) | EXISTS; title, authors and 2023 DOI record match | UNVERIFIED | No |
| 10 | Kumar Sharma & Tr (2023), *A Deep Analysis of Medical Monitoring System...* — [10.1109/ICACITE57410.2023.10182920](https://doi.org/10.1109/ICACITE57410.2023.10182920) | EXISTS; IEEE DOI metadata matches | UNVERIFIED | No |
| 11 | La Mura et al. (2023), *IoT System for Real-Time Posture Asymmetry Detection* — [10.3390/s23104830](https://doi.org/10.3390/s23104830) | EXISTS; MDPI DOI metadata matches | UNVERIFIED | No |
| 12 | Liu et al. (2024), *Comparative Analysis of Force-Sensitive Resistors...* — [10.3390/s24237705](https://doi.org/10.3390/s24237705) | EXISTS; MDPI DOI metadata matches | UNVERIFIED | No |
| 13 | Matuska et al. (2020), *A Smart System for Sitting Posture Detection...* — [10.1155/2020/6625797](https://doi.org/10.1155/2020/6625797) | EXISTS; title, authors and 2020 article record match | UNVERIFIED | No |
| 14 | Odesola et al. (2024), *Smart Sensing Chairs...* — [10.3390/s24092940](https://doi.org/10.3390/s24092940) | EXISTS; MDPI DOI metadata matches | UNVERIFIED | No |
| 15 | Pereira & Plácido da Silva (2023), *A Novel Smart Chair System...* — [10.3390/s23020719](https://doi.org/10.3390/s23020719) | EXISTS; MDPI DOI metadata matches | UNVERIFIED | No |
| 16 | Sifuentes et al. (2019), *Seat Occupancy Detection...* — [10.3390/s19030699](https://doi.org/10.3390/s19030699) | EXISTS; title, authors and 2019 DOI record match | UNVERIFIED | No |
| 17 | Sujithra et al. (2024), *An IoT System for Sitting Posture Detection...* — [10.1109/IC3IoT60841.2024.10550418](https://doi.org/10.1109/IC3IoT60841.2024.10550418) | EXISTS; IEEE DOI metadata matches | UNVERIFIED | No |
| 18 | Zaharuddin & Mohd Shah (2024), *A Smart Chair for Sitting Postures Monitoring...* — [10.30880/jeva.2024.05.02.004](https://doi.org/10.30880/jeva.2024.05.02.004) | EXISTS; UTHM DOI metadata matches | UNVERIFIED | No |
| 19 | Zhao & You (2021), *Design and data analysis of wearable sports posture...* — [10.1016/j.aej.2020.10.001](https://doi.org/10.1016/j.aej.2020.10.001) | EXISTS; title, authors, *Alexandria Engineering Journal* and 2021 publication match | UNVERIFIED | No |

## Conclusion

- References checked: **19**.
- DOI/website existence confirmed: **19**.
- Clearly non-existing references: **0**.
- Student references flagged as fabricated: **0**.
- Scopus-indexing checks: **pending authentication**; the API returned HTTP 401.

The references should not be labelled “Scopus indexed” based only on this report. Once an Elsevier API key is supplied, each DOI can be checked with a query such as `DOI(10.xxxx/xxxxx)` and the Scopus EID recorded in a second pass.
