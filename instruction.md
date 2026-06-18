You are the agent manager for a sequential multi-agent literature-review pipeline.

Your task is to generate, test, and validate a literature-review writing pipeline for the topic:

**Fatigue-driving EEG studies from 2017 to 2026**

Do **not** run the full literature-review sweep yet. First, test the complete pipeline only on:

**Theme A: Limited Number of EEG Electrodes**
**Subtheme: Single-channel EEG**

## 1. Agent orchestration requirements

Spawn several agents conceptually, but execute the workflow sequentially.

For any agent responsible for writing academic text, you must use the **ChatGPT UI agent**, not a local LLM. This agent should access the ChatGPT web interface through Selenium, similar to the existing `chatgpt_ui` code. If the existing code is insufficient, create a new implementation that can reliably send both:

1. the writing prompt, and
2. the relevant extracted paper information

into the ChatGPT UI.

You are responsible for designing the agent workflow and writing custom prompts for each agent.

All custom prompts must be saved locally so they can be inspected later for quality control.

## 2. Input files and folders

Use the following inputs:

* `candidates_eeg_fatigue_driver.csv`

    * Contains the 969 selected studies to be considered for the full literature review.

* `iterate_literature_review/fatigue_eeg_outputs/`

    * Contains the study summaries.
    * The summaries are stored as nested dictionaries.
    * Extract only the content under the key:

```json
"chatgpt_response"
```

* `literature_review_theme.md`

    * Contains the main themes and subthemes.
    * Use this file to determine the correct theme and subtheme structure.

* `writing_technique.MD`

    * Contains the required academic writing style and technique.
    * All generated writing must follow this file.

The relevant classification metadata may appear in fields such as:

```json
"zotero_classification": {
  "main_collection": "",
  "sub_collection": "",
  "subsub_collection": "",
  "secondary_collections": [],
  "suggested_zotero_path": ""
}
```

and:

```json
"themes": [
  {
    "theme_code": "",
    "theme_name": "",
    "subthemes": []
  }
]
```
You may consider to combine all the JSON under the folder `iterate_literature_review/fatigue_eeg_outputs/` into a single structured dataset for easier querying.Then, you can use SQL or an equivalent structured filtering method to select studies relevant to the target theme and subtheme.



## 3. Literature-review writing requirements

Generate an academic literature-review section for:

**Theme A: Limited Number of EEG Electrodes**
**Subtheme: Single-channel EEG**

The writing must not simply report findings study by study. It must critically discuss, compare, contrast, and synthesize the literature.

The section should have a clear argumentative flow and a coherent story. It should explain how the field has developed from 2017 to 2026, especially in relation to single-channel EEG for fatigue-driving detection.

For each paragraph:

* Critically discuss the relevant subtheme.
* Compare findings across studies where possible.
* Highlight methodological strengths and weaknesses.
* Discuss dataset choices, EEG channel choices, model choices, validation strategies, and limitations where relevant.
* Avoid unsupported claims.
* Ensure all factual claims are traceable to the selected study summaries.
* Use academic writing style consistent with `writing_technique.MD`.

## 4. Consistency-checking requirements

After each paragraph or writing unit is generated, use the same ChatGPT UI writing agent to check whether the generated text is consistent with the JSON-derived input summaries.

As the agent manager, create a dedicated consistency-checking prompt.

The consistency checker must verify:

* Whether every claim is supported by the extracted `chatgpt_response` content.
* Whether the cited studies actually match the claim.
* Whether any study has been misrepresented.
* Whether the paragraph introduces unsupported generalizations.
* Whether the writing remains aligned with the selected theme and subtheme.
* Whether the paragraph maintains an academic and critical tone.

Save all consistency-checking prompts and results locally for future QC.

## 5. LaTeX generation requirements

Generate the final output in LaTeX. All the writing should be saved in the foler `iterate_literature_review\writing`

Each paragraph must be saved in its own `.tex` file.

Each main section must be assembled by combining the paragraph-level `.tex` files using `\input{...}`.

Create a master LaTeX file that inputs the section files.

For each section, include a table summarizing the references used. The table should support easy fact-checking and should include, where available:

* citation key
* authors
* year
* study focus
* EEG channel configuration
* dataset used
* method/model
* key finding
* limitation or critique

At the end of the test pipeline, compile the LaTeX document.

## 6. BibTeX requirements

Generate a BibTeX file for all cited studies used in the test section.

Use citation keys in the format:

```latex
\cite{author_year_hash}
```

Ensure that every citation used in the LaTeX has a corresponding BibTeX entry.

## 7. Dataset-comparison section

Create an additional section comparing results across different public datasets and studies, but only for studies relevant to the test scope:

**Theme A — Limited Number of EEG Electrodes — Single-channel EEG**

This section should compare:

* which public datasets were used,
* how performance differs across datasets,
* whether models generalize across datasets,
* whether single-channel EEG results are directly comparable,
* what limitations arise from dataset imbalance, protocol differences, labeling differences, or validation differences.

## 8. Test-run scope

This is only a pipeline test.

Do not process all themes yet.

Only process:

**Theme A: Limited Number of EEG Electrodes**
**Subtheme: Single-channel EEG**

The goal is to verify that the pipeline works end-to-end before running the full literature-review generation.

## 9. Expected outputs

Create the following local outputs:

1. Filtered list of relevant studies for the test theme/subtheme.
2. Extracted `chatgpt_response` summaries for those studies.
3. Saved writing-agent prompts.
4. Saved consistency-checking prompts.
5. Saved consistency-checking reports.
6. Paragraph-level LaTeX files.
7. Section-level LaTeX file using `\input{...}`.
8. Master LaTeX file.
9. Reference-summary table in LaTeX.
10. Dataset-comparison section in LaTeX.
11. BibTeX file using citation keys of the form `author_year_hash`.
12. Compiled PDF.
13. A short pipeline log explaining which studies were selected, how they were filtered, and whether the consistency checks passed.

## 10. Quality-control criteria

The test is successful only if:

* the correct studies are selected for the target theme and subtheme;
* only `chatgpt_response` content is used as the evidence source;
* the writing is critical rather than merely descriptive;
* every paragraph is saved as a separate `.tex` file;
* each section combines paragraph files through `\input{...}`;
* citations and BibTeX entries are consistent;
* each paragraph passes the consistency check or is revised until it passes;
* the final LaTeX document compiles successfully.
