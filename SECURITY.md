# Security Policy

Verino is pre-alpha and has no supported releases yet.

## Reporting a vulnerability

Please **do not** open a public issue. Use GitHub's private vulnerability reporting: repository → **Security** → **Report a vulnerability**.

Include affected files or commands, steps to reproduce, and the impact. You can expect an acknowledgement within 7 days.

## Scope

In scope: the `verino` CLI and MCP server (e.g. path traversal when writing generated files, unsafe YAML loading, command injection when invoking `idf.py` / `pio`).

Hardware-data errors (a wrong pin fact) are not security issues; please report them with the "Chip / board data" issue template.
