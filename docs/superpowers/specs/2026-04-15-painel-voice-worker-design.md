# Painel Voice Worker

## Goal

Replace browser telephony's dependency on Issabel's legacy WebRTC path with a dedicated voice runtime owned by the `painel` stack, while preserving the existing Issabel callcenter bridge for agent state, queues, pauses, and operational fallback.

The user-facing outcome is:

- the `painel` remains the primary control plane
- audio and signaling stop depending on Issabel's fragile browser WebRTC behavior
- the browser can still place and receive calls directly from the panel
- the legacy Issabel integration continues to handle callcenter workflows and compatibility

## Approved Direction

- The main application remains Laravel/PHP in `/home/vasqs/Projetos/painel`.
- A separate dedicated voice service will run on the same server as the panel, but outside the Laravel request lifecycle.
- The preferred implementation is a `Node.js` voice worker.
- The browser will not speak SIP directly to Issabel as the primary path.
- Issabel remains in the architecture for callcenter state, queue control, agent actions, and contingency.

## Chosen Approach

Use a split control-plane/runtime design:

1. Laravel remains the product API, UI, auth, authorization, persistence, and audit layer.
2. A new `voice-worker` service owns realtime voice session lifecycle, SIP signaling, and browser-facing realtime transport.
3. The global voice bar in the panel uses the worker as the primary mode.
4. The Issabel callcenter bridge remains connected for agent/session state, pause/unpause, extension metadata, and fallback actions when needed.

This is preferred over continuing with Issabel-native WebRTC because current validation already proved that browser registration can work, but the runtime is unstable and tightly coupled to the PBX's legacy media path. It is preferred over trying to make PHP itself host realtime media, because PHP is not an appropriate long-running runtime for SIP/media orchestration.

## Scope

### In Scope

- rollback das customizações experimentais de WebRTC no Issabel que prejudiquem o login normal do Agente Console
- A new standalone `voice-worker` service on the panel server
- Laravel integration with the worker
- Browser session bootstrap against the worker instead of direct Issabel-first media
- Command and event contracts between panel, worker, and Issabel bridge
- Global voice bar migration to worker-primary behavior
- Persistence and audit of worker-originated call events in the panel
- Fallback preservation for existing Issabel bridge behavior

### Out of Scope

- Rewriting Issabel callcenter internals
- Turning PHP into the realtime SIP/media runtime
- Full PBX migration away from Issabel
- Replacing queue logic in the legacy callcenter
- Multi-node voice scaling in the first delivery

## Architecture

### Control Plane

Laravel in `painel` remains the source of product truth for:

- user identity
- company and role scope
- UI state and permissions
- command intent
- audit history
- operational mirror

Laravel does not directly own long-lived SIP or media sessions. It issues intent, receives events, stores state, and renders UI.

### Voice Runtime

The new `voice-worker` is a long-running service on the same server. It owns:

- SIP registration
- call origination and termination
- inbound call session lifecycle
- browser realtime session transport
- per-agent voice session state
- delivery of normalized call events back into Laravel

For v1, the worker should be single-instance and stateless enough to restart safely, with durable call history written into Laravel.

### Legacy PBX Integration

Issabel remains the legacy telephony environment and continues to provide:

- agent login/logout
- pause/unpause
- queue state and queue administration
- extension metadata
- compatibility with legacy operator workflows

The existing `callcenter_bridge` remains the operational integration point from the panel into Issabel.

### Required Rollback Before Worker Adoption

Before the worker becomes the primary voice runtime, the temporary WebRTC-oriented changes applied directly to the Issabel SIP path during homologation must be reverted if they interfere with the legacy operator flow.

This rollback is mandatory because:

- the Agente Console needs to return to normal login behavior
- the legacy path must remain operational while the worker is being introduced
- the worker rollout should not depend on keeping Issabel in a half-migrated WebRTC state

The rollback must restore the last known-good behavior for legacy agent login, extension registration, and ordinary softphone-driven operation.

## Data Flow

### Outbound Call

1. User clicks `Ligar` in the panel.
2. Laravel validates authorization and resolves the user's active voice session context.
3. Laravel sends a command to the `voice-worker`.
4. The worker originates the SIP call through its configured PBX/trunk path.
5. The worker streams normalized session events back to:
   - the browser for live UI updates
   - Laravel for persistence and audit
6. Laravel updates `VoiceStateStore` and call event history.
7. If the call also needs callcenter correlation, Laravel links the worker session to the user's `pbx_agent_id` and current Issabel mirror state.

### Inbound Call

1. The worker receives the inbound SIP invite.
2. The worker emits a normalized `incoming` event to Laravel and the browser.
3. The user answers in the panel.
4. The worker completes the call setup and keeps pushing lifecycle events.
5. Laravel persists the timeline and updates the mirrored call state.

### Agent Operations

Agent operations such as pause, unpause, logout, and extension management continue to flow through Laravel into the Issabel bridge. The worker should subscribe to resulting agent-state changes so the voice session and operational session do not drift silently.

## Components

### Laravel Components

- `VoiceBroker`
  - remains the main panel-side facade
  - chooses primary worker path or legacy fallback
- `VoiceWorkerClient`
  - new service for command dispatch to the worker
- `VoiceWorkerEventController`
  - new authenticated webhook/API ingest for worker events
- `VoiceStateStore`
  - continues to expose the current user-facing voice state
- `VoiceCallEvent`
  - continues to persist lifecycle history with a `source` that now includes `worker`

### Voice Worker Components

- session manager
  - maps panel user/agent session to runtime voice session
- SIP adapter
  - manages registration and call signaling
- browser realtime gateway
  - maintains persistent browser connection
- event normalizer
  - emits a stable contract to Laravel and the browser
- health/recovery logic
  - reconnects SIP registration and restores recoverable session metadata

### Issabel Bridge Components

- existing `callcenter_bridge` endpoints remain unchanged in purpose
- panel continues consuming queue, agent, and administrative state from the bridge
- worker does not replace the bridge's operational domain

## Contracts

### Laravel -> Worker Commands

Minimum commands:

- `session.connect`
- `call.start`
- `call.hangup`
- `call.answer`
- `session.disconnect`
- `audio.input.set`
- `audio.output.set`

Canonical envelope:

```json
{
  "command_id": "uuid",
  "company_id": 45,
  "user_id": 133,
  "agent_id": "Agent/1",
  "extension": "1001",
  "command": "call.start",
  "params": {
    "number": "71986322652"
  }
}
```

### Worker -> Laravel Events

Minimum events:

- `session.ready`
- `session.degraded`
- `call.ringing`
- `call.progress`
- `call.answered`
- `call.hangup`
- `call.failed`
- `incoming`

Canonical envelope:

```json
{
  "event_id": "uuid",
  "occurred_at": "2026-04-15T15:00:00-03:00",
  "source": "worker",
  "company_id": 45,
  "user_id": 133,
  "agent_id": "Agent/1",
  "extension": "1001",
  "call_id": "uuid-or-runtime-id",
  "event_type": "call.ringing",
  "state": "ringing",
  "direction": "outbound",
  "remote_number": "71986322652",
  "payload": {}
}
```

### Worker -> Browser Events

The browser should receive the same normalized state vocabulary used by Laravel, to avoid maintaining parallel state models.

## Runtime Boundaries

### Why Node.js

Node.js is preferred because:

- it is appropriate for persistent websocket connections
- it is more suitable than PHP for long-lived realtime processes
- it is easier to isolate from Laravel request workers
- it provides better ergonomics for session-oriented transport and streaming control

### Why Not PHP SIP Runtime

PHP may remain part of orchestration, but it should not be the realtime session runtime. Even if a SIP library exists, the hard part is not only SIP signaling. The system also needs durable connection management, browser-facing realtime transport, and stable media/session coordination. That is better handled by the dedicated worker.

## Failure Handling

### Worker Failure

- Laravel must detect worker unavailability quickly and mark voice state as degraded.
- The global voice bar should expose a clear degraded state rather than silently failing.
- Existing legacy fallback can remain available for eligible users if configured.

### Issabel Drift

- Agent state remains mirrored from Issabel bridge events and reconciliation.
- If the worker is available but Issabel callcenter state is stale, Laravel should surface the mismatch explicitly.
- Calls should not silently assume the queue/agent session is healthy if bridge reconciliation disagrees.

### Browser Media Failure

- The worker-primary design removes Issabel-native browser WebRTC instability from the main path, but the browser still needs an explicit media/session contract.
- If browser-side audio/session setup fails, Laravel should record a `worker` failure event and keep the session recoverable without forcing a full page refresh.

## Security

- Laravel and worker communicate with dedicated shared credentials or signed requests.
- Worker event ingest into Laravel must be authenticated and idempotent.
- Browser connection to the worker must be tied to a Laravel-authenticated session token.
- Worker commands must remain scoped to the authenticated user and company.
- Issabel bridge auth remains separate and unchanged from the current bridge token model.

## Verification

The new architecture will be considered validated when:

1. The panel can establish a worker-backed voice session without using Issabel's browser WebRTC path as the primary mode.
2. Outbound call attempts from the panel generate worker-sourced events in Laravel.
3. Inbound call signaling reaches the panel through the worker path.
4. Agent pause/unpause and queue controls still function through the Issabel bridge.
5. The global voice bar can switch between normal, ringing, in-call, hangup, and degraded states using worker events.
6. Existing fallback behavior remains available when the worker path is unavailable or intentionally disabled.

## Risks And Mitigations

### Two Telephony Domains

Risk: worker call state and Issabel callcenter state may diverge.

Mitigation: keep strict domain boundaries. Worker owns media/call runtime. Issabel owns callcenter operations. Laravel is the reconciliation and presentation layer.

### Legacy Login Regression

Risk: experimental SIP/WebRTC changes in Issabel can continue breaking Agente Console login while the new worker is still under construction.

Mitigation: make rollback of the homologation WebRTC tweaks the first implementation step, verify normal agent login in the legacy flow, and only then continue with worker rollout.

### Runtime Complexity

Risk: a new worker adds operational overhead.

Mitigation: keep v1 single-instance, same-server, with explicit health checks, restart policy, and narrow responsibilities.

### Browser Media Contract

Risk: if the browser contract is underspecified, the system will simply move instability from Issabel into a new custom layer.

Mitigation: keep a single normalized event vocabulary, a dedicated session model, and explicit degraded/failure states from the start.

## Implementation Intent

After spec approval, implementation planning should focus on:

1. revert Issabel WebRTC-specific homologation changes that interfere with normal Agente Console login
2. verify legacy agent login and extension registration behavior after rollback
3. worker service skeleton and lifecycle
4. Laravel client and event ingest integration
5. global voice bar migration to worker-primary behavior
6. preservation of Issabel bridge compatibility
7. homologation tests with a real phone number and clear source attribution in events
