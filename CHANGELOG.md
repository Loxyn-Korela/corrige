# Changelog

## 1.1.0 — 2026-09-10
- **The straw witness is gone.** The first cycle experiment let the right edge be chosen without any solver (283 of 288 injected edges also violated the date law). The new design has two arms in one graph: informed (150 cycles the date law can settle) and blind (130 cycles nothing but the two-edge law can see). pgrepair's own Greedy is now a witness beside its ILP.
- Result, and it corrects us twice: against a plain rule the gain is large (150 true edges kept against 0); between the ILP and the greedy there is **no measurable difference** on this workload; and on the blind arm both sit at chance (44.6 % and 50.8 %, ±8.6 points), which is the ceiling and is now stated as such.
- All seven damages injectable; label law L6 from the CELEX letter; pgrepair repairs 3,932 of 3,932 wrong labels, a half of the tool no measurement had touched.

## 1.0.0 — 2026-09-10
First version anyone can run end to end without us.

- **The truth is published**: `doi:10.5281/zenodo.22688808` — 489,223 EUR-Lex relations frozen on
  2026-09-09, its human audit, and the overlay measuring what the acts' texts state. Until now the
  repository held only a 200-fact sample and the real file lived on our disk.
- Layer 1 complete and measured: truth builder, judge (rules R1-R9), injector with sealed seed and
  journal, two witnesses, 22 planted-fault assertions, the pgrepair workload with the four world laws.
- Measured: pgrepair matches a plain rule edge for edge on one-edge laws, and separates from it on
  the two-edge law (274 of 288 cycles resolved in favour of the true edge, against 0 for the rule).
- Measured by hand then at scale: 2.3 % of the register is wrong, and about a quarter of its repeals
  are not stated in the act that performs them.
- The judge accepts the overlay (`--stated`) and reports recall on the facts the documents state,
  counting apart the misses no reader could have found.
