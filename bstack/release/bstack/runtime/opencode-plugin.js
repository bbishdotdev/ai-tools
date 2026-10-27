import { spawnSync } from "node:child_process"

const HOOK = __BSTACK_HOOK__
const GUARD = __BSTACK_GUARD__
const AUTO = __BSTACK_AUTO__

function run(command, payload) {
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

function reminder(event, sessionID) {
  return run(`${HOOK} --event ${event}`, { hook_event_name: event, sessionID }).additionalContext
}

export const Bstack = async () => ({
  "tool.execute.before": async (input, output) => {
    if (input.tool !== "bash") return
    const decision = run(GUARD, { toolName: "bash", toolArgs: { command: output.args?.command ?? "" } })
    if (decision.permissionDecision === "deny") throw new Error(decision.permissionDecisionReason)
  },
  ...(AUTO
    ? {
        "experimental.chat.system.transform": async (input, output) => {
          const text = reminder("chat.system.transform", input.sessionID)
          if (text) output.system.push(text)
        },
        "experimental.session.compacting": async (input, output) => {
          const text = reminder("session.compacting", input.sessionID)
          if (text) output.context.push(text)
        },
      }
    : {}),
})
