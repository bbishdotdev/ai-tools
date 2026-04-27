import { execFileSync } from "node:child_process";
import { mkdirSync, rmSync, writeFileSync } from "node:fs";
import { join } from "node:path";

const contextDir = ".agent-context";
const issueDir = join(contextDir, "issues");
const repo = requiredEnv("GITHUB_REPOSITORY");
const prNumber = requiredEnv("PR_NUMBER");

rmSync(contextDir, { recursive: true, force: true });
mkdirSync(issueDir, { recursive: true });

const prJson = ghJson(["pr", "view", prNumber, "--repo", repo, "--json", "title,body,files,commits,headRefName,baseRefName,url"]);
writeFileSync(join(contextDir, "pr.json"), `${JSON.stringify(prJson, null, 2)}\n`);

const candidateIssueNumbers = extractIssueNumbers(prJson);
const issueNumbers = candidateIssueNumbers.filter((issueNumber) => !isPullRequestNumber(issueNumber));
writeFileSync(join(contextDir, "issue-numbers.txt"), `${issueNumbers.join("\n")}\n`);

if (issueNumbers.length > 0) {
  for (const issueNumber of issueNumbers) {
    const issueJson = ghJson([
      "issue",
      "view",
      issueNumber,
      "--repo",
      repo,
      "--json",
      "number,title,body,comments,labels,milestone,state,url",
    ]);
    writeFileSync(join(issueDir, `${issueNumber}.json`), `${JSON.stringify(issueJson, null, 2)}\n`);
  }
}

const diff = gh(["pr", "diff", prNumber, "--repo", repo]);
writeFileSync(join(contextDir, "pr.diff"), diff);

try {
  const checks = ghJson(["pr", "checks", prNumber, "--repo", repo, "--json", "name,state,link,description,workflow"]);
  writeFileSync(join(contextDir, "checks.json"), `${JSON.stringify(checks, null, 2)}\n`);
} catch {
  writeFileSync(join(contextDir, "checks.json"), "[]\n");
}

console.log(`issue_numbers=${issueNumbers.join(",")}`);

function extractIssueNumbers(prJson) {
  const text = [
    prJson.title,
    prJson.body,
    ...(prJson.commits ?? []).flatMap((commit) => [
      commit.messageHeadline,
      commit.messageBody,
    ]),
  ]
    .filter(Boolean)
    .join("\n");

  const issueNumbers = new Set();
  const pattern = /(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?|refs?)\s+#(\d+)/gi;
  for (const match of text.matchAll(pattern)) {
    issueNumbers.add(match[1]);
  }

  return [...issueNumbers].sort((left, right) => Number(left) - Number(right));
}

function ghJson(args) {
  return JSON.parse(gh(args));
}

function isPullRequestNumber(issueNumber) {
  const issue = ghJson(["api", `repos/${repo}/issues/${issueNumber}`]);
  return Boolean(issue.pull_request);
}

function gh(args) {
  return execFileSync("gh", args, {
    encoding: "utf8",
    env: process.env,
    stdio: ["ignore", "pipe", "pipe"],
  });
}

function requiredEnv(name) {
  const value = process.env[name];
  if (!value) {
    throw new Error(`Missing required environment variable: ${name}`);
  }

  return value;
}
