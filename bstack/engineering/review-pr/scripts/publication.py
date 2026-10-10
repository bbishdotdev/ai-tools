from collections import defaultdict
from datetime import datetime, timezone
from urllib.parse import quote

from contracts import ReviewError, digest
from host import read_json, write_json
from shared import compatible_receipt, matching_context, public_receipt, receipts, source_record


LABELS = {"blocker": "🛑", "human-decision": "❓", "moderate": "⚠️", "low": "💡"}


def now():
    return datetime.now(timezone.utc).isoformat()


def signature(result):
    roles = result["config"]["roles"]
    return (f"Independently reviewed by {roles['reviewer_a']['model']} and {roles['reviewer_b']['model']}. "
            f"Finalized by {roles['adjudicator']['model']}.")


def evidence_link(result, evidence):
    if evidence["path"] == "@pr":
        return result["snapshot"]["pr"]["html_url"]
    target = result["snapshot"]["target"]
    commit = result["evidence_commits"][evidence["side"]]
    return f"https://{target['host']}/{target['repo']}/blob/{commit}/{quote(evidence['path'], safe='/')}#L{evidence['line']}"


def evidence_links(result, evidence):
    urls = list(dict.fromkeys(evidence_link(result, item) for item in evidence))
    return " ".join(f"[Evidence{'' if len(urls) == 1 else ' ' + str(index + 1)}]({url})" for index, url in enumerate(urls))


def desired_event(result):
    categories = {item["category"] for item in result["findings"]}
    new_ids = set(result.get("new_findings", [item["id"] for item in result["findings"]]))
    new_categories = {item["category"] for item in result["findings"] if item["id"] in new_ids}
    if "blocker" in new_categories:
        return "REQUEST_CHANGES"
    if "human-decision" in new_categories:
        return "COMMENT"
    if categories & {"blocker", "human-decision"}:
        return None
    if result["status"] != "complete" or not result.get("coverage", {"complete": True})["complete"]:
        return "COMMENT"
    return "APPROVE"


def assessment_details(result):
    text = []
    new_ids = set(result.get("new_findings", [item["id"] for item in result["findings"]]))
    for item in result["findings"]:
        if item["id"] not in new_ids:
            continue
        text.append(f"{LABELS[item['category']]} **{item['title']}**\n\n{item['explanation']} {item['action']} {evidence_links(result, item['evidence'])}")
    limits = result.get("coverage", {}).get("limits", [])
    if limits:
        text.append("**Still unverified**\n\n" + "\n".join("- " + limit for limit in dict.fromkeys(limits)))
    replied = {name for item in result.get("feedback", []) if item["relation"] == "resolved" for name in item["finding_ids"]}
    resolved = [item["title"] for item in result.get("resolved_findings", []) if item["id"] not in replied]
    if resolved:
        text.append("✅ Fixed: " + "; ".join(resolved) + ".")
    return text


def summary_body(result, event, self_review):
    intended = desired_event(result)
    if intended == "APPROVE":
        text = ["✅ Looks good. GitHub won't let me formally approve my own PR." if self_review else "✅ Looks good."]
    elif intended == "REQUEST_CHANGES":
        text = ["🛑 These changes need attention before merging."]
    elif result["status"] == "partial":
        text = ["⚠️ Here's what I could verify. A few gaps still need checking."]
    else:
        text = ["❓ There's a decision to make before merging."]
    text.extend(assessment_details(result))
    if result["scope"]["mode"] != "full":
        text.append("Checked the follow-up and the behavior it affects.")
    text.append(signature(result))
    return "\n\n".join(text)


def source_url(result, kind, item):
    if item.get("html_url"):
        return item["html_url"]
    prefix = {"reviews": "pullrequestreview-", "comments": "issuecomment-", "inline": "discussion_r"}[kind]
    return result["snapshot"]["pr"]["html_url"] + "#" + prefix + str(item["id"])


def reviewed_commit_url(result):
    target = result["snapshot"]["target"]
    return f"https://{target['host']}/{target['repo']}/commit/{result['evidence_commits']['head']}"


def action(result, kind, destination, body=None, **values):
    identity = digest({"kind": kind, "destination": destination, "body": body, **values})[:24]
    marker = f"<!-- bstack-review-action:{result['run_id']}:{identity} -->"
    value = {"id": identity, "kind": kind, "destination": destination, "marker": marker, "status": "pending", **values}
    if body is not None:
        value["visible_body"] = body
        value["body"] = body.rstrip() + "\n\n" + marker
    return value


def plan_actions(result, user):
    discussion = result["snapshot"]["discussion"]
    sources = {(kind, item["id"]): item for kind, items in discussion.items() for item in items}
    responses = defaultdict(list)
    actions = []
    for feedback in result.get("feedback", []):
        kind, identity = feedback["kind"], feedback["id"]
        source = sources.get((kind, identity))
        if source is None:
            raise ReviewError("A feedback target is no longer present in the reviewed discussion")
        if feedback["relation"] == "agree":
            if source.get("author", "").casefold() != user.casefold():
                actions.append(action(result, "reaction", {"kind": kind, "id": identity}, source=source))
            continue
        root = source
        seen = set()
        while kind == "inline" and root.get("in_reply_to_id"):
            if root["id"] in seen or (kind, root["in_reply_to_id"]) not in sources:
                raise ReviewError("The inline review thread has an invalid parent")
            seen.add(root["id"])
            root = sources[(kind, root["in_reply_to_id"])]
        target = root["id"] if kind == "inline" else identity
        prefix = {"extend": "⚠️", "disagree": "💬", "resolved": "✅"}[feedback["relation"]]
        mention = "@" + source["author"] + " " if source.get("author") and source["author"].casefold() != user.casefold() else ""
        body = f"{prefix} {mention}{feedback['body'].strip()}"
        if feedback["relation"] == "resolved":
            references = []
            if kind != "inline":
                label = "Earlier review" if kind == "reviews" else "Earlier comment"
                references.append(f"[{label}]({source_url(result, kind, source)})")
            references.append(f"[Reviewed commit]({reviewed_commit_url(result)})")
            body += "\n\n" + " · ".join(references)
        else:
            if kind != "inline":
                body += f" [Earlier {'review' if kind == 'reviews' else 'comment'}]({source_url(result, kind, source)})"
            links = evidence_links(result, feedback.get("evidence", []))
            if links:
                body += " " + links
        responses[(kind, target)].append(body)
    timeline = []
    timeline_sources = []
    for (kind, identity), bodies in responses.items():
        if kind == "inline":
            actions.append(action(result, "reply", {"kind": kind, "id": identity}, "\n\n".join([*bodies, signature(result)])))
        else:
            timeline.extend(bodies)
            timeline_sources.append({"kind": kind, "id": identity})
    event = desired_event(result)
    self_review = user.casefold() == result["snapshot"]["pr"]["author"].casefold()
    actual = "COMMENT" if self_review and event else event
    if actual:
        body = summary_body(result, actual, self_review)
        if timeline:
            body = body.removesuffix(signature(result)).rstrip() + "\n\n" + "\n\n".join([*timeline, signature(result)])
        actions.append(action(result, "review", {"kind": "reviews", "pr": result["snapshot"]["target"]["number"]}, body, event=actual))
    else:
        updates = [*assessment_details(result), *timeline]
        if updates:
            actions.append(action(result, "comment", {"kind": "comments", "sources": timeline_sources}, "\n\n".join([*updates, signature(result)])))
    return actions, actual


def item_record(kind, item):
    author = item.get("author") or (item.get("user") or {}).get("login")
    value = {**item, "author": author}
    return {**source_record(kind, value), "url": item.get("html_url"), "state": item.get("state")}


def echoes(journal):
    return [{key: item["receipt"][key] for key in ("kind", "id", "author", "body_digest")}
            for item in journal["actions"] if item["kind"] != "reaction" and item.get("receipt")]


def graph(github, query, **variables):
    result = github.api("graphql", data={"query": query, "variables": variables}, global_path=True)
    if not isinstance(result, dict) or result.get("errors") or not isinstance(result.get("data"), dict):
        raise ReviewError("GitHub could not confirm the review reaction")
    return result["data"]


def reaction_present(github, item, user):
    source, destination = item["source"], item["destination"]
    if destination["kind"] != "reviews":
        prefix = "issues" if destination["kind"] == "comments" else "pulls"
        reactions = github.api(f"{prefix}/comments/{destination['id']}/reactions?per_page=100", pages=True)
        return next((entry for entry in reactions if entry.get("content") == "+1" and (entry.get("user") or {}).get("login", "").casefold() == user.casefold()), None)
    node = source.get("node_id")
    if not node:
        raise ReviewError("GitHub did not provide a node ID for the review reaction")
    cursor = None
    while True:
        data = graph(github, "query($id:ID!,$cursor:String){node(id:$id){... on PullRequestReview{reactions(first:100,after:$cursor,content:THUMBS_UP){nodes{id user{login}} pageInfo{hasNextPage endCursor}}}}}", id=node, cursor=cursor)
        connection = (data.get("node") or {}).get("reactions")
        if not isinstance(connection, dict):
            raise ReviewError("GitHub did not return the review's reactions")
        match = next((entry for entry in connection["nodes"] if (entry.get("user") or {}).get("login", "").casefold() == user.casefold()), None)
        if match or not connection["pageInfo"]["hasNextPage"]:
            return match
        cursor = connection["pageInfo"]["endCursor"]
        if not cursor:
            raise ReviewError("GitHub returned incomplete reaction pagination")


def reconcile_action(item, state, github, user, head):
    if item["kind"] == "reaction":
        reaction = reaction_present(github, item, user)
        return {"id": reaction["id"]} if reaction else None
    kind = "reviews" if item["kind"] == "review" else "inline" if item["kind"] == "reply" else "comments"
    for candidate in state["discussion"][kind]:
        if item["marker"] not in (candidate.get("body") or "") or candidate.get("author", "").casefold() != user.casefold():
            continue
        if candidate["body"] != item["body"]:
            raise ReviewError("A published review action was edited; reassess before posting again")
        if item["kind"] == "review":
            if candidate.get("commit_id") != head:
                raise ReviewError("The existing review action belongs to a different commit")
            expected = {"APPROVE": {"APPROVE", "APPROVED"}, "REQUEST_CHANGES": {"REQUEST_CHANGES", "CHANGES_REQUESTED"}, "COMMENT": {"COMMENT", "COMMENTED"}}[item["event"]]
            if candidate.get("state", "").upper() not in expected:
                raise ReviewError("The existing review status changed or was dismissed; reassess before posting again")
        if item["kind"] == "reply" and candidate.get("in_reply_to_id") != item["destination"]["id"]:
            raise ReviewError("The existing review reply belongs to a different thread")
        return item_record(kind, candidate)
    return None


def execute_action(item, result, github):
    destination = item["destination"]
    number = result["snapshot"]["target"]["number"]
    if item["kind"] == "reaction":
        if destination["kind"] == "reviews":
            return graph(github, "mutation($id:ID!,$client:String!){addReaction(input:{subjectId:$id,content:THUMBS_UP,clientMutationId:$client}){reaction{id}}}", id=item["source"]["node_id"], client=item["marker"])["addReaction"]["reaction"]
        prefix = "issues" if destination["kind"] == "comments" else "pulls"
        return github.api(f"{prefix}/comments/{destination['id']}/reactions", data={"content": "+1"})
    if item["kind"] == "review":
        return github.api(f"pulls/{number}/reviews", data={"body": item["body"], "event": item["event"], "commit_id": result["snapshot"]["pr"]["head"]["sha"]})
    path = f"pulls/{number}/comments/{destination['id']}/replies" if item["kind"] == "reply" else f"issues/{number}/comments"
    return github.api(path, data={"body": item["body"]})


def equivalent(result, value):
    def findings(items):
        return sorted(digest({key: value for key, value in item.items() if key != "id"}) for item in items)
    return (value["verdict"] == result["verdict"] and value["coverage"] == result["coverage"]
            and findings(value["findings"]) == findings(result["findings"]))


def assert_fresh(result, journal, state, checks):
    pr = state["pr"]
    if pr["state"] != "open" or pr.get("merged") or pr.get("mergeable") is False or pr.get("mergeable_state") == "dirty":
        raise ReviewError("The PR is closed or has merge conflicts; reassess before publishing")
    if not matching_context(result, state, checks, extra_ignored=echoes(journal)):
        raise ReviewError("Review is stale: code, requirements, checks or discussion changed. Run a follow-up review before publishing.")


def completed_response(journal, stale=False, repeated=False):
    review = next((item for item in journal["actions"] if item["kind"] == "review" and item.get("receipt")), None)
    status = "already_published" if repeated else "published"
    if stale:
        status += "_stale" if repeated else "_but_stale"
    value = {"status": status, "event": journal.get("event"), "actions": len(journal["actions"])}
    if review:
        value.update({"url": review["receipt"].get("url"), "state": review["receipt"].get("state")})
    if stale:
        value["warning"] = "The PR changed during publication. This review covers the earlier snapshot; run a follow-up review."
    return value


def publish_result(result, directory, github, write):
    directory = directory.resolve()
    if result.get("stale"):
        raise ReviewError("Review is stale; run a follow-up before publishing")
    saved = directory / "publication.json"
    user = github.api("user", global_path=True)["login"]
    head = result["snapshot"]["pr"]["head"]["sha"]
    state, checks = github.state(), github.checks(head)
    journal = read_json(saved) if saved.exists() else {}
    if journal and "actions" not in journal:
        marker = f"<!-- bstack-review:{result['run_id']}:{head} -->"
        old = next((item for item in state["discussion"]["reviews"] if marker in (item.get("body") or "") and item.get("commit_id") == head and item.get("author", "").casefold() == user.casefold()), None)
        if old:
            return {"status": "already_published", "url": old.get("html_url"), "state": old.get("state")}
        if journal.get("status") in {"sending", "uncertain", "published"}:
            raise ReviewError("A prior publication may have succeeded. Reconcile it before posting again.")
        journal = {}
    if journal:
        if journal.get("result_digest") != result["digest"] or journal.get("actor", "").casefold() != user.casefold():
            raise ReviewError("This publication belongs to a different assessment or GitHub account")
        for item in journal["actions"]:
            receipt = reconcile_action(item, state, github, user, head)
            if receipt:
                item.update({"status": "done", "receipt": receipt})
            elif item["status"] in {"done", "sending", "uncertain"}:
                raise ReviewError("A prior review action is missing or uncertain. Reconcile it before posting again.")
        write_json(saved, journal)
        if all(item["status"] == "done" for item in journal["actions"]):
            stale = not matching_context(result, state, checks, extra_ignored=echoes(journal))
            return completed_response(journal, stale=stale, repeated=True)
    else:
        for record in receipts(state, github):
            if compatible_receipt(record, state, checks, result["config_digest"], result["policy_digest"]) and equivalent(result, record["receipt"]):
                return {"status": "already_reviewed", "url": record["source"]["url"], "author": record["source"]["author"], "event": None}
        actions, event = plan_actions(result, user)
        journal = {"version": 1, "actor": user, "run_id": result["run_id"], "result_digest": result["digest"], "status": "planned", "event": event, "actions": actions}
    assert_fresh(result, journal, state, checks)
    for item in journal["actions"]:
        if item["kind"] == "review" and item["status"] == "pending":
            receipt = public_receipt({**result, "publication_echoes": echoes(journal)}, item["visible_body"] + "\n\n" + item["marker"])
            item["body"] = item["visible_body"] + "\n\n" + item["marker"] + ("\n\n" + receipt if receipt else "")
    review = next((item for item in journal["actions"] if item["kind"] == "review"), None)
    preview = {"status": "preview", "event": journal["event"], "actions": journal["actions"], "body": review["body"] if review else "", "run": str(directory)}
    write_json(directory / "publication-preview.json", preview)
    if not write:
        return {**preview, "body": "\n\n".join(item["visible_body"] for item in journal["actions"] if item.get("visible_body")), "actions": [{key: value for key, value in item.items() if key not in {"body", "marker", "source", "receipt"}} for item in journal["actions"]]}
    write_json(saved, journal)
    for item in journal["actions"]:
        if item["status"] == "done":
            continue
        state, checks = github.state(), github.checks(head)
        assert_fresh(result, journal, state, checks)
        existing = reconcile_action(item, state, github, user, head)
        if existing:
            item.update({"status": "done", "receipt": existing})
            write_json(saved, journal)
            continue
        if item["kind"] == "review":
            visible = item["visible_body"] + "\n\n" + item["marker"]
            receipt = public_receipt({**result, "publication_echoes": echoes(journal)}, visible)
            item["body"] = visible + ("\n\n" + receipt if receipt else "")
        item["status"] = "sending"
        journal["status"] = "sending"
        write_json(saved, journal)
        try:
            response = execute_action(item, result, github)
            if not isinstance(response, dict) or not response.get("id"):
                raise ReviewError("GitHub did not return an action receipt")
            if item["kind"] == "reaction":
                receipt = {"id": response["id"]}
            else:
                kind = "reviews" if item["kind"] == "review" else "inline" if item["kind"] == "reply" else "comments"
                if response.get("body") != item["body"] or (response.get("user") or {}).get("login", "").casefold() != user.casefold():
                    raise ReviewError("GitHub returned an unexpected action author or body")
                if item["kind"] == "review" and (response.get("commit_id") != head or not response.get("state")):
                    raise ReviewError("GitHub returned an unexpected review commit or state")
                receipt = item_record(kind, response)
            item.update({"status": "done", "receipt": receipt})
            write_json(saved, journal)
        except Exception as exc:
            item["status"] = "uncertain"
            journal.update({"status": "uncertain", "error": str(exc)})
            write_json(saved, journal)
            raise ReviewError("Publication is uncertain. Retry to reconcile the existing action before posting anything else.") from exc
    journal.update({"status": "published", "published_at": now()})
    write_json(saved, journal)
    state, checks = github.state(), github.checks(head)
    stale = not matching_context(result, state, checks, extra_ignored=echoes(journal))
    return completed_response(journal, stale=stale)
