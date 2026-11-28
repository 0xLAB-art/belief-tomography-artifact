# SERVING FINGERPRINTS — behavioral pins for the served endpoints at measurement time

**Written:** 2026-11-28 (post-hoc; pins the frozen records, not the
providers).
**Problem this closes:** catalog names do not pin the served snapshot — a
gateway can silently rotate weights behind an unchanged name, so "the model
we measured" is unverifiable from the name alone. The names cannot be
fixed. The **records can**: each panel's full transcript set is a
fingerprint of what the served endpoint actually produced under the frozen
probes at measurement time. A future reader who re-measures the same
catalog name can fingerprint their own run and compare — not byte-for-byte
(sampling temperature makes exact replay impossible), but at the level this
paper's claims live: adjudicated flag rates, censoring rates, reply-length
distributions, and the refusal-quote shape.

## Fingerprints (SHA-256 of the frozen transcript file; turn count)

| Panel | SHA-256 | turns |
|---|---|---|
| E29 gpt-5.6-sol (gateway, 1024) | `130f0c83f1e541905c3b262e88c9a6eb595553d0fa371d8085886d461b891e5c` | 400 |
| E30 DeepSeek-V4-Flash (200) | `f1524bb8279b956dbfeccc6b5d38c8ab28d747891a83a31f0ba1a4c61fab8469` | 400 |
| E30 DeepSeek-V4-Pro (200) | `9bccfcf27adc0818ae1676c538b1e44526575492872096a3f1868755d3033715` | 400 |
| E30 MiniMax-M3.1-Flash (200) | `1542f2bb5ecf0c28495ca74bb48601ee4d6f9dc9e6d15f535e540c8b1033f235` | 400 |
| E31 DeepSeek-V4-Flash (1024) | `0f6b41939f30289e533b98eefae0daa7419e149227d29591f96d3d3f2ad1929c` | 400 |
| E31 DeepSeek-V4-Pro (1024) | `f46613c4218c8e65c7f91b1560473456eeee0d30a2facb4ee9b6ac1be5cdff1e` | 400 |
| E31 MiniMax-M3.1-Flash (1024) | `c59a2965cc2423ee6270fe1d9d910373c74214ade1a07a14d4e14da05afc9ee5` | 400 |
| E32 gpt-6.2-sol + gpt-6.2-astra (successor grid) | `f868c801953d7ce63e22b859581de2cee85a1a020a320bc551f94e23aee1e93c` | 30 |

These files are individually hash-pinned in the frozen manifest; the table
above exists so the pinning is legible as a *serving* claim, not just a
storage claim.

## Re-check protocol (registered)

A re-measurement of the same catalog name under the same frozen probes is
comparable to the fingerprint at three levels, strongest first:

1. **Censoring rate** — blocked-turn fraction per panel (E30 MiniMax's
   76.2% is a structural signature; a radically different rate indicates a
   different serving configuration).
2. **Adjudicated flag profile** — genuine canary-echo rate per family and
   pooled (E31 V4-Pro's 42/60 echo = 0.700 is the strongest single
   behavioral signature in the deposit).
3. **Refusal-quote shape** — the B01–B05 boundary-refusal mode's presence
   in refusals that name the forbidden action.

A re-run whose profile matches within the panel's CIs is evidence the same
(or behaviorally equivalent) snapshot is still served; divergence localizes
the drift. What no fingerprint can do: recover a retired endpoint, or make
a provider's silent rotation detectable after the fact — this protocol
makes the drift **detectable at the next measurement**, not retroactively.

E2-v1's gateway turns predate full retention; its uncensored-turn records
exist in the E2-v1 artifacts and inherit the manifest pins without a
serving-fingerprint table row.
