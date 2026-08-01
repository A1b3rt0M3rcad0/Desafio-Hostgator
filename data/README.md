# Ticket source

`data/tickets.json` is the static HelpDesk fixture consumed by the infrastructure worker.
It contains 10,000 deterministic tickets for 500 fictitious customers, anchored at
`2026-08-01T05:30:00Z` and with no timestamp later than that instant. The history
covers the preceding two years so that 7, 30 and 90-day dashboard windows remain
meaningful at the beginning of August 2026.

Regenerate the fixture from the repository root with:

```bash
python data/generate_tickets_mock.py
```

The worker mounts this directory read-only at `/data` and processes one batch of up
to 25 source records every 30 seconds by default.
