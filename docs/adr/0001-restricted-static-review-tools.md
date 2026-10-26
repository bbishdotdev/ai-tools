# Restricted tools for static PR review

Status: Accepted

Date: 2026-10-26

Decision authority: Brenden Bishop approved this direction in the implementation discussion, then requested end-to-end review and merge. This record preserves that approved change to the earlier mandatory-worker design.

Static PR review uses the configured Codex and Claude CLIs with only BStack's pinned-repository browser available to the models. Reviewers can inspect the full base, head, and current target trees, including unchanged callers. The controller retains GitHub publication. OS isolation around the model CLIs is optional; executing project code still requires a separate, credential-free runtime worker.

A mandatory Bubblewrap/Socat worker imposed Linux-specific dependencies and blocked other supported environments and launcher wrappers. Restricting the available tools keeps unattended source review practical without giving the models a general shell, host-file reader, or network tool. The installed CLIs, launcher wrappers, provider connection, and administrator-managed policy remain trusted software. These controls do not isolate a compromised CLI process from the host and do not guarantee correct model conclusions.

Upgrading from the automatic Linux worker removes that default OS isolation. Keep or configure an explicit vetted worker when process isolation is required. Revisit this choice if a supported CLI cannot reliably enforce the restricted tool set; do not restore general host tools to make a review pass.
