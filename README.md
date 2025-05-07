---

# 🤖 Automating Research Workflows with LLMs

This repository provides a modular framework for using **Large Language Models (LLMs)** to automate key stages of academic and technical research — from literature filtering and methodology extraction to drafting summaries and generating BibTeX files.

> ⚡ Powered by OpenAI, Google Gemini, and agentic pipelines.

---

## 🧭 What This Project Does

This repo helps researchers and engineers offload repetitive or complex research tasks to LLM agents. Example tasks include:

* 🔍 Filtering and classifying research papers
* 📄 Extracting methodology details from full texts or abstracts
* 📊 Summarizing results into structured tables
* ✍️ Drafting literature review sections from combined findings
* 📚 Exporting final selections to `.bib` files for citation

All components are **LLM-augmented**, and designed to work with your own corpus of PDFs, abstracts, and filtered Excel files.

---

## 🛠️ Environment Setup

This project supports both `conda` and `virtualenv`. Choose your preferred setup:

### 🐍 With Conda

```bash
conda create --name crewai-flows python=3.12
conda activate crewai-flows
```

### 🌀 With Virtualenv

```bash
pip install virtualenv
virtualenv -p python3.12 myenv
```

Activate:

* Windows: `myenv\Scripts\activate`
* macOS/Linux: `source myenv/bin/activate`

---

## 📁 Project Structure

```
project_root/
├── execution_guide.ipynb                 # Install dependencies & setup API keys
├── helper/                               # Utility functions (e.g., combine_json.py)
├── setting/                              # Project path configs
├── requirements.txt                      # Python dependencies
└── .env                                  # API keys (see notebook for how to create)
```

> 💡 The actual installation and API configuration steps are detailed in `execution_guide.ipynb `.

---

## 🔐 API Keys Required

To use LLMs (OpenAI or Gemini), you’ll need API keys. The notebook provides exact setup instructions, including how to store them safely in a `.env` file.

---

## 🧠 LLM Applications Included

| Step | Task                           | Output                             |
| ---- | ------------------------------ | ---------------------------------- |
| 5–6  | Filter papers (Excel)          | LLM-augmented relevance            |
| 9    | Extract methodology            | JSON (1 per paper)                 |
| 10   | Combine JSON & draft summaries | Combined insights / narrative      |
| 11   | Export to BibTeX               | `.bib` for LaTeX or citation tools |

---

## 📓 Getting Started

Start with the notebook:

```
main.ipynb
```

It walks you through:

* Installing packages
* Creating a `.env` file for API keys
* Testing your LLM setup

---