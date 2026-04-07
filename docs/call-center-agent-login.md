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

### 4. Agent Console default selection

The Call Center UI could prefer SIP agents even when a legacy `Agent/N` existed
for the same operator. This is undesirable in deployments that rely on the
default Issabel `Agent/N` workflow.

## Current Behavior

### Legacy agent priority

When both formats exist for the same operator:

- `Agent/N` is the default selection in Agent Console
- `Agent/N` must keep working as the priority flow
- `SIP/ramal` remains available as a dynamic alternative
- SIP peer events must not tear down the `Agent/N` session

### SIP dynamic support

If a SIP agent exists, the runtime hook ensures:

- the correct AstDB key is written under `QPENALTY`
- the queue has `eventmemberstatus=yes`
- the queue has `eventwhencalled=yes`
- the dialer is restarted so it reloads membership state

## Runtime Hooks

### `modules/dialer-agent-bootstrap-fix`

Persists the dialer-side fixes in `AMIEventProcess.class.php`:

- delay agent-list processing until AMI is ready
- keep pending agent lists across AMI reconnects
- preserve `Agent/N` sessions when `PeerStatus(Unregistered)` belongs to a
  shared SIP peer
- only force-logoff the dynamic agent in that conflict case

### `modules/agent-console-sip-login-fix`

Persists the UI/runtime compatibility fixes:

- Agent Console lists all active agents, not only static ones
- the UI prefers `Agent/*` as the selected agent when both `Agent/*` and
  `SIP/*` exist
- writes the correct `QPENALTY` key for SIP agents (`S1001`, not `SIP1001`)
- ensures queue event flags are enabled
- optionally injects legacy `Agent/*` queue members into active campaign queues
  when they are missing

## Validation

The repository includes HTTP-level regression coverage in:

- `tests/test_agent_console_login.py`

Covered checks:

- static `Agent/1` login starts without `Invalid agent number`
- dynamic `SIP/1001` login starts without `Invalid agent number`
- Agent Console prefers `Agent/1` when both `Agent/1` and `SIP/1001` exist

## Operational Notes

- After updating hooks, run `./scripts/sync-workspace.sh`
- Re-run `python3 -m unittest tests.test_agent_console_login`
- If the runtime was already in a bad state, the hook restarts `issabeldialer`
  so queue membership and agent mappings are reloaded
