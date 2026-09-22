#!/usr/bin/env python3
"""Scan overlapping PRs, prepare a reviewable bundle, and explicitly publish it.

No command pushes a branch. Only ``publish --write`` changes GitHub state.
Semantic review is agent-authored data; shared paths never imply a conflict.
"""

import argparse
import datetime
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import uuid
from urllib.parse import quote

VERSION = 1
MAX_PRS = 500
MAX_BYTES = 50 * 1024 * 1024
VISUAL = re.compile(r"<!--\s*bstack-visual:([A-Za-z0-9_-]+)\s*-->")
DISPOSITIONS = {"clear", "related", "duplicate", "contradiction", "hard-conflict"}
WARNINGS = {"duplicate", "contradiction", "hard-conflict"}


class Error(Exception):
    def __init__(self, code, message, **details):
        super().__init__(message)
        self.code, self.details = code, details


def fail(code, message, **details):
    raise Error(code, message, **details)


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def read_json(path):
    try:
        data = Path(path).read_bytes()
        if len(data) > MAX_BYTES:
            raise ValueError("too large")
        return json.loads(data)
    except (OSError, ValueError) as exc:
        fail("invalid_file", f"Cannot read JSON file: {path}", detail=str(exc))


def write_file(path, data, exclusive=False):
    path = Path(path)
    flags = os.O_WRONLY | os.O_CREAT | (os.O_EXCL if exclusive else os.O_TRUNC)
    fd = os.open(path, flags, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


def write_json(path, value, exclusive=False):
    write_file(path, json.dumps(value, ensure_ascii=False, indent=2) + "\n", exclusive)


def save_state(directory, state):
    temporary = directory / (".publication-" + uuid.uuid4().hex + ".tmp")
    write_json(temporary, state, exclusive=True)
    os.replace(temporary, directory / "publication.json")
    fd = os.open(directory, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def text_value(value, label):
    if not isinstance(value, str) or not value.strip() or "\x00" in value:
        fail("validation", f"{label} must be nonempty text")
    return value


def identity(value):
    return {"ref": value.get("ref"), "sha": value.get("sha"),
            "repo": (value.get("repo") or {}).get("full_name")}


def metadata(pr):
    return {"number": pr["number"], "url": pr["html_url"], "title": pr["title"],
            "body": pr.get("body") or "", "state": pr["state"], "draft": pr.get("draft", False),
            "updatedAt": pr.get("updated_at"), "head": identity(pr["head"]), "base": identity(pr["base"])}


def fingerprint(prs, excluded=()):
    return digest(sorted([item for item in prs if item["number"] not in excluded], key=lambda item: item["number"]))


class GitHub:
    def __init__(self, repo, host="github.com"):
        if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo):
            fail("validation", "--repo must be owner/repo")
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9.-]*", host):
            fail("validation", "Invalid GitHub host")
        self.repo, self.host = repo, host

    def run(self, args, cwd=None):
        try:
            result = subprocess.run(["gh", *args], cwd=cwd, text=True, capture_output=True,
                                    timeout=120, env={**os.environ, "GH_HOST": self.host, "GH_PROMPT_DISABLED": "1"})
        except FileNotFoundError:
            fail("gh_missing", "Install and authenticate gh before scanning or publishing")
        except subprocess.TimeoutExpired:
            fail("gh_timeout", "gh timed out; a publication attempt may have succeeded")
        if len(result.stdout.encode()) > MAX_BYTES:
            fail("response_too_large", "GitHub response exceeds the 50 MiB read limit")
        return result

    def api(self, suffix, pages=False):
        args = ["api", "--hostname", self.host, f"repos/{self.repo}/{suffix}"]
        if pages:
            args.extend(["--paginate", "--slurp"])
        result = self.run(args)
        if result.returncode:
            fail("github_read_failed", f"GitHub read failed: {suffix}", detail=result.stderr.strip()[:2000])
        try:
            return json.loads(result.stdout)
        except ValueError:
            fail("github_read_failed", "gh returned invalid JSON")

    def pulls(self):
        pages = self.api("pulls?state=open&per_page=100", pages=True)
        if not isinstance(pages, list) or not all(isinstance(page, list) for page in pages):
            fail("github_read_failed", "Expected paginated open pull requests")
        prs = [metadata(pr) for page in pages for pr in page]
        if len({pr["number"] for pr in prs}) != len(prs):
            fail("github_read_failed", "Open PR pagination changed during the read; scan again")
        return prs

    def target(self, base, head):
        result = {}
        for role, ref in (("base", base), ("head", head)):
            value = self.api("git/ref/heads/" + quote(ref, safe=""))
            if not isinstance(value, dict) or value.get("ref") != "refs/heads/" + ref:
                fail("unsupported_target", "Target must be a pushed branch in the selected repository")
            result[role] = {"repo": self.repo, "ref": ref, "sha": value["object"]["sha"]}
        return result

    def pr(self, number):
        return metadata(self.api(f"pulls/{number}"))

    def attachments_supported(self):
        if self.host != "github.com":
            return False
        result = self.run(["pr", "edit", "--help"])
        return result.returncode == 0 and "--attach" in result.stdout


def snapshot(gh, base, head):
    return {"target": gh.target(base, head), "openPrs": gh.pulls()}


def same_head(pr, scan):
    return (pr["head"]["repo"] or "").casefold() == scan["repo"].casefold() and pr["head"]["ref"] == scan["head"]


def files_coverage(files, issues, label):
    for item in files:
        if "patch" not in item:
            issues.append(f"{label}: patch unavailable for {item.get('filename', 'unknown file')} (binary or omitted)")
        elif item.get("changes", 0) and patch_changes(item["patch"]) < item["changes"]:
            issues.append(f"{label}: patch may be truncated for {item.get('filename', 'unknown file')}")


def patch_changes(patch):
    # GitHub's patch property contains hunks, without --- / +++ file headers.
    return sum(line.startswith(("+", "-")) for line in patch.splitlines())


def scan_repository(gh, base, head, out):
    if ":" in head or ":" in base or head == base:
        fail("unsupported_target", "Use distinct pushed same-repository branch names; fork targets are unsupported")
    if Path(out).exists():
        fail("output_exists", "Scan output already exists; choose a new path")
    first = snapshot(gh, base, head)
    issues = []
    report = {"version": VERSION, "createdAt": now(), "repo": gh.repo, "host": gh.host,
              "base": base, "head": head, **first, "comparison": {}, "pullRequests": []}
    try:
        comparison = gh.api("compare/" + first["target"]["base"]["sha"] + "..." +
                            first["target"]["head"]["sha"] + "?per_page=100", pages=True)
        if not isinstance(comparison, list) or not comparison:
            fail("github_read_failed", "Comparison pages are missing")
        report["comparison"] = dict(comparison[0])
        report["comparison"]["commits"] = [commit for page in comparison for commit in page.get("commits", [])]
        files = report["comparison"].get("files", [])
        if len(files) >= 300:
            issues.append("Target comparison reaches GitHub's 300-file limit; additional files may be omitted")
        if len(report["comparison"]["commits"]) < report["comparison"].get("total_commits", 0):
            issues.append("Target comparison commit list is incomplete")
        files_coverage(files, issues, "Target")
    except Error as exc:
        issues.append("Target comparison unavailable: " + str(exc))
    if len(first["openPrs"]) > MAX_PRS:
        issues.append(f"Only the first {MAX_PRS} open PRs have detailed patches; all metadata was saved")
    for pr in first["openPrs"][:MAX_PRS]:
        detail = dict(pr)
        detail["sameHead"] = same_head(pr, report)
        try:
            raw = gh.api(f"pulls/{pr['number']}")
            if metadata(raw) != pr:
                issues.append(f"PR #{pr['number']} metadata changed during the scan")
            pages = gh.api(f"pulls/{pr['number']}/files?per_page=100", pages=True)
            if not isinstance(pages, list) or not all(isinstance(page, list) for page in pages):
                fail("github_read_failed", "Expected paginated PR files")
            detail["files"] = [item for page in pages for item in page]
            detail["changedFiles"] = raw.get("changed_files")
            if detail["changedFiles"] is None or len(detail["files"]) != detail["changedFiles"]:
                issues.append(f"PR #{pr['number']}: changed-file count is missing or incomplete")
            if len(detail["files"]) >= 3000:
                issues.append(f"PR #{pr['number']}: GitHub's 3000-file limit reached")
            files_coverage(detail["files"], issues, f"PR #{pr['number']}")
        except Error as exc:
            detail["files"] = detail.get("files", [])
            issues.append(f"PR #{pr['number']} details unavailable: {exc}")
        report["pullRequests"].append(detail)
    try:
        last = snapshot(gh, base, head)
        if last != first:
            issues.append("Branches or open PR metadata changed during the scan; rescan before publication")
    except Error as exc:
        issues.append("Final scan consistency check failed: " + str(exc))
    report["openPrFingerprint"] = fingerprint(first["openPrs"])
    report["coverage"] = {"complete": not issues, "issues": issues, "openPrs": len(first["openPrs"]),
                          "detailedPrs": len(report["pullRequests"])}
    report["scanId"] = digest(report)
    Path(out).parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    write_json(out, report, exclusive=True)
    return scan_summary(report, out)


def validate_scan(scan):
    if not isinstance(scan, dict) or scan.get("version") != VERSION or "scanId" not in scan:
        fail("invalid_scan", "Expected a version 1 scan")
    if digest({key: value for key, value in scan.items() if key != "scanId"}) != scan["scanId"]:
        fail("invalid_scan", "Scan content changed after its identity was calculated; rescan")
    return scan


def scan_summary(scan, path=None):
    return {"status": "scanned", "scanId": scan["scanId"], "path": str(Path(path).resolve()) if path else None,
            "target": scan["target"], "coverage": scan["coverage"],
            "pullRequests": [{"number": pr["number"], "url": pr["url"], "title": pr["title"],
                              "sameHead": same_head(pr, scan)} for pr in scan["openPrs"]]}


def review_scan(scan, review):
    if not isinstance(review, dict) or review.get("version") != 1 or review.get("scanId") != scan["scanId"]:
        fail("invalid_review", "Review must reference this scanId and version 1")
    rows = review.get("reviews")
    if not isinstance(rows, list):
        fail("invalid_review", "reviews must be an array")
    prs = {pr["number"]: pr for pr in scan["openPrs"] if not same_head(pr, scan)}
    seen = set()
    for row in rows:
        if not isinstance(row, dict) or type(row.get("number")) is not int or row["number"] not in prs:
            fail("invalid_review", "Each review must reference a scanned PR other than the same-head PR")
        if row["number"] in seen or row.get("disposition") not in DISPOSITIONS:
            fail("invalid_review", "Review numbers must be unique and dispositions supported")
        text_value(row.get("reason"), "Review reason")
        evidence = row.get("evidence")
        if not isinstance(evidence, list) or not evidence or not all(isinstance(item, str) and item.strip() for item in evidence):
            fail("invalid_review", "Each review needs at least one evidence string")
        seen.add(row["number"])
    return {"missing": sorted(set(prs) - seen), "findings": [row for row in rows if row["disposition"] in WARNINGS],
            "complete": scan["coverage"]["complete"] and not (set(prs) - seen)}


def review_notices(scan, review, assessment):
    prs = {pr["number"]: pr for pr in scan["openPrs"]}
    lines, details = [], []
    if assessment["findings"]:
        links = ", ".join(f"[#{row['number']}]({prs[row['number']]['url']}) ({row['disposition']})"
                          for row in assessment["findings"])
        lines.append("> Overlap review needs attention: " + links + ". This PR remains a draft.")
    if not assessment["complete"]:
        lines.append("> Overlap review is incomplete. This PR remains a draft.")
    if assessment["missing"]:
        details.append("Missing semantic review: " + ", ".join(f"[#{number}]({prs[number]['url']})" for number in assessment["missing"]) + ".")
    issues = scan["coverage"]["issues"]
    if issues:
        coverage = "\n".join("- " + issue for issue in issues[:20])
        if len(issues) > 20:
            coverage += f"\n- {len(issues) - 20} more coverage gaps are recorded in the saved scan."
        details.append(f"<details>\n<summary>Scan coverage ({len(issues)} gaps)</summary>\n\n{coverage}\n\n</details>")
    for row in review["reviews"]:
        if row["disposition"] != "clear":
            details.append(f"[#{row['number']}]({prs[row['number']]['url']}) ({row['disposition']}): {row['reason']}\n" +
                           "\n".join("- " + item for item in row["evidence"]))
    return "\n".join(lines), "\n\n".join(details)


def prepare_bundle(scan_path, review_path, title, body_path, out, media_path=None, draft=False):
    scan = validate_scan(read_json(scan_path))
    review = read_json(review_path)
    assessment = review_scan(scan, review)
    text_value(title, "Title")
    body = text_value(Path(body_path).read_text(), "Body")
    media = read_json(media_path) if media_path else []
    if not isinstance(media, list):
        fail("invalid_media", "Media must be an array")
    if len(media) > 50:
        fail("invalid_media", "GitHub accepts up to 50 attached files per command")
    entries = {}
    for item in media:
        if not isinstance(item, dict) or not re.fullmatch(r"[A-Za-z0-9_-]+", str(item.get("id", ""))):
            fail("invalid_media", "Media IDs must contain letters, numbers, underscores or hyphens")
        media_id = item["id"]
        if media_id in entries:
            fail("invalid_media", "Media IDs must be unique")
        text_value(item.get("alt"), "Media alt text")
        fallback = text_value(item.get("fallback"), "Media fallback Markdown")
        if re.search(r"!\[|<img\b|bstack-visual:", fallback, re.I):
            fail("invalid_media", "Every visual needs a plain fallback: Mermaid, a table, or text")
        file = Path(text_value(item.get("file"), "Media file"))
        if not file.is_absolute():
            file = Path(media_path).resolve().parent / file
        if not file.is_file():
            fail("invalid_media", f"Media file does not exist: {file}")
        entries[media_id] = {**item, "source": file}
    used = set(VISUAL.findall(body))
    if used != set(entries):
        fail("invalid_media", "Visual placeholders and media IDs must match exactly")
    directory = Path(out).resolve()
    if directory.exists():
        fail("output_exists", "Bundle output already exists; choose a new directory")
    directory.mkdir(parents=True, mode=0o700)
    marker = "<!-- bstack-pr:" + uuid.uuid4().hex + " -->"
    media_records = []
    if entries:
        (directory / "assets").mkdir(mode=0o700)
    for media_id, item in entries.items():
        extension = item["source"].suffix.lower()
        if not re.fullmatch(r"\.[a-z0-9]{1,10}", extension):
            extension = ".bin"
        relative = f"assets/{media_id}{extension}"
        shutil.copyfile(item["source"], directory / relative)
        os.chmod(directory / relative, 0o600)
        media_records.append({"id": media_id, "file": relative, "alt": item["alt"], "fallback": item["fallback"]})
    mapping = {item["id"]: item for item in media_records}
    warning, attention = review_notices(scan, review, assessment)
    def render(with_media):
        def visual(match):
            item = mapping[match[1]]
            fallback = item["fallback"]
            if not with_media:
                return fallback
            alt = item["alt"].replace("\\", "\\\\").replace("[", "\\[").replace("]", "\\]").replace("\n", " ")
            return f"![{alt}]({item['file']})\n\n<details>\n<summary>Text fallback</summary>\n\n{fallback}\n\n</details>"
        result = VISUAL.sub(visual, body)
        if attention:
            heading = re.search(r"^## Reviewer attention\s*$", result, re.M | re.I)
            if heading:
                result = result[:heading.end()] + "\n\n" + attention + "\n" + result[heading.end():]
            else:
                result = result.rstrip() + "\n\n## Reviewer attention\n\n" + attention
        rendered = ((warning + "\n\n") if warning else "") + result.rstrip() + "\n\n" + marker + "\n"
        if len(rendered) > 65000:
            fail("body_too_large", "Rendered PR body exceeds 65,000 characters; shorten body, findings, or visual fallbacks")
        return rendered
    write_json(directory / "scan.json", scan, True)
    write_json(directory / "review.json", review, True)
    write_file(directory / "body.source.md", body, True)
    write_file(directory / "body.fallback.md", render(False), True)
    write_file(directory / "body.media.md", render(True), True)
    write_json(directory / "media.json", media_records, True)
    bundle = {"version": VERSION, "createdAt": now(), "repo": scan["repo"], "host": scan["host"],
              "base": scan["base"], "head": scan["head"], "scanId": scan["scanId"], "title": title,
              "marker": marker, "requestedDraft": draft, "retainDraft": draft or bool(assessment["findings"]) or not assessment["complete"],
              "assessment": assessment, "files": {str(path.relative_to(directory)): hashlib.sha256(path.read_bytes()).hexdigest()
                                                    for path in directory.rglob("*") if path.is_file()}}
    write_json(directory / "bundle.json", bundle, True)
    save_state(directory, {"version": VERSION, "status": "prepared", "attempted": False, "pr": None, "events": []})
    return {"status": "prepared", "bundle": str(directory), "scanId": scan["scanId"],
            "retainDraft": bundle["retainDraft"], "assessment": assessment, "media": len(media_records)}


def load_bundle(directory):
    bundle = read_json(directory / "bundle.json")
    if bundle.get("version") != VERSION:
        fail("invalid_bundle", "Unsupported bundle version")
    for name, expected in bundle["files"].items():
        file = directory / name
        if file.resolve().is_relative_to(directory) is False or not file.is_file() or hashlib.sha256(file.read_bytes()).hexdigest() != expected:
            fail("invalid_bundle", "Bundle files changed or are missing; prepare a new bundle")
    scan = validate_scan(read_json(directory / "scan.json"))
    review = read_json(directory / "review.json")
    assessment = review_scan(scan, review)
    expected_draft = bundle["requestedDraft"] or bool(assessment["findings"]) or not assessment["complete"]
    if (bundle["scanId"] != scan["scanId"] or bundle["assessment"] != assessment or bundle["retainDraft"] != expected_draft
            or any(bundle[key] != scan[key] for key in ("repo", "host", "base", "head"))):
        fail("invalid_bundle", "Bundle does not match its scan and review")
    return bundle, scan, read_json(directory / "publication.json")


def freshness(gh, scan, owned_number=None):
    fresh = snapshot(gh, scan["base"], scan["head"])
    excluded = {owned_number} if owned_number else set()
    return (fresh["target"] == scan["target"] and
            fingerprint(fresh["openPrs"], excluded) == fingerprint(scan["openPrs"], excluded)), fresh


def owned(pr, bundle):
    return (bundle["marker"] in pr["body"] and (pr["head"]["repo"] or "").casefold() == bundle["repo"].casefold() and
            pr["head"]["ref"] == bundle["head"] and pr["base"]["ref"] == bundle["base"] and
            (pr["base"]["repo"] or "").casefold() == bundle["repo"].casefold())


def generated_media_body(body, directory):
    expected = (directory / "body.media.md").read_text()
    pattern = re.escape(expected)
    for item in read_json(directory / "media.json"):
        local = "](" + item["file"] + ")"
        if local not in expected:
            return False
        pattern = pattern.replace(re.escape(local), r"\]\(https://github\.com/user-attachments/assets/[A-Za-z0-9_-]+\)")
    return re.fullmatch(pattern, body) is not None


def check_owned_body(pr, bundle, state):
    if not owned(pr, bundle) or pr["state"] != "open":
        fail("ownership_changed", "PR marker, target, or open status changed; no further writes authorized", pr=pr["url"])
    if state.get("lastBodyHash") and digest(pr["body"]) != state["lastBodyHash"]:
        fail("body_changed", "PR body changed outside this publication; no further writes authorized", pr=pr["url"])


def publication_freshness(gh, scan, bundle, state, number):
    fresh, current = freshness(gh, scan, number)
    actual = next((item for item in current["openPrs"] if item["number"] == number), None)
    if actual is None:
        fail("ownership_changed", "Owned PR is no longer open; no further writes authorized")
    check_owned_body(actual, bundle, state)
    return fresh, actual


def event(directory, state, stage, **values):
    state.update(values)
    state["stage"] = stage
    state["events"].append({"at": now(), "stage": stage})
    save_state(directory, state)


def mutation(gh, args, directory, state, stage):
    event(directory, state, stage)
    try:
        return gh.run(args, cwd=directory)
    except Error as exc:
        state["lastError"] = {"code": exc.code, "message": str(exc)}
        save_state(directory, state)
        return subprocess.CompletedProcess(args, 1, "", str(exc))


def reconcile(gh, bundle, state):
    if state.get("pr"):
        pr = gh.pr(state["pr"]["number"])
        if not owned(pr, bundle):
            fail("ownership_changed", "Recorded PR no longer contains the bundle marker and target; no changes made", pr=pr["url"])
        return pr
    prs = gh.pulls()
    candidates = [pr for pr in prs if owned(pr, bundle)]
    if len(candidates) > 1:
        fail("ambiguous_recovery", "Multiple PRs contain this bundle marker; no changes made")
    return candidates[0] if candidates else None


def edit_body(gh, directory, bundle, state, pr, body_path, attach=False):
    check_owned_body(gh.pr(pr["number"]), bundle, state)
    args = ["pr", "edit", str(pr["number"]), "--repo", bundle["repo"], "--body-file", str(body_path)]
    if attach:
        for item in read_json(directory / "media.json"):
            args.extend(["--attach", item["file"]])
    result = mutation(gh, args, directory, state, "attaching" if attach else "restoring_body")
    actual = gh.pr(pr["number"])
    if not owned(actual, bundle):
        fail("ownership_changed", "PR marker or target changed during publication; no further edits made")
    state["lastBodyHash"] = digest(actual["body"])
    save_state(directory, state)
    return result, actual


def stale_draft(gh, directory, bundle, state, pr):
    check_owned_body(gh.pr(pr["number"]), bundle, state)
    if not pr["draft"]:
        result = mutation(gh, ["pr", "ready", str(pr["number"]), "--repo", bundle["repo"], "--undo"], directory, state, "returning_to_draft")
        pr = gh.pr(pr["number"])
        if result.returncode or not pr["draft"]:
            fail("draft_restore_failed", "Overlap review changed, but draft status could not be verified", pr=pr["url"])
    warning = "> Overlap review needs refresh. Branches or open PRs changed during publication. Keep this PR in draft.\n\n"
    fallback = (directory / "body.fallback.md").read_text()
    path = directory / "body.refresh.md"
    write_file(path, warning + fallback)
    result, actual = edit_body(gh, directory, bundle, state, pr, path)
    state["status"] = "review_stale"
    state["pr"] = {"number": actual["number"], "url": actual["url"]}
    save_state(directory, state)
    return {"status": "review_stale", "pr": actual["url"], "draft": actual["draft"],
            "warningSaved": result.returncode == 0 and actual["body"] == warning + fallback,
            "message": "Rescan and review current branches and open PRs before marking ready"}


def publish_bundle(directory, write=False, gh=None):
    directory = Path(directory).resolve()
    bundle, scan, state = load_bundle(directory)
    if not write:
        return {"status": "plan", "bundle": str(directory), "repo": bundle["repo"], "base": bundle["base"],
                "head": bundle["head"], "retainDraft": bundle["retainDraft"], "publication": state,
                "steps": ["Check branch SHAs and all open PR metadata", "Create draft with complete fallback body",
                          "Attach supported media and verify actual body", "Recheck overlap freshness before marking ready"]}
    gh = gh or GitHub(bundle["repo"], bundle["host"])
    with (directory / ".publish.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            fail("publication_busy", "Another publication is using this bundle")
        bundle, scan, state = load_bundle(directory)
        pr = reconcile(gh, bundle, state) if state["attempted"] else None
        if state["attempted"] and pr is None:
            fail("uncertain_creation", "A previous create may have succeeded; no matching open PR was found. Do not retry creation blindly")
        if pr and pr["state"] != "open":
            fail("pr_closed", "The recorded PR is closed; no changes made", pr=pr["url"])
        if pr and state.get("lastBodyHash") and digest(pr["body"]) != state["lastBodyHash"]:
            if state.get("stage") == "attaching" and generated_media_body(pr["body"], directory):
                state["lastBodyHash"] = digest(pr["body"])
                state["mediaDone"] = True
                state["mediaResult"] = "attached_recovered"
                save_state(directory, state)
            elif state.get("stage") == "restoring_body" and pr["body"] == (directory / "body.fallback.md").read_text():
                state["lastBodyHash"] = digest(pr["body"])
                save_state(directory, state)
            else:
                fail("body_changed", "PR body changed outside this publication; no changes made", pr=pr["url"])
        if pr and not state.get("lastBodyHash") and pr["body"] != (directory / "body.fallback.md").read_text():
            fail("body_changed", "Recovered PR body differs from the complete fallback; inspect it before further edits", pr=pr["url"])
        fresh, current = freshness(gh, scan, pr["number"] if pr else None)
        if pr:
            actual = next((item for item in current["openPrs"] if item["number"] == pr["number"]), None)
            if actual is None:
                fail("ownership_changed", "Owned PR is no longer open; no further writes authorized")
            check_owned_body(actual, bundle, state)
            pr = actual
        if not fresh:
            return {"status": "review_stale", "pr": pr["url"] if pr else None,
                    "message": "Target SHAs or open PR metadata changed; rescan and review before publication"}
        if not pr:
            existing = [item for item in current["openPrs"] if same_head(item, scan)]
            if existing:
                return {"status": "existing_pr", "pullRequests": [{"number": item["number"], "url": item["url"]} for item in existing],
                        "message": "Same-head PR already exists; no body or readiness changes authorized"}
            event(directory, state, "creating", attempted=True)
            result = mutation(gh, ["pr", "create", "--repo", bundle["repo"], "--base", bundle["base"],
                                  "--head", bundle["head"], "--title", bundle["title"], "--draft",
                                  "--body-file", str(directory / "body.fallback.md")], directory, state, "creating")
            pr = reconcile(gh, bundle, state)
            if pr is None:
                # The create URL may be visible before the open-PR listing catches up.
                match = re.search(r"https://[^\s]+/pull/(\d+)\b", result.stdout or "")
                if match:
                    candidate = gh.pr(int(match[1]))
                    if owned(candidate, bundle):
                        pr = candidate
            if pr is None:
                event(directory, state, "creation_uncertain", status="uncertain_creation")
                fail("uncertain_creation", "Creation could not be reconciled. The attempt is saved; retries will only recover, never create again")
            event(directory, state, "created", pr={"number": pr["number"], "url": pr["url"]}, lastBodyHash=digest(pr["body"]))
            if pr["body"] != (directory / "body.fallback.md").read_text():
                fail("body_changed", "Created PR body differs from the prepared fallback; inspect it before further writes", pr=pr["url"])
        else:
            state["pr"] = {"number": pr["number"], "url": pr["url"]}
            state["lastBodyHash"] = digest(pr["body"])
            save_state(directory, state)
        if state.get("status") in {"ready", "draft"}:
            return {"status": state["status"], "pr": pr["url"], "draft": pr["draft"], "reused": True}
        if not pr["draft"]:
            # An interrupted ready operation is safe to reconcile, but do not modify an externally readied PR.
            if state.get("stage") == "marking_ready" and not bundle["retainDraft"]:
                event(directory, state, "complete", status="ready")
                return {"status": "ready", "pr": pr["url"], "draft": False, "reused": True}
            fail("readiness_changed", "PR was marked ready outside this publication; no changes made", pr=pr["url"])
        media = read_json(directory / "media.json")
        if media and not state.get("mediaDone"):
            if gh.attachments_supported():
                result, pr = edit_body(gh, directory, bundle, state, pr, directory / "body.media.md", attach=True)
                if result.returncode or not generated_media_body(pr["body"], directory):
                    restored, pr = edit_body(gh, directory, bundle, state, pr, directory / "body.fallback.md")
                    if pr["body"] != (directory / "body.fallback.md").read_text():
                        fail("fallback_restore_failed", "Media upload was incomplete and the full fallback could not be verified", pr=pr["url"])
                    state["mediaResult"] = "fallback_after_upload_failure"
                else:
                    state["mediaResult"] = "attached"
            else:
                state["mediaResult"] = "fallback_attach_unavailable"
            state["mediaDone"] = True
            save_state(directory, state)
        fresh, pr = publication_freshness(gh, scan, bundle, state, pr["number"])
        if not fresh:
            return stale_draft(gh, directory, bundle, state, pr)
        if not bundle["retainDraft"]:
            result = mutation(gh, ["pr", "ready", str(pr["number"]), "--repo", bundle["repo"]], directory, state, "marking_ready")
            pr = gh.pr(pr["number"])
            check_owned_body(pr, bundle, state)
            fresh, pr = publication_freshness(gh, scan, bundle, state, pr["number"])
            if not fresh:
                return stale_draft(gh, directory, bundle, state, pr)
            if pr["draft"]:
                fail("ready_failed", "PR exists with its body, but ready status could not be verified", pr=pr["url"])
        event(directory, state, "complete", status="draft" if pr["draft"] else "ready", lastBodyHash=digest(pr["body"]))
        return {"status": state["status"], "pr": pr["url"], "draft": pr["draft"],
                "media": state.get("mediaResult", "none")}


class Parser(argparse.ArgumentParser):
    def error(self, message):
        fail("validation", message)


def main(argv=None):
    try:
        parser = Parser(description=__doc__)
        commands = parser.add_subparsers(dest="command", required=True)
        scan = commands.add_parser("scan", help="Save pushed branch comparison and every open PR")
        scan.add_argument("--repo", required=True)
        scan.add_argument("--host", default="github.com")
        scan.add_argument("--base", required=True)
        scan.add_argument("--head", required=True)
        scan.add_argument("--out", type=Path, required=True)
        show = commands.add_parser("show", help="Read a saved scan or one PR's full details")
        show.add_argument("--scan", type=Path, required=True)
        selection = show.add_mutually_exclusive_group()
        selection.add_argument("--number", type=int)
        selection.add_argument("--target", action="store_true")
        selection.add_argument("--full", action="store_true")
        prepare = commands.add_parser("prepare", help="Render a self-contained publication bundle")
        for flag in ("scan", "review", "body", "out"):
            prepare.add_argument("--" + flag, type=Path, required=True)
        prepare.add_argument("--title", required=True)
        prepare.add_argument("--media", type=Path)
        prepare.add_argument("--draft", action="store_true")
        publish = commands.add_parser("publish", help="Plan, or explicitly publish, a saved bundle")
        publish.add_argument("--bundle", type=Path, required=True)
        publish.add_argument("--write", action="store_true")
        args = parser.parse_args(argv)
        if args.command == "scan":
            result = scan_repository(GitHub(args.repo, args.host), args.base, args.head, args.out)
        elif args.command == "show":
            value = validate_scan(read_json(args.scan))
            if args.full:
                result = value
            elif args.target:
                result = {"scanId": value["scanId"], "target": value["target"],
                          "comparison": value["comparison"], "coverage": value["coverage"]}
            elif args.number is not None:
                result = next((pr for pr in value["pullRequests"] if pr["number"] == args.number), None)
                if result is None:
                    fail("pr_not_scanned", "PR details are not present in this scan")
            else:
                result = scan_summary(value, args.scan)
        elif args.command == "prepare":
            result = prepare_bundle(args.scan, args.review, args.title, args.body, args.out, args.media, args.draft)
        else:
            result = publish_bundle(args.bundle, args.write)
        print(canonical({"ok": True, "value": result}))
        return 0
    except Error as exc:
        print(canonical({"ok": False, "error": {"code": exc.code, "message": str(exc), **exc.details}}))
        return 1
    except (OSError, KeyError, TypeError, ValueError) as exc:
        print(canonical({"ok": False, "error": {"code": "invalid_input", "message": str(exc)}}))
        return 1


if __name__ == "__main__":
    sys.exit(main())
