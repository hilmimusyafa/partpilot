# Public demo access

Set `PARTPILOT_DEMO_PUBLIC_ACCESS=true` in the API's private runtime.env and
recreate the API container after building the updated image. The API serves
the technician UI, manager UI, and application endpoints without HTTP Basic
authentication. A password is not required in this mode. All visitors share
the same synthetic demo database, workflows, reset action, and configured
WhatsApp integration, including its operator page. This is intentionally a
public interactive demo, not a production authorization model.

Request-origin checks, required mutation headers, database generation fences,
recipient opt-in checks, and validating database functions remain enforced.
Public visitors can trigger messages to the configured consenting recipients;
the internal WhatsApp bridge token and database credentials remain server-side.

To restore private access, remove the public-access flag (or set it to false),
ensure PARTPILOT_DEMO_PASSWORD is configured, and recreate the API container.
The default remains private. Only the exact value `true` enables public access.
