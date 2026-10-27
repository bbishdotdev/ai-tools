import json
from pathlib import Path
import subprocess
import sys

root = Path(__file__).resolve().parents[3]
recipes = json.loads((Path(__file__).parent / "recipes.json").read_text())
results = []
for recipe in recipes:
    run = subprocess.run([sys.executable, "-m", "invoices", *recipe["args"]], cwd=root, capture_output=True, text=True)
    output = run.stdout.strip()
    results.append({"name": recipe["name"], "args": recipe["args"], "output": output,
                    "passed": run.returncode == 0 and output == recipe["expect"]})
    print(("PASS " if results[-1]["passed"] else "FAIL ") + recipe["name"])
(root / ".verify").mkdir(exist_ok=True)
(root / ".verify/last-run.json").write_text(json.dumps(results, indent=2) + "\n")
sys.exit(0 if all(item["passed"] for item in results) else 1)
