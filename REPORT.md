# Where Natural Language Analytics Breaks: A Failure Taxonomy and Semantic-Layer Fix for NL-to-SQL Systems

Author: [Your Name]
Dataset: Northwind (SQLite)
Tools: Python, SQLite, Google Gemini API, Streamlit

---

## 1. Problem Statement

Natural-language-to-SQL (NL-to-SQL) tools are increasingly used to let non-technical users query business data directly, bypassing dashboards and analysts entirely. The promise is speed: ask a question in plain English, get an answer immediately.

The risk is that these systems can produce confidently wrong answers when a business term is ambiguous or undefined - "active customer," "top products," "recent trend" - because the underlying database schema contains no information about what these terms are supposed to mean. The AI does not fail loudly; it fails silently, returning a number that looks exactly as trustworthy as a correct one.

This project investigates two questions:

1. Where, specifically, does an LLM-powered NL-to-SQL pipeline break when faced with realistic business ambiguity?
2. Can a lightweight, low-cost intervention - a short glossary of business-term definitions meaningfully reduce that failure rate?

---

## 2. Objectives

- Build a working NL-to-SQL pipeline using a free LLM API (Google Gemini).
- Design a graded question bank that deliberately exposes different types of ambiguity.
- Establish verified ground-truth answers for every question and interpretation.
- Run the pipeline against these questions and measure accuracy against ground truth.
- Build a failure taxonomy categorizing why each error occurred.
- Design and test a semantic glossary as a fix, and measure its effect on accuracy.
- Report results honestly, including cases that improved but did not perfectly resolve.
 This project also tests whether semantic guidance can reduce silent failures in NL-to-SQL systems.
---

## 3. Methodology

### 3.1 Dataset

The Northwind database (SQLite) was used, containing standard e-commerce tables: `Customers`, `Orders`, `"Order Details"`, `Products`, `Categories`, `Employees`, `Suppliers`, and `Shippers`. The working copy of the dataset spans order dates from 2012 to 2023.

### 3.2 Question Bank Design

20 unique business questions were designed across five difficulty tiers, each representing a distinct type of ambiguity a real analytics team might encounter:

| Tier | Type | Example | Count |
|---|---|---|---|
| 1 | Unambiguous | "How many orders were placed in 2017?" | 4 |
| 2 | Metric-ambiguous | "Which customers are our top customers?" (by revenue? by order count?) | 4 |
| 3 | Business-context-dependent | "Which products are underperforming?" | 4 |
| 4 | Time-window-tricky | "What was our recent sales trend?" | 4 |
| 5 | Join-ambiguous | "What is the average order value per customer?" | 4 |

For Tiers 2–5, each question was paired with 2–3 competing but individually defensible interpretations, one of which was marked as the most likely default - the reading a business user would typically intend. This produced 37 total interpretation-rows across the 20 questions.

### 3.3 Ground Truth Construction

For every question and interpretation, a corresponding SQL query was hand-written and executed directly against the database (via DB Browser for SQLite), and the actual output was recorded as ground truth. 

### 3.4 Baseline Pipeline

Each of the 20 questions was sent to the Gemini API along with the database schema, with an explicit instruction to return only SQL. The returned SQL was executed against the database, and its result was logged for comparison against ground truth.

Note on this design choice: because the prompt forced SQL-only output, the AI had no mechanism to state which assumption it was making when facing an ambiguous question. This is a deliberate methodological limitation, discussed further in Section 7.

### 3.5 Taxonomy Construction

Each of the 20 baseline results was manually compared against its ground-truth interpretations and tagged as `MATCH`, `MISMATCH`, or `PARTIAL`. Every mismatch was further classified into a specific failure category (Section 5).

### 3.6 Glossary Intervention

A short glossary (approx. 150 words) was written, defining the exact ambiguous terms responsible for the 9 baseline failures (e.g., "active customer," "top," "underperforming," "recent"). This glossary was injected into the prompt - with the SQL-only output format left unchanged and only the 9 previously-failed questions were re-run, to isolate the glossary as the single variable being tested.

---

## 4. Results

### 4.1 Baseline Accuracy by Tier

| Tier | Matched Intended Default | Rate |
|---|---|---|
| 1 — Unambiguous | 4 / 4 | 100% |
| 2 — Metric-ambiguous | 3 / 4 | 75% |
| 3 — Business-context-dependent | 0 / 4 | **0%** |
| 4 — Time-window | 1 / 4 | 25% |
| 5 — Join-ambiguous | 3 / 4 | 75% |
| Overall | 11 / 20 | 55% |

Performance was strongest on unambiguous questions and weakest when business meaning had to be inferred.

### 4.2 Accuracy After the Glossary Fix

| Question | Baseline Result | Glossary Result | Outcome |
|---|---|---|---|
| Active customers | 93 (all-time — wrong) | 88 (90-day window) | Fixed |
| Underperforming products | Global average (wrong scope) | Correct per-category average | Fixed |
| Category needing attention | Inventory-based reframing | Grains/Cereals (lowest revenue) | Fixed |
| Discontinue candidates | Trivial "already flagged" reading | Correct low-sales candidates | Fixed |
| Inefficient shipping | Unrelated country/delay metric | Correct freight-ratio concept, different grouping | Improved (not exact) |
| Recent sales trend | Full history, no filter | Correct 3-month window | Fixed |
| Sales change, last few months | Full history, no filter | Correct 3-month window | Fixed |
| This month vs. last month | Unfiltered full history | Exact match, correct two months isolated | Fixed |
| Top employee per category | Ranked by quantity | Ranked by revenue (correct metric) | Fixed |

Result: 8 of 9 previously-failing questions produced exact matches. The 9th produced a methodologically valid but differently-scoped answer.

The glossary fixed most failures, especially those caused by ambiguous terms and missing time filters.

Overall accuracy: 11/20 (55%) baseline → 19/20 (95%) with glossary applied.

---

## 5. Failure Taxonomy

Six distinct failure categories emerged from the 9 baseline mismatches:

| Category | Count | Description |
|---|---|---|
| `metric_ambiguity_wrong_default` | 2 | The AI picks a valid, defensible metric — just not the one a business user would typically mean (e.g., ranking by units sold instead of revenue). |
| `unanticipated_reframing` | 2 | The AI substitutes an entirely different business question without any signal that it did so (e.g., answering an inventory question when asked a revenue question). |
| `ignored_recency_qualifier` | 2 | Words like "recent" or "the last few months" are ignored entirely; the AI returns full historical data with no time filter applied. |
| `trivial_reading_over_business_relevant` | 1 | The AI chooses the easiest, most literal reading of a question over the interpretation that would actually be useful to a business user. |
| `wrong_aggregation_scope` | 1 | The AI computes an aggregate (e.g., an average) across the wrong grouping — a global average instead of a category-relative one. |
| `unfiltered_result_scope` | 1 | The SQL technique itself is correct, but the AI does not isolate the specific period or subset the question actually asked for. |

Key finding: the AI's raw SQL-writing ability is not the bottleneck. Tier 5 (complex joins, window functions, multi-table aggregation) scored 75% at baseline - proof the model can write genuinely sophisticated SQL correctly. The failures concentrate almost entirely in Tiers 3 and 4, where business judgment, not technical capability, is required to resolve ambiguity.

---

## 6. Case Studies

### 6.1 The Silent Guess (NLQ06 — "How many active customers do we have?")

At baseline, the AI's SQL applied no time filter at all — `COUNT(DISTINCT CustomerID) FROM Orders` — silently interpreting "active" as "has ever placed an order, ever" (93 customers). The intended, business-realistic reading was a 90-day recency window (88 customers). Both numbers are plausible in isolation; only one is what a business user actually meant. Nothing in the AI's output indicated a choice had been made at all.

### 6.2 A New Interpretation the Ground Truth Didn't Anticipate (NLQ10 — "Which product category needs attention?")

Rather than choosing between the two predicted interpretations (lowest revenue, or declining trend), the AI invented a third: it flagged the category with the most products below their reorder level — an inventory-risk framing, entirely disconnected from the revenue-based question that was intended. This is a distinct and important failure mode: the AI did not fail to choose between options, it silently substituted a different business question.

### 6.3 The Limit of the Glossary (NLQ12 — "Which shipping routes are inefficient?")

Even after the glossary explicitly defined "inefficient" as a high freight-to-order-value ratio, the AI computed that ratio correctly but aggregated it by **city/country** rather than by individual order, as the ground truth had assumed. Arguably, the word "routes" supports a geographic aggregation better than the original ground truth did. This case shows a real limit of the glossary approach: it can fix what a term means, but not always what grain a result should be aggregated at — that ambiguity can survive even an explicit definition.

---

## 7. Limitations

- The prompt design suppressed explanation. Because the AI was instructed to return SQL only, it had no opportunity to state which assumption it made when facing ambiguity. This means the baseline failures reported here are a measure of silent accuracy, not of the AI's underlying reasoning quality — a differently-designed prompt that allowed the AI to state its assumptions might make the same wrong guesses "catchable" by a human reviewer, even without improving the guesses themselves. This is a natural extension for future work.
- Sample size. 20 questions is sufficient to establish a clear taxonomy but too small to produce statistically robust tier-level percentages; the 0% and 100% figures at the tier level should be read as indicative, not as precise population estimates.
- Single dataset. All results are specific to the Northwind schema and its particular scale; ambiguity patterns may differ on other schemas.

---

## 8. Business Recommendation

For any team deploying NL-to-SQL or AI-generated analytics tools on real business data:

1. Maintain a lightweight semantic glossary of commonly-used, ambiguous business terms (a plain text file is sufficient - this project's glossary was under 200 words and resolved 8 of 9 failures). This is a low-cost, low-maintenance intervention compared to retraining or fine-tuning a model.
2. Do not treat glossary coverage as complete protection. As shown in Section 6.4, some ambiguity (particularly around aggregation grain, not just term definition) can survive an explicit glossary. Spot-checking AI-generated answers against known ground truth periodically remains necessary.
3. Prefer systems that can express uncertainty over systems that only return a number. The most dangerous failure mode identified in this project was not incorrect SQL - it was silently incorrect SQL indistinguishable in format from a correct answer. A system that states its assumptions, even imperfectly, converts an invisible risk into a visible, catchable one.

---

## 9. Conclusion

Across 20 realistic business questions, a baseline NL-to-SQL pipeline matched the intended business interpretation only 55% of the time — with a complete failure rate (0%) on questions requiring business-context judgment, despite strong technical performance (75%) on questions requiring complex SQL joins. A single, inexpensive glossary of business-term definitions raised this to 95%, resolving 8 of 9 identified failures outright and meaningfully improving the 9th.This project shows that the biggest failure in AI-generated analytics is silent ambiguity, not technical SQL generation.
