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
  amp.on("tool.call", async (event, ctx) => {
    const shell = amp.helpers.shellCommandFromToolCall(event)
    if (!shell) return { action: "allow" }
    const payload = { toolName: "bash", toolArgs: { command: shell.command }, threadId: event.thread.id, toolUseID: event.toolUseID }
    let decision = run(GUARD, payload)
    if (decision.permissionDecision === "deny") return { action: "reject-and-continue", message: decision.permissionDecisionReason }
    if (!decision.modifiedArgs) return { action: "allow" }
    try {
      const messages = await Promise.race([
        ctx.thread.messages({ full: true, from: "end", limit: 20, roles: ["assistant"] }),
        new Promise<never>((_, reject) => setTimeout(() => reject(new Error("Model lookup timed out")), 1500)),
      ])
      const models = new Set(messages.flatMap((message) =>
        message.role === "assistant" && message.content.some((part) => part.type === "tool_use" && part.id === event.toolUseID)
          ? [message.usage?.model] : []
      ))
      if (models.size === 1) decision = run(GUARD, { ...payload, response_model: [...models][0] })
    } catch {}
    const key = typeof event.input.cmd === "string" ? "cmd" : "command"
    return { action: "modify", input: { ...event.input, [key]: decision.modifiedArgs.command } }
  })
  if (!AUTO) return
  amp.on("agent.start", async (event) => {
    const text = run(`${HOOK} --event agent.start`, { hook_event_name: "agent.start", threadId: event.thread.id })
      .additionalContext
    return text ? { message: { content: text, display: false } } : undefined
  })
}
