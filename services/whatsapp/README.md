# PartPilot private WhatsApp bridge

Local Baileys WhatsApp Web adapter for the PartPilot worker. This is a single-process MVP, not Meta's hosted WhatsApp Cloud API. The API must proxy this bridge; never expose its token or endpoints to a browser or the public reverse proxy.

## Configuration and startup

Use Node 24 LTS or newer. `npm ci --ignore-scripts`, then `npm test` and `npm start`.

Supply these variables through the private deployment environment, outside Git:

| Variable | Meaning |
| --- | --- |
| `PARTPILOT_WA_INTERNAL_TOKEN` | Required, at least 32 random characters; worker and API use the same token. |
| `PARTPILOT_WA_ENABLED` | Exactly `true` enables connection and messaging; default disabled. |
| `PARTPILOT_WA_RECIPIENTS` | Comma-separated E.164 digits without `+`; no real recipients belong in source. Empty means nobody is allowed. |
| `PARTPILOT_WA_STATE_DIR` | Private persistent directory; default `./state`, Docker `/state`. |

Listener is fixed at `127.0.0.1:18081`. On a Linux VPS, use host networking for both this container and its callers, or a shared network namespace. A normal Docker bridge container cannot access another container's loopback. Run only one instance against a state volume. The fixed port prevents a second process in the same network namespace from loading/mutating state.

New accounts remain disconnected until authenticated `POST /connect`. Scan the returned QR through the authenticated PartPilot interface. QR is generated locally, held only in memory, excluded from logs, and cleared on connection/disconnection. Registered sessions reconnect after restart. `/connect` is idempotent while a socket is connecting, awaiting QR, or connected. Logged-out/invalid sessions reset their credentials and require a new QR.

## Internal API

Every route requires `Authorization: Bearer <PARTPILOT_WA_INTERNAL_TOKEN>`. POST requests require JSON content type. Responses have `Cache-Control: no-store`. No CORS access is enabled.

| Request | Body | Response |
| --- | --- | --- |
| `GET /status` | — | `{connection, qr_data_url, enabled}` |
| `POST /connect` | `{}` | Same as status; poll for QR. |
| `POST /check` | `{phone}` | `{registered: boolean, jid: string or null}`; must be connected and phone allowed. |
| `POST /send` | `{event_id, phone, text}` | `{status: "sent" or "uncertain" or "pending", message_id?: string}` |
| `GET /inbox` | — | `{messages:[{message_id,phone,text,received_at,quoted_transport_id}]}`; oldest 100 unacknowledged messages. |
| `POST /inbox/ack` | `{message_ids:[...]}` | `{acknowledged:true}`; maximum 100 IDs. |

Connection states: `disabled`, `disconnected`, `connecting`, `qr`, `connected`, `logged_out`, `error`.

`event_id` accepts 1–128 letters, digits, underscores or hyphens, excluding JavaScript prototype names. Text is nonempty, at most 8,000 UTF-16 code units. The same event ID with different phone/text returns 409. Recipient checks apply to outgoing messages and number registration checks. Invalid input is 400, unallowlisted phone 403, missing/bad token 401, disabled/not-connected check 503. Errors never include raw dependency exceptions or request content.

## Delivery and recovery semantics

Before transport is called, a payload hash and event reservation are atomically written and fsynced. A duplicate event returns the saved result. A concurrent duplicate returns `pending`; callers should poll by repeating the same event ID and exact payload. Disconnected sends return `pending` without reservation, so that exact event can be attempted when connected.

`sent` means Baileys returned a message ID; it is not proof of recipient delivery or reading. Timeouts, failures after reservation, and reservations left by a crash become `uncertain`. They never auto-resend. A late result after timeout does not change this decision. The worker must retain `uncertain` for operator reconciliation; creating a new event ID would bypass deduplication and must not be automatic. Outgoing Baileys resend caching and automatic session recreation are disabled.

Inbound text is accepted only from configured direct-message phone numbers. Own messages, groups, broadcasts, newsletters, history (`append`), nontext, and oversized text are ignored. LIDs use the supported `remoteJidAlt` or `signalRepository.lidMapping.getPNForLID`; an unresolved LID is ignored, never treated as a phone. Protocol authentication keys may still contain metadata needed by WhatsApp; the application does not retain unrelated message text.

Inbound IDs are stable SHA-256 identifiers of sender plus WhatsApp message ID. They remain deduplicated after acknowledgement. The worker should commit its database transaction before acknowledging. The bridge can return a message again until acknowledged, so database insertion must also deduplicate `message_id`.

`quoted_transport_id` preserves the quoted WhatsApp `contextInfo.stanzaId` for supported text replies, including ephemeral text wrappers, or is null for unquoted messages. The database must correlate this against the outbound transport message ID and reject unknown IDs or IDs belonging to old/closed runs. The bridge does not infer that a quote belongs to an active run. Invalid or oversized quote IDs cause the inbound message to be ignored, rather than silently treating it as unquoted. Unquoted text after a reset is inherently ambiguous; an active-run/time-window policy reduces but cannot eliminate that ambiguity.

## Storage and limitations

`auth.json` holds credentials and all Signal key categories, including LID mappings. `ledger.json` holds payload hashes, delivery status, unacknowledged inbox text, and inbound deduplication IDs. Atomic snapshots use file fsync, rename, and directory fsync on Linux. Directory permissions are 0700 and files 0600; use the Docker Linux volume for enforced POSIX permissions. Native Windows additionally needs an owner-only directory ACL because chmod does not provide POSIX access isolation there. Temporary files also use 0600. Corrupt state fails startup rather than silently replacing credentials or ledger.

This private disk store rewrites snapshots and retains deduplication IDs indefinitely. It is suitable for the small demo workload, not high-volume service. Preserve the volume during rebuilds: deleting a ledger removes duplicate protection. Backups contain credentials and message text and must remain private. Run a single replica; cross-host distributed locking is not implemented.

Baileys is a release candidate and follows WhatsApp Web protocol changes. Real QR linking, actual recipient checks, and live send/receive require the operator's account and are not verified by the offline test suite. WhatsApp linking and delivery can fail independently of the local HTTP bridge. No real messages are sent by tests.

Versions were verified from npm: `baileys@7.0.0-rc14`, `qrcode@1.5.4`, `pino@10.4.0`; transitive versions are pinned in `package-lock.json`. Runtime dependencies reported zero known vulnerabilities at the implementation audit.

Official references: [Baileys session management](https://baileys.wiki/authentication/session-management), [socket configuration](https://baileys.wiki/concepts/socket-config), [v7 LID migration](https://baileys.wiki/migration/v7), [Baileys source](https://github.com/WhiskeySockets/Baileys), [Node release support](https://nodejs.org/en/about/previous-releases).
