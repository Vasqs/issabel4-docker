# AGENTS.md

## Purpose

Operational guidance for agents working in this Issabel workspace.

This repository is not a generic PHP app. Most changes here affect a live PBX
runtime contract involving Asterisk, `issabeldialer`, SIP signaling, RTP, and
the painel `janus-browser` stack.

## Repository shape

Treat this workspace as a monorepo.

- The top-level repo coordinates Docker/runtime/bootstrap behavior.
- There are additional versioned repos nested under `modules/` and `overlays/`.
- Before editing anything under those trees, check whether the real source of
  truth is the nested repo rather than the monorepo root.
- When documenting or summarizing changes, be explicit about which repo owns the
  fix.

## Source of truth

When validating call-center behavior, use these sources in order:

1. `/var/log/asterisk/queue_log`
2. bridge status endpoints from `modules/callcenter_bridge`
3. Asterisk CLI state such as `queue show`, `agent show online`, `sip show peer`
4. browser/UI state

Do not treat the browser badge alone as authoritative.

## Identity rules

- `Agent/N` is the canonical call-center identity.
- `SIP/<extension>` is transport/runtime identity, not the primary business
  identity for agent login state.
- Do not “simplify” code by replacing `Agent/N` flows with extension-only
  logic unless the task explicitly requires that migration.

## Janus and SIP topology

- `ISSABEL_COMPOSE_MODE=hostnet` is the expected mode for serious SIP/Janus
  validation.
- Docker bridge mode is lab-only and can hide the real SIP/RTP path behind NAT.
- If painel-side Janus runs in `network_mode: host`, Docker DNS names like
  `issabel-dev` are not reliable registrar targets. Prefer the published host
  SIP address for registration in that topology.
- Tailscale interfaces must not be blindly treated as SIP `localnet`.

## Agent login debugging

When an agent appears stuck in `logging` or gets logged out unexpectedly:

1. check `queue_log` for `AGENTLOGIN`, `CONNECT`, `COMPLETEAGENT`, and `AGENTLOGOFF`
2. inspect bridge `status` for the same agent and extension
3. inspect `AMIEventProcess.class.php` runtime behavior before patching UI code
4. only then inspect panel/browser state transitions

Short `AGENTLOGIN -> AGENTLOGOFF` loops are usually PBX/runtime issues, not just
presentation bugs.

## Safe change areas

Prefer fixes in these places:

- `docker/issabel/rootfs/usr/local/bin/issabel-firstboot`
- versioned docs under `docs/`
- tests under `tests/`
- bridge modules and overlays that are synced into the runtime

Be careful with direct core edits under runtime-extracted Issabel code unless the
change is also made in the versioned source that provisions the container.

## Validation expectations

After voice/login changes, try to validate all of these:

- agent login succeeds
- no immediate `AGENTLOGOFF`
- outbound queue call reaches `CONNECT`
- sidebar/navigation or panel remounts do not tear down the active session
- tests still pass for the touched area

## Documentation

Keep these files aligned with operational reality:

- `docs/call-center-agent-login.md`
- `docs/operations.md`

If a fix changes the validated topology or debugging method, update the docs in
the same task.
