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
TOKEN = re.compile(r'''[ \t\r]+|\n|&&|;|(?:[^\s;&|<>()'"`\\]+|'[^']*'|"(?:[^"\\]|\\.)*"|\\[^\n])+''')


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


def helper_positions(command, helper, cwd):
    if not isinstance(command, str) or len(command) > 131072:
        return []
    tokens, position = [], 0
    for match in TOKEN.finditer(command):
        if match.start() != position:
            return []
        position = match.end()
        raw = match.group()
        if raw.strip() == "" and raw != "\n":
            continue
        if raw in (";", "&&", "\n"):
            tokens.append((raw, match.end(), True))
            continue
        try:
            values = shlex.split(raw)
        except ValueError:
            return []
        if len(values) != 1 or "$" in raw or "`" in raw:
            return []
        tokens.append((values[0], match.end(), False))
    if position != len(command):
        return []
    groups, group = [], []
    for token in tokens:
        if token[2]:
            groups.append(group)
            group = []
        else:
            group.append(token)
    groups.append(group)
    found = []
    for group in groups:
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
