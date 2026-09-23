# DataPulse Embed SDK

## Digital Human Controls

The player advertises `digitalHuman.v1` in its protocol-v1 `ready` message.
`screen.ready` becomes true after the runtime is mounted. Digital-human events
buffered during mounting are delivered after this handshake. Older players keep
working with the existing parameter, refresh and fullscreen APIs; speech commands
reject with `EMBED_CAPABILITY_UNAVAILABLE` when the capability is absent.

```ts
import { DataPulseEmbed } from "@datapulse/embed-sdk";

const screen = DataPulseEmbed.mount(container, {
  url: "https://datapulse.example/embed/screen-id",
  ticket: shortLivedTicket,
  allowAudio: true,
  requestTimeoutMs: 10_000,
});

const unsubscribe = screen.onDigitalHuman((event) => {
  updateStatus(event.component_id, event.name ?? "statusChange", event.status);
});

// Invoke controls after screen.ready, for example from a host toolbar.
const state = await screen.digitalHuman({
  component_id: "speaker",
  action: "getStatus",
});
```

`allowAudio` adds iframe autoplay permission, not a browser user gesture. Embeds
start muted. The viewer may still need to use the iframe's sound control even if
the host unmutes the component. Chromium, Firefox and WebKit apply different
autoplay policies; a resolved command is not proof that sound has started.

### Commands

| Action | Arguments | Behavior |
| --- | --- | --- |
| `getStatus` | `component_id` | Return current status, error code, mute flag and volume. |
| `play` | `component_id` | Resume paused speech, otherwise trigger the published speech configuration. |
| `speak` | `component_id` | Trigger the published configuration using current permitted data. |
| `pause` | `component_id` | Pause active speech. |
| `stop` | `component_id` | Stop active speech and cancel this component's queued tasks. |
| `mute` | `component_id`, `enabled: boolean` | Change mute state; muting currently stops speech. |
| `setVolume` | `component_id`, `volume: number` | Set a finite volume in the inclusive range 0 to 1. |

Commands cannot include arbitrary text, templates, asset URLs, provider options
or scripts. They do not bypass the component's published triggers, cooldown,
quiet hours or usage limits. The current per-player usage counters are not yet
server-enforced project quotas.

The returned Promise acknowledges the command and reports its resulting state;
it does not wait for speech completion. For example, `play` can resolve with
`queued`, `muted`, `fallback` or `waiting_gesture`.

### Lifecycle Events

The wire envelope is `digitalHumanEvent`; its `event.name` identifies the event:

- `digitalHumanReady`: the component's controls are mounted. Data and media can still be loading.
- `statusChange`: a state or error-code change, without repeated identical updates.
- `speechStart`: emitted once when the playback driver starts a task, not again on resume.
- `speechEnd`: normal completion or cancellation; `outcome` is `completed`, `stopped` or `cancelled`.
- `speechError`: a playback failure, terminal for that task. It does not also emit `speechEnd`.
- `fallback`: entry into text/fallback presentation.
- `userGestureRequired`: playback is waiting for user action or timed out before starting.

Each event includes `component_id`, `task_id`, `source`, `status`, `code`,
`timestamp` (Unix milliseconds) and `request_id`. The latter identifies the
source data query where available; it is not the SDK command's request ID.
It can be empty for static content. Events contain no speech text or query rows.
State changes precede their associated lifecycle event. A failed start can
produce `speechError` without an earlier `speechStart`.

### Timeout, Cancellation And Destruction

```ts
const cancellation = new AbortController();
const pending = screen.digitalHuman(
  { component_id: "speaker", action: "getStatus" },
  { signal: cancellation.signal },
);
// Attach the rejection handler before cancelling the request.
pending.catch(handleError);
cancellation.abort();
```

Aborting rejects this local request with `EMBED_REQUEST_CANCELLED` and releases
its timer/listener. It does not undo a command already delivered to the player.
Use `stop` to stop actual playback. Requests also reject on timeout or destroy;
late replies are ignored. Status replies must match the request's component ID.

Call `unsubscribe()` to remove a listener and `screen.destroy()` when removing
the host view. Destruction rejects outstanding requests, removes listeners and
removes the iframe, which releases its runtime and audio resources.

### Errors And Authorization

| Code | Meaning |
| --- | --- |
| `EMBED_PLAYER_NOT_READY` | Wait for the runtime handshake. |
| `EMBED_CAPABILITY_UNAVAILABLE` | The player does not support speech controls. |
| `DIGITAL_HUMAN_COMMAND_INVALID` | Invalid arguments or unpublished content in a command. |
| `DIGITAL_HUMAN_NOT_CONFIGURED` | No accessible digital human has this component ID. |
| `EMBED_REQUEST_TIMEOUT` | No valid correlated reply arrived in time. |
| `EMBED_REQUEST_CANCELLED` | The caller aborted its local wait. |
| `EMBED_DESTROYED` | This SDK instance was destroyed. |
| `EMBED_TICKET_EXPIRED` | The ticket expired; obtain a new ticket and mount a new instance. |

Every message is checked against its source window, exact Origin and instance
ID. Invalid commands from an authenticated host receive a correlated error;
messages from other windows or Origins are ignored. The player rechecks ticket
expiry on its timer, focus/visibility restoration, host commands and protected
resource/data requests. Expiration stops playback and removes the runtime.
The SDK rejects all pending requests and remains unauthorized despite late
`ready` messages. Server authorization remains authoritative for protected APIs.

## Implementation Status

This document describes the implemented SDK surface, not completion of the
whole digital-human phase. See `docs/PHASE_THREE_PROGRESS.md` for remaining media,
provider, rules, quota and acceptance work.
