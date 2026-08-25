# Decision memory (condensed KB port)

The original desktop app uses a SQLite FTS5 graph + E5 vector hybrid recall
(RRF k=60). The plugin condenses this to a JSONL journal + grep recall.
# ponytail: file journal is enough; promote to SQLite FTS5 when recall precision hurts

## Journal: ~/.toss-investor/decisions.jsonl

One analysis = one JSON line (schema at the end of pipeline.md). Create the
directory on first use.

## Recall (right before the portfolio-manager stage)

```bash
grep '"symbol": "005930"' ~/.toss-investor/decisions.jsonl | tail -3
```

Inject the last 3 entries into the PM prompt as
"- [date] rating conf% — key_thesis".

## Recall rules

- Link `supersedes` only to the previous decision for the SAME symbol.
 Linking against the whole recall set causes cross-symbol mislinks (a measured
 failure mode).
- Track direction changes: encode ratings as ±1/0, compare with the previous
 decision — agrees_with (same direction) / maintains (same rating) /
 reverses (opposite switch) / initiates (first ever).
- Feed repeated patterns into the PM prompt as self-reflection: "3 consecutive
 reverses — momentum-chasing pattern suspected; be deliberate about entry."

## Outcome review (optional)

For decisions older than 7 days: compute price_at_decision vs current price
return and append "previous decision +12.4% — direction correct" /
"−5.2% — incorrect" to the PM recall context.
