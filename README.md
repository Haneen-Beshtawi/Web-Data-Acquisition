# Web Data Acquisition: Student Dropout and Academic Success

**Author:** Haneen Beshtawi  
**Course:** DSE 511

## 1. Data-access plan

This project uses the documented-API option to collect **Predict Students' Dropout and Academic Success**, dataset 697 from the UCI Machine Learning Repository. According to the source documentation, each observation represents one student. The selected fields describe the student's course, admission grade, semester performance, and academic outcome.

The planned collection uses two sequential requests: one to obtain the dataset metadata through the API, and another to download the CSV from the URL returned in that response. No scraping, account, or API key is required. This source is appropriate for educational data science because it supports examining academic progress and student outcomes.

The dataset is publicly available under CC BY 4.0. No numeric request limit was verified, so the collection is limited to the necessary requests, with bounded retries for temporary failures and reuse of saved data. The raw file includes demographic and financial information. These fields are excluded from the cleaned dataset because they are unnecessary for the analysis. No attempt is made to identify students or connect their records to outside personal information.

## 2. Source and collection details

| Item | Details |
| --- | --- |
| Source | UCI Machine Learning Repository |
| Dataset | Predict Students' Dropout and Academic Success |
| Dataset ID | 697 |
| Dataset DOI | [10.24432/C5MC89](https://doi.org/10.24432/C5MC89) |
| API endpoint | `https://archive.ics.uci.edu/api/dataset` |
| Query parameter | `id=697` |
| CSV URL returned by the API | `https://archive.ics.uci.edu/static/public/697/data.csv` |
| Account or API key | Not required |
| Requests made | Two GET requests; both returned HTTP 200 |
| Collection date and time | October 23, 2026, approximately 23:09 UTC |
| Collection start | `2026-10-23T23:09:10.622577+00:00` |
| Collection finish | `2026-10-23T23:09:17.617806+00:00` |
| Source last-update label | February 26, 2024 |
| API version | No explicit version is provided in the endpoint |
| Original dataset | 4,424 observations, 36 features, and one outcome |
| Cleaned dataset | 4,424 observations and eight selected attributes, plus a source-row reference |
| License | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) |

The API returns JSON metadata containing a `data_url`. The program downloads the CSV from that URL, following the same two-stage retrieval used by UCI's [official Python client](https://github.com/uci-ml-repo/ucimlrepo). The student records are contained in the CSV, not in the metadata JSON.

The original response bytes are preserved. Collection times, request outcomes, source information, Python version, and SHA-256 file hashes are recorded in `outputs/provenance.json` and `outputs/request_log.json`.

## 3. Change from the original source

The original source was the HarvardX Person-Course dataset on [Harvard Dataverse](https://doi.org/10.7910/DVN/26147). Metadata retrieval succeeded, but data-file requests failed with HTTP 400 and 403 responses. A later server message identified a required response to Guestbook 54. This indicated an unmet access condition, not evidence of a recent policy change.

No successful authorized API download of the HarvardX learner records was verified, and no access restriction was bypassed. The project therefore switched to UCI dataset 697, which was collected successfully without credentials. The replacement contains institutional higher-education records rather than MOOC activity logs. Saved attempt logs and the source-change explanation are included in `evidence/`.

## 4. Requirements and execution

Python 3.10 or later is required. The script was tested with Python 3.12.14. It uses only Python's standard library, so no additional packages or credentials are needed.

Open the **Web Data Acquisition** folder in VS Code and open a terminal.

To verify the saved raw files and reproduce cleaning and analysis:

```powershell
py collect_education.py
```

To collect a new copy from the API and run all steps:

```powershell
py collect_education.py --fresh
```

The script executes acquisition, cleaning, and analysis in that order. A fresh run saves its files in a new dated folder under `collections/` and prints the output location. Existing raw data are not overwritten. Expected runtime is a few seconds to approximately two minutes, depending on the network and computer.

The code reports network errors, timeouts, access failures, and unexpected data structures. It stops on HTTP 401, 403, or 429 rather than repeatedly requesting denied or rate-limited access. No credentials are embedded in the code.

## 5. Project files

| File or folder | Contents |
| --- | --- |
| `collect_education.py` | Separate acquisition, cleaning, and analysis functions |
| `requirements.txt` | Python dependency information |
| `data/raw/metadata.json` | Original API metadata response |
| `data/raw/students_original.csv` | Complete original CSV |
| `data/cleaned/students_cleaned.csv` | Cleaned academic data |
| `outputs/provenance.json` | Source, collection details, and raw-file hashes |
| `outputs/request_log.json` | Request attempts, times, and status codes |
| `outputs/validation.json` | Validation rules and results |
| `outputs/cleaned_sample.csv` | First five cleaned observations |
| `outputs/outcome_summary.csv` | Descriptive statistics by outcome |
| `outputs/MINI_ANALYSIS.md` | Tidy sample, comparison, interpretation, and limitations |
| `ETHICS_REFLECTION.md` | Dataset-specific ethics reflection |
| `evidence/` | Original-source failure evidence |

For a fresh run, the data and outputs folders are created inside its dated collection folder.

## 6. Cleaning and validation

The raw files remain unchanged. The cleaned data retain eight academic attributes: course code, admission grade, first-semester units enrolled and approved, first-semester grade, second-semester units approved and grade, and outcome.

The following steps are documented and implemented:

1. Select the academic fields and rename them using descriptive `snake_case` names.
2. Remove outer whitespace and convert grades to floating-point values and counts/codes to integers.
3. Check that selected values are present and finite, counts are nonnegative integers, admission grades are within 0-200, and semester grades are within 0-20.
4. Validate the outcome labels: `Dropout`, `Enrolled`, and `Graduate`.
5. Check that first-semester approved units do not exceed enrolled units.
6. Check complete source-row duplicates without assuming that students with matching academic values are the same person.

All 4,424 observations passed the implemented checks. No missing selected values, invalid selected values, or complete-row duplicates were found. Unexpected invalid or missing values stop the program for inspection rather than being silently corrected.

The added `source_row` column refers to the row's position in the saved file; it is not a real student identifier. Course codes are categorical labels, even though they are stored as integers. The creators already preprocessed the source dataset, so this project emphasizes validation rather than unnecessary corrections.

## 7. Mini analysis and limitations

The descriptive question is: **How do first-semester grades and approved units differ by recorded academic outcome?**

| Outcome | Students | Mean first-semester grade | Mean first-semester units approved |
| --- | ---: | ---: | ---: |
| Dropout | 1,421 | 7.257 | 2.552 |
| Enrolled | 794 | 11.125 | 4.319 |
| Graduate | 2,209 | 12.644 | 6.232 |

The Graduate group has higher average first-semester grades and approved units than the Dropout group. These are descriptive associations and do not establish causation. A tidy sample and further interpretation are included in `outputs/MINI_ANALYSIS.md`.

The data come from one institutional setting and may not represent other universities. Outcome refers to status at the end of the normal course duration. Semester results are unavailable at admission, so using them for admission-time predictions would introduce future-information leakage. Zero grades should not automatically be interpreted as lack of effort.

The source records, API, and access conditions may change. The saved raw files and hashes support exact reproduction of this collection. A `--fresh` run records its own collection times and provenance; those values should accompany that snapshot. No HTML scraping was performed, and access assessment was based on the documented API and dataset license.

## 8. Ethics and attribution

The separate reflection addresses responsible API access, privacy, potential identification through data linkage, misuse of dropout labels, bias, and limitations. Public access does not eliminate the responsibility to protect students or avoid unsupported conclusions.

**Dataset citation:** Realinho, V., Vieira Martins, M., Machado, J., and Baptista, L. (2021). *Predict Students' Dropout and Academic Success* [Dataset]. UCI Machine Learning Repository. https://doi.org/10.24432/C5MC89.

**License:** CC BY 4.0. Modifications include selecting academic fields, renaming columns, converting types, adding source-row references, and producing aggregate summaries. Original files are preserved unchanged.

**Scientific-computing reference:** Wilson et al. (2017). *Good enough practices in scientific computing*. https://doi.org/10.1371/journal.pcbi.1005510.
