---
name: verify-invoices
description: Drive the real invoices CLI against sample data and record evidence. Use after changing CLI behavior.
---

# Verify invoices

Run `python3 .agents/skills/verify-invoices/drive.py` from the project root. It runs each recipe in `recipes.json` through the real CLI, compares the output, and writes `.verify/last-run.json`.

## Recipes

- **summary-default**: `summary fixtures/sample.csv` prints the invoice count and total.

Add or update a recipe in `recipes.json` when user-facing CLI output changes. Keep one recipe per user path.
