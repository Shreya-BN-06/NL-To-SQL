# NL-to-SQL Failure Audit

**Where natural language analytics quietly gets your data wrong — and a low-cost fix that mostly works.**

This project audits an LLM-powered NL-to-SQL pipeline against 20 realistic business questions on the Northwind database, builds a failure taxonomy from the mistakes it makes, and tests whether a short business-term glossary can improve accuracy. A good README should quickly explain what the project does, why it matters, and how to run it.

## Headline result

- Baseline accuracy: 55% (11/20).
- With a ~150-word glossary: 95% (19/20).
- The one question that did not fully resolve is reported honestly as an improved-but-different interpretation, not rounded up.

## Why this matters

Most NL-to-SQL demos show the happy path. This project focuses on where things break: when the model returns a confident-looking answer built on the wrong business assumption. That makes it a useful portfolio project because it combines analytics, evaluation, and a practical intervention.

## What's interesting here

The model's raw SQL-writing ability was not the main problem — it handled complex multi-table joins and window functions correctly in many cases. The failures clustered around business judgment, such as what "active," "top," or "recent" actually mean in context. A tiny glossary of term definitions fixed most of those failures.

## Repo structure

```
nl-to-sql-audit/
├── REPORT.md                  # full methodology, taxonomy, results, and recommendation
├── requirements.txt
├── data/                      # database, question bank, ground truth
├── scripts/                   # baseline and glossary-fixed pipelines
├── results/                   # tagged results and before/after comparison
└── dashboard/                 # Streamlit app
```

## How to reproduce

**1. Install dependencies**
```bash
pip install -r requirements.txt
```

**2. Set up your API key**

Set your Gemini API key as an environment variable:
```bash
export GEMINI_API_KEY="your_api_key_here"
```

**3. Run the baseline pipeline**
```bash
python scripts/nl_to_sql_pipeline_phase2.py
```

**4. Run the glossary-based pipeline**
```bash
python scripts/phase4_glossary_pipeline.py
```

**5. Compare results**

The before/after comparison is saved in:
```
results/final_combined_comparison.csv
```

## Dashboard

Run the Streamlit app locally with:
```bash
cd dashboard
pip install streamlit pandas
streamlit run streamlit_app.py
```

Live dashboard:https://nl-to-sql-yvxzvbc7dcdrpthpusvjhs.streamlit.app/ 

## Key files

- `data/question_bank_final20_FIXED.xlsx`: all 20 questions, competing interpretations, and verified SQL + results.
- `data/northwind.db`: the SQLite database used for testing.
- `scripts/nl_to_sql_pipeline_phase2.py`: baseline prompt + execution pipeline.
- `scripts/phase4_glossary_pipeline.py`: glossary-enhanced rerun for failed questions.
- `results/final_combined_comparison.csv`: question-by-question before/after comparison.

## Report

Full write-up: [REPORT.md](./REPORT.md)

## Why I built this

Most NL-to-SQL demos focus on the happy path. I built this project to find where the system quietly fails, because a wrong answer that looks correct is a bigger risk in real analytics than a system that visibly breaks.
