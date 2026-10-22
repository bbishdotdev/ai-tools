#!/usr/bin/env python3
import argparse
import json
from pathlib import Path
import re

import package


ROOT = Path(__file__).resolve().parents[1]
GUIDE = ROOT / "shared/skills/bstack-guide/assets/overview.html"
DATA = re.compile(r'(<script id="catalog-data" type="application/json">)(.*?)(</script>)', re.S)

SKILL_WHY = {
    "architect": "Settle risky interfaces and ownership before code locks in the wrong shape.",
    "arena": "Compare real alternatives when one attempt would be too easy to accept.",
    "blast-radius": "Find effects outside the diff before a change ships.",
    "bro": "Get the last answer in language you would use with another developer.",
    "bstack-auto": "Choose whether ordinary engineering requests enter Poteto Mode automatically.",
    "bstack-guide": "Find a useful starting point without reading the whole package.",
    "control-cli": "Prove interactive terminal behavior by driving the actual program.",
    "control-ui": "Prove UI behavior in a real browser or app surface.",
    "configure-pr": "Add a project's own PR priorities without editing shared BStack workflows.",
    "create-verification-skill": "Give a new feature a repeatable user-facing check when the project verification setting calls for it.",
    "deslop": "Remove code patterns that look plausible but add noise or fragility.",
    "domain-modeling": "Give a team shared terms and capture only consequential design choices.",
    "figure-it-out": "Shape a one-off, complex job into a checkable execution plan.",
    "grill-me": "Expose weak assumptions while the decision owner is present.",
    "grill-with-docs": "Question a design while keeping source evidence and decisions together.",
    "grilling": "Reach a sound decision by following dependent questions in order.",
    "handoff": "Move accepted work into a fresh context without losing the important bits.",
    "how": "Ground a change in what the code actually does and where it belongs.",
    "implement": "Start building from accepted scope without recreating the planning process.",
    "interrogate": "Let independent reviewers challenge a change from different angles.",
    "maintain-verification-skill": "Reconcile the whole verifier when requested; routine feature work updates only the affected path.",
    "no-comments": "Make the code explain itself without a Cursor-only named agent.",
    "poteto-mode": "Choose a full PStack engineering playbook for the current task.",
    "prototype": "Make a design or behavior choice with a cheap, disposable example.",
    "research": "Answer a bounded question from evidence before a decision depends on it.",
    "resolve-pr": "Judge review feedback before replying or changing code.",
    "review-pr": "Challenge a PR independently and filter out weak findings.",
    "setup-bstack": "Check or adjust the package and host bindings in this project.",
    "show-me-your-work": "Leave a compact decision trail for work someone must audit later.",
    "swarm": "Cover independent work in parallel and return one usable report.",
    "tdd": "Use a failing behavioral test when it is a useful way to drive the change.",
    "teach": "Combine how the code works with why it was built that way.",
    "technical-writing": "Make technical docs easier to follow and maintain.",
    "to-pr": "Give a reviewer a short, useful explanation of an authorized PR.",
    "to-questionnaire": "Get needed facts or decisions from someone who is not in the session.",
    "to-spec": "Turn settled planning into a stable implementation reference.",
    "to-tickets": "Split accepted scope into work that can be owned and verified.",
    "triage": "Avoid duplicate or contradictory work before it enters the queue.",
    "typescript-best-practices": "Catch TypeScript design and correctness issues while working in TS code.",
    "unslop": "Keep the agent's prose plain, specific, and human.",
    "verify-bstack": "Check package bindings and runtime behavior before claiming BStack works.",
    "wayfinder": "Keep connected planning questions visible across sessions.",
    "why": "Find the evidence behind a choice before proposing to reverse it.",
}

PRINCIPLE_WHY = {
    "principle-attack-the-premise": "Stop repeating fixes that assume the same broken premise.",
    "principle-boundary-discipline": "Keep validation where outside data enters the system.",
    "principle-build-the-lever": "Make nontrivial work repeatable and easier to verify.",
    "principle-encode-lessons-in-structure": "Turn repeated instructions into checks or code.",
    "principle-exhaust-the-design-space": "Compare novel options before committing to one.",
    "principle-experience-first": "Make product tradeoffs serve the person using the result.",
    "principle-fix-root-causes": "Fix the defect instead of hiding its symptom.",
    "principle-foundational-thinking": "Get the underlying data shape right before adding logic.",
    "principle-guard-the-context-window": "Keep only useful context in the main agent thread.",
    "principle-laziness-protocol": "Prefer the smallest effective change and delete extra structure.",
    "principle-make-operations-idempotent": "Let retries converge safely after partial runs.",
    "principle-migrate-callers-then-delete-legacy-apis": "Finish an internal API change without leaving duplicate paths.",
    "principle-minimize-reader-load": "Reduce the state and layers a reader must hold in mind.",
    "principle-model-the-domain": "Put state and rules in an explicit model instead of scattered branches.",
    "principle-never-block-on-the-human": "Keep reversible work moving while reserving real decisions for people.",
    "principle-outcome-oriented-execution": "Reach the intended architecture without preserving throwaway stages.",
    "principle-prove-it-works": "Check the real outcome before reporting success.",
    "principle-redesign-from-first-principles": "Test whether a new requirement changes the right implementation shape.",
    "principle-separate-before-serializing-shared-state": "Remove avoidable write contention before adding coordination.",
    "principle-sequence-verifiable-units": "Make each stage checkable before moving to the next.",
    "principle-subtract-before-you-add": "Remove dead weight before building on top of it.",
    "principle-test-behavior-not-implementation": "Keep tests tied to outcomes rather than code structure.",
    "principle-type-system-discipline": "Use types to prevent invalid states and hidden assumptions.",
}

PLAYBOOKS = {
    "authoring-a-skill": ("Write or revise an agent skill with a clear trigger and checkable result.", "Use when the deliverable is a skill, not application code."),
    "autonomous-run": ("Drive one authorized task to a completion condition without repeated prompting.", "Use for an unattended, bounded run."),
    "bug-fix": ("Reproduce a defect, find its cause, fix it, and verify the behavior.", "Use for a reported bug with code changes in scope."),
    "eval": ("Measure whether a prompt, skill, or workflow change improves agent behavior.", "Use before promoting a change based on model behavior."),
    "feature": ("Shape and implement a new behavior through design, code review, and proof.", "Use for a clear feature request in engineering scope."),
    "hillclimb": ("Iterate on one measurable target with evidence after each attempt.", "Use for sustained improvement of a metric."),
    "investigation": ("Answer a read-only code or system question from evidence.", "Use when the answer is the deliverable."),
    "opening-a-pr": ("Prepare an authorized PR through BStack's to-pr workflow.", "Use when PR delivery is part of the task."),
    "pause-safely": ("Leave a durable state for later pickup.", "Use when an in-flight task needs to stop cleanly."),
    "perf-issue": ("Trace measured slowness and verify a targeted improvement.", "Use for a specific performance defect."),
    "prototype": ("Compare disposable options through BStack's prototype workflow.", "Use when seeing a working sketch will settle a design question."),
    "refactoring": ("Change code structure while preserving its behavior.", "Use when the implementation shape needs work but product behavior does not."),
    "runtime-forensics": ("Diagnose a live runtime symptom from instrumentation.", "Use when a diagnosis, rather than a fix, is requested."),
    "session-pickup": ("Reconstruct in-flight work from a prior session or branch.", "Use to resume without restarting the investigation."),
    "trace-forensics": ("Read a captured profile or trace to explain a runtime problem.", "Use when the evidence already exists."),
    "visual-parity": ("Match an existing UI against a captured visual baseline.", "Use when the task is equivalence, not new design."),
}

RELATED = {
    "grill-me": ["grilling", "wayfinder"],
    "grill-with-docs": ["grilling", "domain-modeling"],
    "wayfinder": ["grilling", "research", "prototype", "to-spec"],
    "prototype": ["wayfinder", "handoff", "implement"],
    "to-spec": ["to-tickets", "implement"],
    "to-tickets": ["triage", "implement"],
    "implement": ["poteto-mode", "handoff", "to-pr"],
    "poteto-mode": ["how", "architect", "to-pr"],
    "to-pr": ["review-pr", "resolve-pr", "configure-pr"],
    "review-pr": ["resolve-pr"],
    "configure-pr": ["to-pr", "review-pr", "resolve-pr"],
    "how": ["why", "architect", "teach"],
    "why": ["how", "teach"],
    "domain-modeling": ["grill-with-docs", "to-spec"],
    "bstack-auto": ["poteto-mode", "bstack-router"],
}


def description(data):
    header = data.decode().split("---", 2)[1]
    lines = header.splitlines()
    for index, line in enumerate(lines):
        if not line.startswith("description:"):
            continue
        value = line.split(":", 1)[1].strip()
        if value in (">", ">-", "|", "|-"):
            return " ".join(part.strip() for part in lines[index + 1:] if part.startswith("  ")).strip()
        if value.startswith('"'):
            return json.loads(value)
        return value.strip("'")
    raise ValueError("Skill has no description")


def area(path, name):
    if name in ("to-pr", "review-pr", "resolve-pr", "configure-pr"):
        return "PR work"
    if path.startswith("sdlc/"):
        return "Planning"
    if name in ("bstack-auto", "bstack-guide", "setup-bstack", "poteto-mode"):
        return "Setup and routing"
    if name in ("handoff", "unslop", "verify-bstack"):
        return "Continuity"
    return "Engineering"


def catalog():
    release = package.assemble()
    files = {key.removeprefix("bstack/"): asset.data for key, asset in release.items() if key.startswith("bstack/")}
    index = json.loads(files["index.json"])
    manifest = json.loads(files["manifest.json"])
    public = set(manifest["public_skills"])
    principles = {name for name in index["skills"] if name.startswith("principle-")}
    if set(SKILL_WHY) != public or set(PRINCIPLE_WHY) != principles or set(PLAYBOOKS) != set(index["playbooks"]):
        raise ValueError("Guide notes no longer match the packaged catalog")
    items = []
    for name in sorted(public):
        path = index["skills"][name]
        items.append({"name": name, "kind": "skill", "area": area(path, name),
                      "what": description(files[path]), "why": SKILL_WHY[name],
                      "loading": "Always available for prose" if name == "unslop" else
                                 "Available from ordinary requests; you can also invoke it directly" if manifest["public_skills"][name]["implicit"] else
                                 "Invoke directly; a selected workflow may read it when relevant",
                      "related": RELATED.get(name, [])})
    for name in sorted(principles):
        items.append({"name": name, "kind": "principle", "area": "Engineering principles",
                      "what": description(files[index["skills"][name]]), "why": PRINCIPLE_WHY[name],
                      "loading": "Loaded by Poteto Mode when its condition applies; no direct slash command",
                      "related": []})
    for name, (what, why) in sorted(PLAYBOOKS.items()):
        items.append({"name": name, "kind": "playbook", "area": "Engineering playbooks",
                      "what": what, "why": why,
                      "loading": "Selected by Poteto Mode for a matching task; no direct slash command",
                      "related": ["to-pr"] if name == "opening-a-pr" else
                                 ["prototype"] if name == "prototype" else []})
    for name, what, why in (
        ("bstack-router", "Apply BStack's policy over selected PStack and SDLC workflows.", "Keep routing and host behavior consistent."),
        ("setup-pstack", "Compatibility name for setup-bstack.", "Keep older references working without a second setup process."),
        ("setup-matt-pocock-skills", "Compatibility name for setup-bstack.", "Keep older references working without a second setup process."),
    ):
        items.append({"name": name, "kind": "internal", "area": "Internal and aliases",
                      "what": what, "why": why,
                      "loading": "Internal reference; use setup-bstack for setup" if name != "bstack-router" else
                                 "Loaded by project instructions or the automatic routing hook when enabled",
                      "related": ["setup-bstack"] if name != "bstack-router" else ["poteto-mode"]})
    assert len(items) == len(index["skills"]) + len(index["playbooks"])
    return {"version": manifest["version"], "counts": {"skills": len(public), "principles": len(principles),
            "playbooks": len(index["playbooks"]), "internal": 3}, "items": items}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    html = GUIDE.read_text()
    data = catalog()
    records = ",\n".join("    " + json.dumps(item, ensure_ascii=False, separators=(",", ":")) for item in data["items"])
    payload = ("\n{\n  \"version\": " + json.dumps(data["version"]) +
               ",\n  \"counts\": " + json.dumps(data["counts"], separators=(",", ":")) +
               ",\n  \"items\": [\n" + records + "\n  ]\n}\n  ").replace("<", "\\u003c")
    match = DATA.search(html)
    if not match:
        raise ValueError("Guide catalog-data element missing")
    expected = html[:match.start(2)] + payload + html[match.end(2):]
    if args.check:
        if html != expected:
            raise SystemExit("Guide catalog is out of date; run bstack/scripts/guide_catalog.py")
        print("Guide catalog matches the packaged skills and playbooks")
        return
    GUIDE.write_text(expected)
    print("Updated guide catalog")


if __name__ == "__main__":
    main()
