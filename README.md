\# Test Task - Pipeline Design

\## Overview

This project implements a data generation and validation pipeline that produces synthetic documents containing various Sensitive Information Types (SIT).  
The system automatically generates text and formatted files (.txt, .docx, .pdf, .eml) with sensitive and non-sensitive data, and validates them using regular expressions and heuristics.

---

\## Project Structure

\```
test_pipeline_design/
│
├── config.json               \# Main configuration file with SIT definitions and parameters
├── modules/
│   ├── meta_generator.py     \# Generates metadata (mapping_meta) describing SIT and test case distribution
│   ├── content_generator.py  \# Generates document text content based on metadata
│   ├── postprocessor.py      \# Converts generated text into multiple file formats
│   └── validator.py          \# Validates generated files and produces a report
│
├── output/
│   ├── files/                \# All generated document files
│   ├── mapping_meta.csv      \# SIT-to-document mapping table
│   ├── mapping_final.xlsx    \# Final mapping summary
│   ├── generation.log        \# Generation log
│   ├── meta.json
│   └── validation_report.txt \# Validation report
│
├── templates/    \# All templates
├── requirements.txt
├── show_sit_samples.py
└── README.md
\```

---

\## Setup

Create a virtual environment and install dependencies:

\```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
\```

\## Execution Order

Run the modules strictly in the following order:

\```bash
python modules/meta_generator.py
python modules/content_generator.py
python modules/postprocessor.py
python modules/validator.py
\```

Each module uses the output from the previous stage and writes results to the `output/` directory.

---

\## Module Descriptions

\### meta_generator.py

Generates metadata (mapping_meta.csv) describing which SITs and test categories will appear in each document.

\### content_generator.py

Creates synthetic text files containing the defined SIT patterns and random contextual content.

\### postprocessor.py

Converts generated text files into different file formats (.txt, .docx, .pdf, .eml, and others) to simulate realistic data diversity.

\### validator.py

Checks all generated documents using SIT regex patterns defined in `config.json`.  
Produces `validation_report.txt`, summarizing:

* True Positives (TP)
* False Positives (FP)
* Missing SIT occurrences

---

\## Validation

Run the validation step:

\```bash
python modules/validator.py
\```

Then review the report:

\```
output/validation_report.txt
\```

Example output snippet:

\```
SIT: SIT_SSN
  TP missing count: 10
  FP flagged count: 0
------------------------------------------------------------
SIT: SIT_DRIVER_US
  FP flagged count: 10
  sample matches: ['XXXXXXX']
\```

---

\## Configuration

Adjust parameters in `config.json` to control generation behavior:

* `"per_sit_count"` defines how many documents to generate per SIT.
* `"formats"` defines which document formats to produce.
* `"sits"` contains all SIT definitions and regular expressions.
* `"output"` section defines output file locations.
