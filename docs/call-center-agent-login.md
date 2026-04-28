# Call Center Agent Login Fixes

## Scope

These fixes keep the Issabel Call Center default flow working for agents created
in `Call Center / Agent Options / Agents`, while also allowing SIP-based agents
to log in without breaking legacy `Agent/N` behavior.

## Problems Addressed

### 1. AMI bootstrap race

`AMIEventProcess` could receive the agent list before the AMI connection was
ready. When that happened, the dynamic queue membership map was lost until a
later refresh, producing errors such as:

- `Invalid agent number`
- `Agent login process not started`
- missing dynamic queue membership after restart

### 2. Wrong AstDB key for SIP agents

Dynamic queue membership for SIP agents must be stored in AstDB with the key:

- `type_first_letter + agent_number`

Examples:

- `SIP/1001` -> `S1001`
- `IAX2/2001` -> `I2001`

Using `SIP1001` does not work for the dialer parser in
`AMIEventProcess::_cb_Command_DatabaseShow`.

### 3. Legacy `Agent/N` session being dropped by SIP peer events

When both a legacy `Agent/N` and a SIP agent shared the same physical peer,
`msg_PeerStatus` could force-logoff the wrong agent. A SIP unregistration event
for `SIP/1001` could log out `Agent/1`, which broke the default GUI-created
agent flow.

### 4. Legacy `Agent/N` session being dropped during `AgentsComplete` races

During login races, `queue_log` could show `AGENTLOGIN` followed by
`AGENTLOGOFF` within a few seconds for the same legacy identity. The strongest
culprit was `AMIEventProcess::msg_AgentsComplete`: if Asterisk already reported
the agent as logged in but the dialer still carried a transient
`estado_consola = 'logged-out'`, the reconciliation path could force-logoff the
same `Agent/N` session that had just been accepted by Asterisk. The fix is
intentionally narrow: it only preserves the session when the dialer itself has
evidence of a local login still in flight, such as `extension` or
`logging_inicio`.

### 5. Agent Console default selection

The Call Center UI could prefer SIP agents even when a legacy `Agent/N` existed
for the same operator. This is undesirable in deployments that rely on the
default Issabel `Agent/N` workflow.

### 6. Tailscale overlay being treated as SIP localnet

In the containerized Asterisk runtime, treating a `tailscale*` interface as a
`localnet` for `chan_sip` can make SIP dialogs advertise the container bridge
address (for example `172.18.0.2`) instead of a reachable host address. Janus
or other external peers may then answer the call but lose media or DTMF because
subsequent SIP traffic is sent to the unreachable bridge IP.

### 7. Production SIP and Janus behind Docker bridge NAT

The repository now treats Docker `bridge` plus published ports as a lab mode
only. It may be good enough for loopback checks, but it is not the correct
production contract for SIP/UDP or Janus because Docker can still hide the real
host path behind bridge NAT.

For production, homologation, or any serious SIP or Janus validation, run the
stack with `ISSABEL_COMPOSE_MODE=hostnet` or an equivalent no-NAT runtime.
Otherwise the PBX can advertise a Docker bridge address or an unstable mapped
path even when the initial registration appears healthy.

### 8. Janus host-mode using Docker DNS names for SIP registration

When the painel-side Janus runs in `network_mode: host`, names such as
`issabel-dev` are no longer resolved by Docker's internal DNS. In that mode,
using `issabel-dev` as the SIP registrar/proxy can degrade the browser runtime
immediately with `registration_failed` / `503 DNS Error`, which leaves the
panel in `session.degraded` before the agent login even starts.

For the validated local topology where Issabel publishes SIP on the host, the
stable registration target is:

- `VOICE_GATEWAY_SIP_DOMAIN=127.0.0.1`
- `VOICE_GATEWAY_SIP_PROXY=127.0.0.1`
- `VOICE_GATEWAY_SIP_OUTBOUND_DOMAIN=127.0.0.1`

This is not a call-center identity change. `Agent/N` remains the canonical
call-center identity; this only fixes how the painel-side Janus reaches the SIP
registrar.
## Current Behavior

### Operator-entered agent references

The painel field historically called `pbx_agent_id` accepts the same value that
an operator sees in `Call Center / Agent Options / Agents`: the agent
`Number`.

That means:

- plain numeric references such as `34` must resolve by `call_center.agent.number`
- explicit internal references such as `route:34` or `id:34` may resolve by
  the database primary key when a stable route identifier is required
- debugging a mismatch must compare the bridge `/status` result, `queue show`,
  and `queue_log` for the same effective `Agent/N`

Treating a plain numeric value as the database `id` is incorrect for normal
panel operation and can silently map one user to another agent.

### Legacy agent priority

When both formats exist for the same operator:

- `Agent/N` is the default selection in Agent Console
- `Agent/N` must keep working as the priority flow
- `SIP/ramal` remains available as a dynamic alternative
- SIP peer events must not tear down the `Agent/N` session
- `AgentsComplete` must not force-logoff a just-logged-in `Agent/N` while the
  dialer still lags behind Asterisk state and the local login is still in
  flight

### SIP dynamic support

If a SIP agent exists, the runtime hook ensures:

- the correct AstDB key is written under `QPENALTY`
- the queue has `eventmemberstatus=yes`
- the queue has `eventwhencalled=yes`
- the dialer is restarted so it reloads membership state

### Bootstrap login call handling

The validated one-click `Logar` flow now has an explicit contract across bridge,
gateway, and browser:

- the bridge persists a pending login window and reports `status=logging` while
  ECCP and call-center runtime state are still converging
- the painel-side gateway marks the first technical post-register call used for
  campaign activation as `bootstrap_login_call`
- the browser auto-answers only that marked bootstrap call locally, instead of
  relying on a slower `gateway -> Livewire -> browser` roundtrip

This keeps one-click login behavior without requiring the browser to guess that
every `ringing` event during `logging` should be auto-answered.

## Bootstrap

The active fix is now the container bootstrap in
`docker/issabel/rootfs/usr/local/bin/issabel-firstboot`.

It is responsible for:

- reconciling AMI credentials from the PBX configuration
- normalizing `/etc/asterisk/manager.conf` so `admin` keeps the required
  `read`, `write`, `originate`, and `channelvars` settings
- aligning `call_center.valor_config` with the same AMI user/password
- patching `/opt/issabel/dialer/AMIEventProcess.class.php` so `PeerStatus`
  `Unregistered` only force-logoffs dynamic SIP sessions and preserves legacy
  `Agent/N` console sessions
- patching `/opt/issabel/dialer/AMIEventProcess.class.php` so
  `msg_AgentsComplete` preserves legacy `Agent/N` sessions when Asterisk has
  already accepted the login but the dialer still reports a transient
  `logged-out` state for the same locally initiated login
- filtering `tailscale*` interfaces out of SIP `localnet` autodetection so
  external peers never receive Docker bridge addresses in SIP dialogs

The previous runtime hook modules were removed after the bootstrap fix proved
stable enough for both `Agent/*` and `SIP/*` logins.

## Validation

The repository includes HTTP-level regression coverage in:

- `tests/test_agent_console_login.py`

Covered checks:

- static `Agent/1` login no longer fails with `Invalid agent number` or `Specified agent not found`
- dynamic `SIP/1001` login starts without `Invalid agent number`
- Agent Console prefers `Agent/1` when both `Agent/1` and `SIP/1001` exist

## Operational Notes

- After updating hooks, run `./scripts/sync-workspace.sh`
- Re-run `python3 -m unittest tests.test_agent_console_login`
- If the runtime was already in a bad state, the hook restarts `issabeldialer`
  so queue membership and agent mappings are reloaded
- For production SIP or Janus, run the stack with
  `ISSABEL_COMPOSE_MODE=hostnet`; keep `bridge` only for local lab workflows
- For containerized Issabel plus Tailscale peers, do not force
  `ISSABEL_SIP_LOCALNETS=100.64.0.0/10`; prefer leaving it empty so bootstrap
  autodetection ignores `tailscale*`, or explicitly set only the Docker-local
  bridge ranges that should bypass `externip`
- If a panel user enters `34`, validate it against the Issabel agent `Number`
  first. Use `route:34` or `id:34` only when you intentionally need the
  internal database identity.
- When validating the painel `janus-browser` flow, trust `queue_log` plus the
  bridge `status` endpoint before trusting the browser badge alone. The browser
  can remain `in-call` briefly while the PBX has already issued `AGENTLOGOFF`,
  and the opposite can also happen during short-lived login races.
