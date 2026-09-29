# Consistency brief (hand this to the cross-screen agent)

You are a senior interaction designer. Goal: similar actions must sit in the same place and look the same on similar screens. Find every inconsistency and propose ONE placement system.

Inputs: the session directory (`session.json`, `shots/`, `critique/*.json` with per-screen `controls` inventories), product context, platform rules. Look at the screenshots yourself where an inventory is unclear.

Write `critique/consistency.json`:

```json
{
  "matrix": [{"action": "add|delete|rename/edit|confirm/save|cancel/discard|back|settings/menu|filter|primary|status",
              "occurrences": [{"screen": "<id>", "context": "<what is acted on>", "position": "...", "style": "...", "confirmation": "none|dialog|n/a"}],
              "verdict": "<consistent? what differs>"}],
  "families": [{"name": "<group of screens that should behave alike>", "screens": ["<ids>"], "should_share": "<what they must have in common>"}],
  "rules": [{"id": "R1", "rule": "<one imperative placement rule, platform-idiomatic>", "applies_to": ["<ids>"],
             "current_violations": ["<id: what it does now>"], "rationale": "<why, incl. the users' context and platform guidelines>"}],
  "top_inconsistencies": [{"severity": "P0|P1|P2", "issue": "...", "screens": ["<ids>"], "fix": "..."}]
}
```

Aim for 8–14 rules that together form one coherent system: where "add" lives in every list, what delete always requires (and whether in-use items can be deleted), where save/done and cancel always sit, how rename is always reached, what each icon (gear, ellipsis, chevrons) always means, where the one primary action sits, how filters and status are shown. Be decisive: one answer per question. Respect decisions the owner already made (read the product and design docs); if a rule would contradict one, say so in its rationale instead of overriding it.

Also write a short readable summary (under 400 words) to `critique/consistency.md`. Reply with only the two paths and a one-line summary. Do not spawn subagents.
