# Nuwa-Inspired Experience Memory

This project integrates the core idea of `nuwa-skill` into the backend experience-summary layer: durable memory should capture how to reason, decide, express and respect evidence boundaries, rather than storing loose fragments.

Reference:

- https://github.com/alchaincyf/nuwa-skill
- https://raw.githubusercontent.com/alchaincyf/nuwa-skill/main/SKILL.md
- https://raw.githubusercontent.com/alchaincyf/nuwa-skill/main/references/extraction-framework.md

## What Changed

`src/backend/rule_memory.py` now converts supported document/query evidence into structured experience rules. Each rule can include:

- `memory_kind`: `mental_model`, `decision_heuristic`, `principle`, `anti_pattern`, `expression_pattern`, or `boundary`
- `decision_trigger`: when the rule should be used
- `heuristic`: a concise actionable rule
- `anti_pattern`: what to avoid
- `boundary`: what the rule cannot claim, and how strong the evidence is
- `transfer_scope`: where the rule can be reused
- `validation`: evidence count, source type, confidence, and validation status

The existing `/api/memory/rules` interface remains backward compatible. Older rules without these fields still render normally.

## Nuwa Mapping

| Nuwa concept | AeroKB memory field |
| --- | --- |
| Mental model / cognitive frame | `memory_kind=mental_model` |
| Decision heuristic | `memory_kind=decision_heuristic`, `heuristic` |
| Expression DNA | `memory_kind=expression_pattern` |
| Anti-pattern / value boundary | `memory_kind=anti_pattern`, `anti_pattern` |
| Honest boundary | `memory_kind=boundary`, `boundary`, `validation` |

## Evidence Discipline

The memory store still rejects `unsupported` and `model_prior` claims for long-term rule memory. A model-only answer can appear in conversation provenance, but it is not silently promoted into document-backed memory.

Rules are treated as:

- `validated`: multiple evidence links and sufficient confidence
- `provisional`: at least one evidence link
- `weak`: insufficient supporting evidence
- `excluded`: unsupported or model-only content

## Frontend Display

`web/app.js` now renders each experience rule with a compact kind badge, trigger, heuristic, boundary and transfer scope. The UI intentionally avoids exposing raw implementation internals while still making the rule quality and evidence boundary visible.

## Maintenance Notes

- Keep the memory schema additive to preserve old portable projects.
- Do not store raw API keys, private prompts, cookies or secrets in rule memory.
- Prefer concise reusable rules over long copied paragraphs.
- When evidence conflicts, keep the boundary explicit instead of forcing a single overconfident rule.
