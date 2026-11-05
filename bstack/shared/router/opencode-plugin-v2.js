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

export default {
  id: "bstack",
  async setup(ctx) {
    await ctx.tool.hook("execute.before", async (event) => {
      if (!["bash", "shell"].includes(event.tool)) return
      const payload = { toolName: "bash", toolArgs: event.input, sessionID: event.sessionID, callID: event.id }
      let decision = run(GUARD, payload)
      if (decision.permissionDecision === "deny") throw new Error(decision.permissionDecisionReason)
      if (!decision.modifiedArgs) return
      try {
        const messages = await Promise.race([
          ctx.session.context({ sessionID: event.sessionID }),
          new Promise((_, reject) => setTimeout(() => reject(new Error("Model lookup timed out")), 1500)),
        ])
        const message = messages.find((item) => item.type === "assistant" && item.id === event.messageID &&
          item.content.some((part) => part.type === "tool" && part.id === event.id))
        if (typeof message?.model?.providerID === "string" && message.model.providerID.length > 0 &&
            typeof message.model.id === "string" && message.model.id.length > 0) decision = run(GUARD, {
          ...payload, response_model: `${message.model.providerID}/${message.model.id}`,
        })
      } catch {}
      event.input.command = decision.modifiedArgs.command
    })
    if (!AUTO) return
    for (const [name, hook] of [["context", "chat.system.transform"], ["compaction", "session.compacting"]]) {
      await ctx.session.hook(name, (event) => {
        const text = reminder(hook, event.sessionID)
        if (text) event.system.push({ type: "text", text })
      })
    }
  },
}
