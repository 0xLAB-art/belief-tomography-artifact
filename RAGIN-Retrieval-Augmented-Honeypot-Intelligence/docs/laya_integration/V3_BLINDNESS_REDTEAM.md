# V3 Blindness Red-Team Report

## Scope

This adversarial audit inspected only rater-visible V3 `id`, `evidence`, and `context` fields plus serialized packet forms. It did not inspect predictions, labels, prior annotation outcomes, ground truth, or confirmatory evaluation output.

## VERIFIED LEAKAGE

Critical explicit source and role framing in rater-visible metadata: 0. The five real-Linux context claims, decorative `sysadmin@srv-01` prompt family, attacker-command wording, historical-session wording, and controlled-session wording were removed or globally normalized.

## PLAUSIBLE BIAS

Material source-role bias: 0. No rater-visible context identifies authorization, attack role, source family, or expected class.

## MINOR SIDE CHANNEL

Detailed multiline shell output remains because it is observed behavioral evidence and cannot be rewritten without changing the instrument's construct. It can signal transcript richness, but it is not a deterministic source-family decoder from metadata and is documented as a residual limitation.

## SAFE / NON-INFORMATIVE

- Case IDs are uniform opaque 12-hexadecimal strings.
- Packet fields and field order are uniform.
- Context uses only neutral observed-sequence wording.
- Packet order is independently shuffled for each rater.

## Source-family inference attempt

The blind inference attempt used only opaque IDs, serialized field structure, context values, prompt prefixes, and visible metadata. It did not use private provenance. Source-family recovery failed from those metadata fields. Private provenance was used only afterward for the separate dependence audit, not to choose edits. The v3 acceptance gate is `CRITICAL_LEAKAGE = 0` and `MATERIAL_SOURCE_ROLE_BIAS = 0`.
