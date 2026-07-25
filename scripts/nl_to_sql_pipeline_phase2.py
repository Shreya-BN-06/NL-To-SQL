"""
NL-to-SQL Failure Mapping — Phase 2: Run Questions Through Gemini
====================================================================

WHAT THIS SCRIPT DOES
----------------------
1. Reads your 20 unique NL questions from questions_to_run.csv.
2. Reads your database schema automatically (handles table names with
   spaces, like "Order Details", correctly).
3. Sends each question + schema to Gemini, gets back generated SQL.
4. Executes that SQL against your real database.
5. Logs everything to results_phase2_log.csv so you can manually compare
   the AI's answer against your ground_truth file, row by row.

BEFORE YOU RUN THIS
--------------------
1. pip install google-generativeai      (if not already installed)
2. Make sure these files are in the same folder:
     - your database file (edit DB_PATH below to match its name)
     - questions_to_run.csv
3. Set your Gemini API key (Colab Secrets, or environment variable, or
   paste directly into API_KEY below for quick local testing).
"""

import os
import sqlite3
import re
import csv
import time
from datetime import datetime

import google.generativeai as genai

# -------------------- CONFIG --------------------

# Try Colab secrets first (if running in Colab), else fall back to env var
try:
    from google.colab import userdata
    API_KEY = userdata.get('GEMINI_API_KEY')
except Exception:
    API_KEY = os.environ.get("GEMINI_API_KEY", "PASTE_YOUR_KEY_HERE_IF_NOT_USING_SECRETS")

DB_PATH = "northwind.db"                # <-- EDIT to match your actual database filename
QUESTIONS_CSV = "questions_to_run.csv"
RESULTS_CSV = "results_phase2_log.csv"
MODEL_NAME = "gemini-2.5-flash"   # change here if this model shows a quota error - see README steps

genai.configure(api_key=API_KEY)
model = genai.GenerativeModel(MODEL_NAME)


# -------------------- SCHEMA EXTRACTION --------------------

def get_schema(db_path: str) -> str:
    """
    Reads every table and its columns from the database.
    Table names with spaces (like "Order Details") are automatically
    quoted correctly so both the PRAGMA call and the schema text shown
    to the AI reflect the real table name.
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row[0] for row in cursor.fetchall()]

    schema_lines = []
    for table in tables:
        # Quote every table name defensively -- safe even if no space exists
        cursor.execute(f'PRAGMA table_info("{table}");')
        columns = cursor.fetchall()
        col_names = ", ".join(col[1] for col in columns)
        # Show the AI the exact quoted form it should use in generated SQL
        display_name = f'"{table}"' if " " in table else table
        schema_lines.append(f"Table {display_name}({col_names})")

    conn.close()
    return "\n".join(schema_lines)


# -------------------- PROMPT + SQL GENERATION --------------------

def build_prompt(schema: str, question: str) -> str:
    prompt = f"""You are a SQL expert. Given the database schema below, write a single
valid SQLite query that answers the question. If a table name contains a
space, it is shown here in double quotes -- use double quotes around it
in your SQL too (e.g. "Order Details"). Return ONLY the SQL code, with
no explanation, no markdown formatting, and no comments.

Schema:
{schema}

Question: {question}

SQL:"""
    return prompt


def clean_sql(raw_text: str) -> str:
    text = raw_text.strip()
    text = re.sub(r"^```sql", "", text, flags=re.IGNORECASE).strip()
    text = re.sub(r"^```", "", text).strip()
    text = re.sub(r"```$", "", text).strip()
    return text


def generate_sql(schema: str, question: str) -> str:
    prompt = build_prompt(schema, question)
    response = model.generate_content(prompt)
    return clean_sql(response.text)


# -------------------- EXECUTION --------------------

def run_sql(db_path: str, sql: str):
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(sql)
        rows = cursor.fetchall()
        conn.close()
        return True, str(rows[:15])  # cap for readability
    except Exception as e:
        return False, f"SQL ERROR: {e}"


# -------------------- MAIN PIPELINE --------------------

def run_pipeline():
    schema = get_schema(DB_PATH)
    print("Schema loaded:\n", schema, "\n")

    with open(QUESTIONS_CSV, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        questions = list(reader)

    results = []

    for row in questions:
        master_id = row.get("master_question_id", "")
        tier = row.get("tier", "")
        question = row.get("question", "")
        linked_rows = row.get("linked_ground_truth_rows", "")

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
            "linked_ground_truth_rows": linked_rows,
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "generated_sql": sql,
            "execution_success": success,
            "execution_result": output,
            "matched_interpretation": "",   # fill in manually: which ground-truth row does this match?
            "stated_assumption": "",         # fill in manually: TRUE/FALSE - did the AI say which assumption it made?
            "error_category": ""             # fill in manually during your taxonomy step
        })

        time.sleep(5)   # pause between requests to avoid hitting free-tier rate limits

    fieldnames = list(results[0].keys())
    with open(RESULTS_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    print(f"\nDone. Results saved to {RESULTS_CSV}")


if __name__ == "__main__":
    run_pipeline()
