import { readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";

const contextDir = process.env.ISSUE_DRIFT_AGENT_CONTEXT ?? ".agent-context";
const outputPath = process.env.ISSUE_DRIFT_AGENT_OUTPUT ?? join(contextDir, "review.json");
const instructionsPath =
  process.env.ISSUE_DRIFT_AGENT_INSTRUCTIONS ?? ".github/agents/pr-issue-drift-reviewer.md";
const issueDir = join(contextDir, "issues");
const issueNumbersPath = join(contextDir, "issue-numbers.txt");
const model = process.env.ISSUE_DRIFT_MODEL ?? "gpt-5.4-mini";
const maxDiffChars = Number(process.env.ISSUE_DRIFT_MAX_DIFF_CHARS ?? 180_000);
const maxIssueChars = Number(process.env.ISSUE_DRIFT_MAX_ISSUE_CHARS ?? 40_000);
const maxPrChars = Number(process.env.ISSUE_DRIFT_MAX_PR_CHARS ?? 25_000);
const maxChecksChars = Number(process.env.ISSUE_DRIFT_MAX_CHECKS_CHARS ?? 20_000);
const maxReviewChars = Number(process.env.ISSUE_DRIFT_MAX_REVIEW_CHARS ?? 4_000);
const maxInlineComments = Number(process.env.ISSUE_DRIFT_MAX_INLINE_COMMENTS ?? 10);

const issueNumbers = readLines(issueNumbersPath);
const issues = issueNumbers.map((issueNumber) =>
  readJson(join(issueDir, `${issueNumber}.json`), undefined),
).filter(Boolean);
const checks = readJson(join(contextDir, "checks.json"), []);

if (issueNumbers.length === 0) {
  writeReview("COMMENT", noIssueBody());
  process.exit(0);
}

if (!process.env.OPENAI_API_KEY) {
  writeReview("COMMENT", baselineIssueReviewBody(issues, checks));
  process.exit(0);
}

const review = await runOpenAiReview();
writeReview(normalizeEvent(review.event), String(review.body ?? "").trim(), review.comments);

async function runOpenAiReview() {
  const response = await fetch("https://api.openai.com/v1/chat/completions", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${process.env.OPENAI_API_KEY}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      model,
      messages: [
        {
          role: "system",
          content: [
            readText(instructionsPath),
            "",
            "You must return only JSON matching the requested schema. Do not wrap it in Markdown.",
          ].join("\n"),
        },
        {
          role: "user",
          content: buildReviewPrompt(),
        },
      ],
      response_format: {
        type: "json_schema",
        json_schema: {
          name: "issue_drift_review",
          strict: true,
          schema: {
            type: "object",
            additionalProperties: false,
            required: ["event", "body", "comments"],
            properties: {
              event: {
                type: "string",
                enum: ["COMMENT", "REQUEST_CHANGES", "APPROVE"],
              },
              body: {
                type: "string",
                minLength: 1,
                maxLength: maxReviewChars,
              },
              comments: {
                type: "array",
                maxItems: maxInlineComments,
                items: {
                  type: "object",
                  additionalProperties: false,
                  required: ["path", "line", "body"],
                  properties: {
                    path: {
                      type: "string",
                      minLength: 1,
                    },
                    line: {
                      type: "integer",
                      minimum: 1,
                    },
                    body: {
                      type: "string",
                      minLength: 1,
                      maxLength: 1_200,
                    },
                  },
                },
              },
            },
          },
        },
      },
    }),
  });

  if (!response.ok) {
    const errorBody = await response.text();
    throw new Error(`OpenAI review request failed (${response.status}): ${errorBody}`);
  }

  const payload = await response.json();
  const content = payload.choices?.[0]?.message?.content;
  if (!content) {
    throw new Error("OpenAI review response did not include message content.");
  }

  return JSON.parse(content);
}

function buildReviewPrompt() {
  const prJson = truncate(readText(join(contextDir, "pr.json")), maxPrChars, "pr.json");
  const diff = truncate(readText(join(contextDir, "pr.diff")), maxDiffChars, "pr.diff");
  const checksJson = truncate(readText(join(contextDir, "checks.json")), maxChecksChars, "checks.json");
  const issueBlocks = issues.map((issue) => {
    const issueJson = truncate(JSON.stringify(issue, null, 2), maxIssueChars, `issue #${issue.number}`);
    return [
      `## Issue #${issue.number}: ${issue.title}`,
      "",
      "```json",
      issueJson,
      "```",
    ].join("\n");
  });

  return [
    "Review this pull request for issue drift.",
    "",
    "Only use the provided context. If evidence is absent, mark the requirement as missing, partial, or manual verification needed.",
    "If you request changes, make the requested action specific enough for the author to fix or intentionally defer.",
    "Write for product owners first and engineers second. Explain expected outcome, observed behavior, product/business impact, evidence, and needed action.",
    "Format each blocking gap as a readable mini-card with separate Expected, Observed, Impact, Evidence, and Needed bullets.",
    "Keep the review body compact. Summarize aligned requirements in one sentence. Detail only blocking gaps or important manual verification.",
    `The review body must be ${maxReviewChars} characters or fewer.`,
    `You may include up to ${maxInlineComments} inline comments for actionable findings tied to changed lines.`,
    "For REQUEST_CHANGES, include inline comments for blocking gaps with concrete changed-file evidence whenever you can confidently anchor them.",
    "Inline comments must use { path, line, body }, where line is a right-side line number visible in the PR diff.",
    "Inline comment bodies must still explain the product/business impact before technical evidence.",
    "If a finding is about missing code or cannot be anchored to a changed line, keep it in the top-level body instead.",
    "",
    "# PR metadata",
    "",
    "```json",
    prJson,
    "```",
    "",
    "# Tagged issues",
    "",
    ...issueBlocks,
    "",
    "# Check results",
    "",
    "```json",
    checksJson,
    "```",
    "",
    "# PR diff",
    "",
    "```diff",
    diff,
    "```",
  ].join("\n");
}

function writeReview(event, body, comments = []) {
  const normalizedEvent = normalizeEvent(event);
  const normalizedBody = limitReviewBody(body.trim());

  if (!normalizedBody) {
    throw new Error("Issue drift review body is empty.");
  }

  const finalEvent =
    normalizedEvent === "APPROVE" && process.env.ISSUE_DRIFT_ALLOW_APPROVE !== "true"
      ? "COMMENT"
      : maybeDowngradeBlockingEvent(normalizedEvent);

  const finalBody =
    normalizedEvent === "APPROVE" && finalEvent === "COMMENT"
      ? `${normalizedBody}\n\n_Approval was downgraded to COMMENT because ISSUE_DRIFT_ALLOW_APPROVE is not enabled._`
      : normalizedBody;

  writeFileSync(
    outputPath,
    `${JSON.stringify(
      {
        event: finalEvent,
        body: finalBody,
        comments: normalizeInlineComments(comments),
      },
      null,
      2,
    )}\n`,
  );
}

function normalizeInlineComments(comments) {
  if (!Array.isArray(comments)) {
    return [];
  }

  return comments
    .slice(0, maxInlineComments)
    .map((comment) => ({
      path: String(comment?.path ?? "").trim(),
      line: Number(comment?.line),
      body: limitCommentBody(String(comment?.body ?? "").trim()),
    }))
    .filter((comment) => comment.path && Number.isInteger(comment.line) && comment.line > 0 && comment.body);
}

function limitCommentBody(body) {
  const maxCommentChars = 1_200;
  if (body.length <= maxCommentChars) {
    return body;
  }

  return `${body.slice(0, maxCommentChars - 20).trimEnd()}\n\n_[truncated]_`;
}

function maybeDowngradeBlockingEvent(event) {
  if (event !== "REQUEST_CHANGES") {
    return event;
  }

  if (process.env.ISSUE_DRIFT_MODE === "advisory") {
    return "COMMENT";
  }

  return event;
}

function baselineIssueReviewBody(issues, checks) {
  const reviewed = issues.map((issue) => `#${issue.number}`).join(", ");
  const checksSeen = checks.length === 0 ? "not available" : `${checks.length} check(s)`;

  return [
    "## Issue Drift Review",
    "",
    `Reviewed: ${reviewed}`,
    "",
    "Semantic issue-drift analysis did not run because `OPENAI_API_KEY` is missing.",
    "",
    `Checks seen: ${checksSeen}.`,
    "",
    "Required follow-up: add `OPENAI_API_KEY` as a GitHub Actions repository secret.",
  ].join("\n");
}

function noIssueBody() {
  return [
    "## Issue Drift Review",
    "",
    "No tagged GitHub issues were found in the PR title, body, or commit messages. Skipping issue drift review.",
  ].join("\n");
}

function readLines(path) {
  try {
    return readText(path)
      .split("\n")
      .map((line) => line.trim())
      .filter(Boolean);
  } catch {
    return [];
  }
}

function readJson(path, fallback) {
  try {
    return JSON.parse(readText(path));
  } catch {
    return fallback;
  }
}

function readText(path) {
  return readFileSync(path, "utf8");
}

function truncate(value, maxChars, label) {
  if (value.length <= maxChars) {
    return value;
  }

  const omitted = value.length - maxChars;
  const headLength = Math.floor(maxChars * 0.65);
  const tailLength = maxChars - headLength;
  return [
    value.slice(0, headLength),
    `\n\n[${label} truncated: ${omitted} characters omitted]\n\n`,
    value.slice(value.length - tailLength),
  ].join("");
}

function limitReviewBody(body) {
  if (body.length <= maxReviewChars) {
    return body;
  }

  const notice = `_[Review truncated to ${maxReviewChars} characters by ISSUE_DRIFT_MAX_REVIEW_CHARS. Ask the reviewer to focus on blocking gaps if this hides needed detail.]_`;
  const bodyLimit = Math.max(0, maxReviewChars - notice.length - 2);

  return [
    body.slice(0, bodyLimit).trimEnd(),
    "",
    notice,
  ].join("\n");
}

function normalizeEvent(event) {
  if (event === "COMMENT" || event === "REQUEST_CHANGES" || event === "APPROVE") {
    return event;
  }

  throw new Error(`Invalid review event: ${event}`);
}
