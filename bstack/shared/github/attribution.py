import base64
from dataclasses import asdict, dataclass
import json
from pathlib import Path
import re
import shlex


HOSTS = {"codex", "claude", "cursor", "grok", "copilot", "opencode", "amp"}
EVIDENCE = {"response-model", "selected-model", "explicit", "unavailable"}
MODEL = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/+-]{0,159}")
ALIASES = {"auto", "default", "low", "smart", "rush", "deep", "free", "high", "ultra", "balanced", "balance"}
TOKEN = re.compile(
    r'''(?P<space>[ \t]+|\\\n)|(?P<separator>\n|&&|;)|'''
    r'''(?P<redirect>[0-9]*(?:>&|<&)[0-9-]+|[0-9]*(?:>>?|<)(?![<&>]))|'''
    r'''(?P<word>(?:[^\s;&|<>(){}'"`\\]+|'[^']*'|"(?:[^"\\]|\\[\s\S])*"|\\[\s\S])+)'''
)
SHELL_KEYWORDS = {"!", "[[", "]]", "if", "then", "else", "elif", "fi", "case", "esac", "for", "select",
                  "while", "until", "do", "done", "function", "time", "coproc", "in"}


class ExistingContext(ValueError):
    pass


@dataclass(frozen=True)
class Attribution:
    model: str | None
    host: str | None
    evidence: str
    reason: str | None = None

    def record(self):
        return asdict(self)


def unavailable(host, reason):
    return Attribution(None, host, "unavailable", reason)


def reported(host, model, evidence):
    if not isinstance(model, str) or not MODEL.fullmatch(model):
        return unavailable(host, "model_not_exposed")
    if model.lower().split("/")[-1] in ALIASES:
        return unavailable(host, "host_reported_model_alias")
    return Attribution(model, host, evidence)


def encode(attribution):
    return base64.urlsafe_b64encode(json.dumps(attribution.record(), separators=(",", ":")).encode()).decode()


def resolve(context=None, explicit=None):
    automatic = unavailable(None, "no_host_context")
    if context:
        try:
            if not isinstance(context, str) or len(context) > 2048:
                raise ValueError
            value = json.loads(base64.b64decode(context, altchars=b"-_", validate=True))
            if set(value) != {"model", "host", "evidence", "reason"} or value["host"] not in HOSTS:
                raise ValueError
            if value["evidence"] not in EVIDENCE - {"explicit"}:
                raise ValueError
            automatic = Attribution(**value)
            if automatic.model is None:
                if automatic.evidence != "unavailable" or not re.fullmatch(r"[a-z_]{1,80}", automatic.reason or ""):
                    raise ValueError
            elif automatic.evidence == "unavailable" or automatic.reason is not None or reported(automatic.host, automatic.model, automatic.evidence).model is None:
                raise ValueError
        except (ValueError, TypeError, KeyError):
            raise ValueError("Invalid host attribution context") from None
    if explicit is not None:
        manual = reported(None, explicit, "explicit")
        if manual.model is None:
            raise ValueError("Use an exact model identifier, not a mode, Auto, prose or markup")
        if automatic.model and automatic.model != explicit:
            raise ValueError(f"Explicit model {explicit} conflicts with host model {automatic.model}")
        if not automatic.model:
            return manual
    return automatic


def literal_word(raw):
    value, quote, index = [], None, 0
    while index < len(raw):
        character = raw[index]
        if character == quote:
            quote = None
        elif quote == "'":
            value.append(character)
        elif character == "\\":
            index += 1
            if index == len(raw):
                return None
            escaped = raw[index]
            if quote == '"' and escaped not in '\\"$`\n':
                value.append("\\")
            if escaped != "\n":
                value.append(escaped)
        elif quote is None and character in "'\"":
            quote = character
        elif character in "$`" or quote is None and character in "*?[]~":
            return None
        else:
            value.append(character)
        index += 1
    return "".join(value) if quote is None else None


def helper_positions(command, helper, cwd):
    if not isinstance(command, str) or len(command) > 131072:
        return []
    groups, position, redirect_target = [[]], 0, False
    for match in TOKEN.finditer(command):
        if match.start() != position:
            return []
        position = match.end()
        raw = match.group()
        if match.lastgroup == "space":
            continue
        if match.lastgroup == "separator":
            if redirect_target:
                return []
            groups.append([])
            continue
        if match.lastgroup == "redirect":
            if redirect_target:
                return []
            redirect_target = "&" not in raw
            continue
        if raw.startswith("#"):
            return []
        value = literal_word(raw)
        if redirect_target:
            redirect_target = False
            if value is not None:
                continue
        groups[-1].append((value, match.end(), raw))
    if position != len(command) or redirect_target:
        return []
    if any(group and group[0][2].replace("\\\n", "") in SHELL_KEYWORDS for group in groups):
        return []
    found = []
    for group in groups:
        if any(value is None for value, _, _ in group):
            continue
        if len(group) < 3 or Path(group[0][0]).name not in ("python", "python3"):
            continue
        path = Path(group[1][0])
        if not path.is_absolute():
            continue
        if path.resolve() != Path(helper).resolve() or group[2][0] != "prepare":
            continue
        if any(value == "--host-context" or value.startswith("--host-context=") for value, _, _ in group):
            raise ExistingContext("BStack supplies attribution automatically. Remove --host-context and rerun prepare so it captures this call's model.")
        found.append(group[2][1])
    return found


def attach(command, positions, attribution):
    addition = " --host-context " + shlex.quote(encode(attribution))
    for position in reversed(positions):
        command = command[:position] + addition + command[position:]
    return command
