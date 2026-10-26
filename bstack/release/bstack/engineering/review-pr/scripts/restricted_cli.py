import json
from pathlib import Path

from contracts import ReviewError, canonical
from host import command, read_json, write_json
from repo_browser import TOOL_DEFINITIONS

CODEX_DISABLED_FEATURES = (
    "shell_tool", "unified_exec", "apps", "plugins", "remote_plugin", "browser_use",
    "browser_use_external", "browser_use_full_cdp_access", "computer_use", "in_app_browser",
    "in_app_local_automation", "image_generation", "view_image", "memories", "multi_agent",
    "multi_agent_v2", "goals", "code_mode", "code_mode_only",
    "workspace_dependencies", "realtime_conversation", "sleep_tool", "skill_search", "hooks",
)

CLAUDE_SETTINGS = {
    "disableAllHooks": True,
    "autoMemoryEnabled": False,
    "claudeMdExcludes": ["**"],
    "enabledPlugins": {},
}


def toml_value(value):
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False)
    if type(value) is bool:
        return "true" if value else "false"
    if type(value) is int:
        return str(value)
    if isinstance(value, list):
        return "[" + ",".join(toml_value(item) for item in value) + "]"
    if isinstance(value, dict):
        return "{" + ",".join(toml_value(key) + "=" + toml_value(item) for key, item in value.items()) + "}"
    raise ReviewError("Restricted review configuration contains an unsupported value")


def browser_server(work):
    config = read_json(work / "mcp.json")
    if not isinstance(config, dict) or set(config) != {"mcpServers"} or not isinstance(config["mcpServers"], dict):
        raise ReviewError("Restricted review requires its generated MCP configuration")
    servers = config["mcpServers"]
    if set(servers) - {"bstack_repo"}:
        raise ReviewError("Restricted review permits only the bundled repository browser")
    if not servers:
        return None
    server = servers["bstack_repo"]
    if (not isinstance(server, dict) or set(server) - {"command", "args", "env"}
            or not isinstance(server.get("command"), str) or not server["command"]
            or not isinstance(server.get("args"), list) or any(not isinstance(arg, str) for arg in server["args"])
            or ("env" in server and (not isinstance(server["env"], dict)
                or any(not isinstance(key, str) or not isinstance(value, str) for key, value in server["env"].items())))):
        raise ReviewError("The generated repository browser command is invalid")
    return {**server, "required": True, "enabled_tools": sorted(TOOL_DEFINITIONS),
            "default_tools_approval_mode": "approve"}


def restricted_model_catalog(role, work, project, launcher_argv):
    try:
        catalog = json.loads(command(launcher_argv(project, "codex", ["debug", "models"]), cwd=work, timeout=30))
        if not isinstance(catalog, dict) or not isinstance(catalog.get("models"), list):
            raise ValueError("Invalid model catalog")
        selected = [item for item in catalog["models"] if isinstance(item, dict) and item.get("slug") == role["model"]]
        if len(selected) != 1:
            raise ValueError("The exact selected model was not found once")
        metadata = {**selected[0], "apply_patch_tool_type": None,
                    "experimental_supported_tools": [], "multi_agent_version": None}
        destination = work / "restricted-model-catalog.json"
        write_json(destination, {**catalog, "models": [metadata]})
        return destination
    except (ReviewError, OSError, ValueError, TypeError) as error:
        raise ReviewError(f"Cannot prepare restricted Codex review for {role['model']}. Update or sign in to Codex, check the exact model ID and .bstack/model-clis.json launcher, then run doctor --live. No model was substituted") from error


def build_command(role, schema, work, project, launcher_argv):
    work = Path(work)
    server = browser_server(work)
    if role["cli"] == "codex":
        catalog = restricted_model_catalog(role, work, project, launcher_argv)
        values = {
            "model_reasoning_effort": role["effort"], "project_doc_max_bytes": 0,
            "web_search": "disabled", "agents.enabled": False,
            "model_catalog_json": str(catalog),
            **{"features." + name: False for name in CODEX_DISABLED_FEATURES},
            "features.skip_host_skill_discovery": True,
            "features.code_mode_host": str(read_json(catalog)["models"][0].get("tool_mode") or "").startswith("code_mode"),
        }
        args = ["exec", "--ignore-user-config", "--ignore-rules", "--ephemeral", "--strict-config",
                "--skip-git-repo-check", "--json", "--sandbox", "read-only", "--model", role["model"]]
        for key, value in values.items():
            args.extend(["-c", key + "=" + toml_value(value)])
        args.extend(["-c", "mcp_servers.bstack_repo=" + toml_value(server) if server else "mcp_servers={}"])
        args.extend(["--output-schema", str(work / "schema.json"), "--output-last-message", str(work / "answer.json"), "-"])
        return launcher_argv(project, "codex", args)
    if role["cli"] == "claude":
        args = ["--print", "--restricted", "--tools", "", "--permission-mode", "dontAsk",
                "--permission-prompts", "none", "--setting-sources", "", "--strict-mcp-config",
                "--mcp-config", str(work / "mcp.json"), "--disable-slash-commands",
                "--settings", canonical(CLAUDE_SETTINGS), "--no-session-persistence", "--no-chrome",
                "--model", role["model"], "--effort", role["effort"], "--output-format", "json",
                "--json-schema", canonical(schema)]
        if server:
            args.extend(["--allowedTools", "mcp__bstack_repo__*"])
        return launcher_argv(project, "claude", args)
    raise ReviewError("Restricted PR review supports only Codex and Claude model CLIs")
