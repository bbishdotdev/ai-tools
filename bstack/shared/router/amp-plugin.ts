import { spawnSync } from "node:child_process"
import type { PluginAPI } from "@ampcode/plugin"

export const description = "bstack routing reminder and PR creation guard"

const HOOK = __BSTACK_HOOK__
const GUARD = __BSTACK_GUARD__
const AUTO = __BSTACK_AUTO__

function run(command: string, payload: object) {
  const result = spawnSync("/bin/sh", ["-c", command], {
    input: JSON.stringify(payload),
    encoding: "utf8",
    timeout: 5000,
  })
  try {
    return JSON.parse(result.stdout || "{}")
  } catch {
    return {}
  }
}

export default function (amp: PluginAPI) {
  amp.on("tool.call", async (event) => {
    const shell = amp.helpers.shellCommandFromToolCall(event)
    if (!shell) return { action: "allow" }
    const decision = run(GUARD, { toolName: "bash", toolArgs: { command: shell.command } })
    return decision.permissionDecision === "deny"
      ? { action: "reject-and-continue", message: decision.permissionDecisionReason }
      : { action: "allow" }
  })
  if (!AUTO) return
  amp.on("agent.start", async (event) => {
    const text = run(`${HOOK} --event agent.start`, { hook_event_name: "agent.start", threadId: event.thread.id })
      .additionalContext
    return text ? { message: { content: text, display: false } } : undefined
  })
}
