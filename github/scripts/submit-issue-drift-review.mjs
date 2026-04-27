import { execFileSync } from "node:child_process";
import { existsSync, readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";

const contextDir = ".agent-context";
const repo = requiredEnv("GITHUB_REPOSITORY");
const prNumber = requiredEnv("PR_NUMBER");
const reviewPath = join(contextDir, "review.json");
const issueNumbersPath = join(contextDir, "issue-numbers.txt");

if (!existsSync(issueNumbersPath)) {
  throw new Error("Missing issue number context. Run collect-issue-drift-context.mjs first.");
}

const issueNumbers = readFileSync(issueNumbersPath, "utf8")
  .split("\n")
  .map((line) => line.trim())
  .filter(Boolean);

if (issueNumbers.length === 0) {
  const body = [
    "## Issue Drift Review",
    "",
    "No tagged GitHub issues were found in the PR title, body, or commit messages. Skipping issue drift review.",
  ].join("\n");
  submitReview("COMMENT", body);
  process.exit(0);
}

if (!existsSync(reviewPath)) {
  const body = [
    "## Issue Drift Review",
    "",
    "Tagged issues were found, but no agent review output was produced.",
    "",
    "Configure the issue drift reviewer runner so it reads `.github/agents/pr-issue-drift-reviewer.md` and writes `.agent-context/review.json`.",
  ].join("\n");
  submitReview("REQUEST_CHANGES", body);
  throw new Error("Missing .agent-context/review.json from issue drift reviewer agent.");
}

const review = JSON.parse(readFileSync(reviewPath, "utf8"));
const event = normalizeEvent(review.event);
const body = String(review.body ?? "").trim();
const comments = normalizeInlineComments(review.comments);

if (!body) {
  throw new Error("Issue drift review body is empty.");
}

submitReview(event, body, comments);

if (event === "REQUEST_CHANGES") {
  console.log("Issue drift review requested changes. Review state is blocking; workflow completed successfully.");
}

function submitReview(event, body, comments = []) {
  const bodyPath = join(contextDir, "submitted-review.md");
  writeFileSync(bodyPath, `${body}\n`);

  if (comments.length > 0) {
    submitReviewWithInlineComments(event, body, comments);
    return;
  }

  const args = ["pr", "review", prNumber, "--repo", repo, "--body-file", bodyPath];
  if (event === "REQUEST_CHANGES") {
    args.push("--request-changes");
  } else if (event === "APPROVE") {
    args.push("--approve");
  } else {
    args.push("--comment");
  }

  execFileSync("gh", args, {
    encoding: "utf8",
    env: process.env,
    stdio: "inherit",
  });
}

function submitReviewWithInlineComments(event, body, comments) {
  const payloadPath = join(contextDir, "submitted-review.json");
  const payload = {
    event,
    body,
    comments: comments.map((comment) => ({
      path: comment.path,
      line: comment.line,
      side: "RIGHT",
      body: comment.body,
    })),
  };

  writeFileSync(payloadPath, `${JSON.stringify(payload, null, 2)}\n`);

  execFileSync("gh", ["api", `repos/${repo}/pulls/${prNumber}/reviews`, "--method", "POST", "--input", payloadPath], {
    encoding: "utf8",
    env: process.env,
    stdio: "inherit",
  });
}

function normalizeInlineComments(comments) {
  if (!Array.isArray(comments)) {
    return [];
  }

  return comments
    .map((comment) => ({
      path: String(comment?.path ?? "").trim(),
      line: Number(comment?.line),
      body: String(comment?.body ?? "").trim(),
    }))
    .filter((comment) => comment.path && Number.isInteger(comment.line) && comment.line > 0 && comment.body);
}

function normalizeEvent(event) {
  if (event === "COMMENT" || event === "REQUEST_CHANGES" || event === "APPROVE") {
    return event;
  }

  throw new Error(`Invalid review event: ${event}`);
}

function requiredEnv(name) {
  const value = process.env[name];
  if (!value) {
    throw new Error(`Missing required environment variable: ${name}`);
  }

  return value;
}
