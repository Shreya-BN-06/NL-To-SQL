"""
Phase 4 — Semantic Glossary Fix
=================================

WHAT THIS SCRIPT DOES
----------------------
Re-runs ONLY the 9 questions that failed in your Phase 2/3 baseline,
this time with a short business-term glossary injected into the prompt.
Output format is UNCHANGED from your baseline (still strict SQL-only) --
this isolates ONE variable (added context) so you can directly compare
failure rates before vs. after, without any parsing/format differences
muddying the comparison.

BEFORE RUNNING
--------------
1. Upload this script, your database file, and confirm GEMINI_API_KEY
   is set up the same way as before (Colab Secrets -> os.environ).
2. No other files needed -- the 9 failed questions are hardcoded below
   based on your tagged Phase 3 results.
"""

import os
import sqlite3
import re
import csv
import time
from datetime import datetime

import google.generativeai as genai

# -------------------- CONFIG --------------------

try:
    from google.colab import userdata
    API_KEY = userdata.get('GEMINI_API_KEY')
except Exception:
    API_KEY = os.environ.get("GEMINI_API_KEY", "PASTE_YOUR_KEY_HERE_IF_NOT_USING_SECRETS")

DB_PATH = "northwind.db"                 # <-- edit to match your database filename
RESULTS_CSV = "results_phase4_log.csv"
MODEL_NAME = "gemini-2.0-flash-lite-001"  # use whichever model worked for you in Phase 2
DELAY_SECONDS = 15

genai.configure(api_key=API_KEY)
model = genai.GenerativeModel(MODEL_NAME)


# -------------------- THE 9 FAILED QUESTIONS FROM YOUR BASELINE --------------------

FAILED_QUESTIONS = [
    {"master_question_id": "NLQ06", "tier": 2, "question": "How many active customers do we have?"},
    {"master_question_id": "NLQ09", "tier": 3, "question": "Which products are underperforming?"},
    {"master_question_id": "NLQ10", "tier": 3, "question": "Which product category needs attention?"},
    {"master_question_id": "NLQ11", "tier": 3, "question": "What products should we discontinue?"},
    {"master_question_id": "NLQ12", "tier": 3, "question": "Which shipping routes are inefficient?"},
    {"master_question_id": "NLQ14", "tier": 4, "question": "What was our recent sales trend?"},
    {"master_question_id": "NLQ15", "tier": 4, "question": "How have sales changed over the last few months?"},
    {"master_question_id": "NLQ16", "tier": 4, "question": "Compare this month's performance to last month."},
    {"master_question_id": "NLQ19", "tier": 5, "question": "Which employee sold the most of each product category?"},
]


# -------------------- THE GLOSSARY --------------------

GLOSSARY = """
- "active customer" means a customer who placed at least one order within
  the last 90 days of the most recent order date in the dataset.
- "top", "best-selling", or "sold the most" (for customers, employees, or
  products) means ranked by total REVENUE (UnitPrice * Quantity * (1 - Discount)),
  unless the question explicitly says "by quantity" or "by units".
- "underperforming" (for a product) means its total revenue is below the
  average revenue of other products in the SAME category (not the overall
  average across all products).
- "needs attention" (for a product category) means the category with the
  lowest total revenue among all categories.
- "should be discontinued" means a product with low or zero sales revenue
  that is NOT already flagged as Discontinued = 1 (exclude already-flagged
  products from this list -- we want new candidates).
- "inefficient" (for shipping) means orders where the Freight cost is high
  relative to the order's total value (a high freight-to-order-value ratio).
- "recent" or "the last few months" means the last 3 calendar months of
  data available in the dataset, unless a different window is specified.
- "this month" and "last month" mean the two most recent calendar months
  present in the OrderDate data.
"""


# -------------------- SCHEMA + SQL GENERATION --------------------

def get_schema(db_path: str) -> str:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row[0] for row in cursor.fetchall()]
    schema_lines = []
    for table in tables:
        cursor.execute(f'PRAGMA table_info("{table}");')
        columns = cursor.fetchall()
        col_names = ", ".join(col[1] for col in columns)
        display_name = f'"{table}"' if " " in table else table
        schema_lines.append(f"Table {display_name}({col_names})")
    conn.close()
    return "\n".join(schema_lines)


def build_prompt(schema: str, question: str) -> str:
    # Identical structure to your Phase 2 prompt, with ONE addition: the glossary block.
    return f"""You are a SQL expert. Given the database schema below, write a single
valid SQLite query that answers the question. If a table name contains a
space, it is shown here in double quotes -- use double quotes around it
in your SQL too (e.g. "Order Details"). Return ONLY the SQL code, with
no explanation, no markdown formatting, and no comments.

Schema:
{schema}

Business term definitions (use these to resolve any ambiguous terms in the question):
{GLOSSARY}

Question: {question}

SQL:"""


def clean_sql(raw_text: str) -> str:
    text = raw_text.strip()
    text = re.sub(r"^```sql", "", text, flags=re.IGNORECASE).strip()
    text = re.sub(r"^```", "", text).strip()
    text = re.sub(r"```$", "", text).strip()
    return text


def generate_sql(schema: str, question: str) -> str:
    response = model.generate_content(build_prompt(schema, question))
    return clean_sql(response.text)


def run_sql(db_path: str, sql: str):
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(sql)
        rows = cursor.fetchall()
        conn.close()
        return True, str(rows[:15])
    except Exception as e:
        return False, f"SQL ERROR: {e}"


# -------------------- MAIN --------------------

def run_pipeline():
    schema = get_schema(DB_PATH)
    print("Schema loaded:\n", schema, "\n")

    results = []

    for row in FAILED_QUESTIONS:
        master_id = row["master_question_id"]
        tier = row["tier"]
        question = row["question"]

        print(f"\n[{master_id} | Tier {tier}] Q: {question}")

        try:
            sql = generate_sql(schema, question)
            print("Generated SQL:", sql)
            success, output = run_sql(DB_PATH, sql)
            print("Execution result:", output)
        except Exception as e:
            sql = ""
            success = False
            output = f"PIPELINE ERROR: {e}"

        results.append({
            "master_question_id": master_id,
            "tier": tier,
            "question": question,
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "generated_sql_with_glossary": sql,
            "execution_success": success,
            "execution_result": output,
            "matched_interpretation_after_glossary": "",  # fill in manually after comparing to ground truth
            "improved_vs_baseline": "",                    # fill in manually: TRUE/FALSE/SAME
        })

        time.sleep(DELAY_SECONDS)

    fieldnames = list(results[0].keys())
    with open(RESULTS_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    print(f"\nDone. Results saved to {RESULTS_CSV}")


if __name__ == "__main__":
    run_pipeline()
