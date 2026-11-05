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

export const Bstack = async ({ client, directory }) => ({
  "tool.execute.before": async (input, output) => {
    if (!["bash", "shell"].includes(input.tool)) return
    const payload = { toolName: "bash", toolArgs: output.args, sessionID: input.sessionID, callID: input.callID, cwd: directory }
    let decision = run(GUARD, payload)
    if (decision.permissionDecision === "deny") throw new Error(decision.permissionDecisionReason)
    if (!decision.modifiedArgs) return
    try {
      const result = await client.session.messages({
        path: { id: input.sessionID },
        query: { limit: 20 },
        signal: AbortSignal.timeout(1500),
      })
      const models = new Set((result.data ?? []).filter((message) =>
        message.info.role === "assistant" && message.info.sessionID === input.sessionID &&
        typeof message.info.providerID === "string" && message.info.providerID.length > 0 &&
        typeof message.info.modelID === "string" && message.info.modelID.length > 0 &&
        message.parts.some((part) => part.type === "tool" && part.callID === input.callID)
      ).map((message) => `${message.info.providerID}/${message.info.modelID}`))
      if (models.size === 1) decision = run(GUARD, { ...payload, response_model: [...models][0] })
    } catch {}
    output.args.command = decision.modifiedArgs.command
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
