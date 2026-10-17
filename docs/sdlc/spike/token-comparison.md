# Spike · token comparison for /sdlc 5-implement (2026-10-17, n = 1 per arm)

Task replayed: **T8 `proveedores.py`** on throwaway clones at 23c56a9 (`D:\Claude\sdlc-token-spike\{A,B,C}`,
same docs, ADRs and data; the real repo is untouched). Protocol and `measure.py` (reads the session transcripts) are there.
$ = list-price proxy (Opus 5.5 $4/$20, Sonnet 5.5 $2/$10, cache read $0.20 on both, cache write 1.25× input).

| Arm | Setup | Calls | Cache read | Output | ≈ $ | Wall | Retries | Suite | Quality vs R1/R2 |
|-----|-------|------:|-----------:|-------:|----:|-----:|--------:|-------|------------------|
| A | Opus 5.5, real T8 session (1012b358) | 27 | 2.48 M | 20 k | 1.19 | 6.8 min | 0 | green, +18 checks | full: NIT DV checked, dirección/municipio required, alias not stolen, 4 WebFetch of DIAN rules |
| B | Sonnet 5.5 + Haiku scout (4771a1f2)* | 15 | 1.17 M | 10 k | 0.65 | 2.0 min | 0 nudges, 1 blocked call | green, +14 checks | done-check met; **misses** NIT DV, makes dirección/municipio optional (R1 requires them), `asociar` silently moves an alias |
| C | B + explore-only and read-only-guard hooks | — | — | — | — | — | — | — | not run, see below |

\* B's first 5 calls ran on Opus before the switch to Sonnet ($0.27 of the $0.65). An all-Sonnet run is estimated at ≈$0.55.
Later, T9–T12 also ran in clone B on Sonnet: $0.53 / 0.44 / 0.34 / 0.45, 1–2 min each, suite green (not reviewed; not ported).
The blocked call was a stray `Write D:\Claude\sdlc-score-placeholder` (content "x"), which the auto-mode classifier denied.

## Findings
- About 70k of every call is fixed harness context (tools 36k, MCP 20k, system 11k). Cache reads are 97% of the tokens
  and cost the same on both models, so the **call count** sets the bill. On identical work, Sonnet is only ≈30% cheaper.
- B cost ≈45–55% of A mainly because it did **less**: fewer calls, no DIAN lookups, and 3 validations skipped.
  The ~2.2× gap isn't a like-for-like price saving. Adding the missing R1 work would likely bring B to ~60–70% of A.
- The scout was never called in A or B: T8's reads were targeted, so the skill's ">5 files" rule didn't fire.
- **C not run:** both hooks act only inside subagents, and B started none. On this task C would equal B plus noise.
  The scout's tool list already blocks writes. Hooks remain installed only in clone C (command fixed `python3` → `python`).

## Decision rule (set before running) → result
- Change the skill if B ≤80% of A's cost, the suite is green, the done-check is met and NIT DV is correct. Result: cost ✓,
  suite ✓, done-check ✓, **DV ✗**. Hooks were to be adopted only if C beat B by more than 5%; they can't, so they're out.

## Recommendation
Keep Sonnet for 5-implement (it's what the table already says; switch **before** `/sdlc next`, since a mid-run switch
re-caches ~80k). Add one line to `stages/5-implement.md`: *"If `regulated: yes`, the test covers every field and
validation the R-line names (e.g. R1 dirección/municipio, NIT DV), not only the done-check."* Don't install the community hooks.
For B's gaps, add a FIX task only if T8 is ever re-done on Sonnet. The real repo has A's version.
