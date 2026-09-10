# Changelog

## 1.3.0 — 2026-09-10
- **R10, a tenth judge rule: one run of a repairer establishes nothing.** `corrige.spread` judges several runs of one design and prints each arm's figure beside what a coin gives, labelled stable, MOVES or NOT REPEATED. T13 covers the three readings, including that one run licenses neither of the other two.
- **Both experiments repeated, and the contrast is the result.** EUR-Lex, four runs per algorithm: the informed arm returns 150 of 150 on all eight, the blind arm returns 58, 59, 65, 69 (ILP) and 64, 66, 66, 70 (Greedy) where a coin gives 65 in a band of 54 to 76. ICIJ, six runs: 24 to 31 of 60 where a coin gives 30. Where information exists both algorithms use it, every time; where it does not, repeating the arm moves the figure by more than the choice of algorithm does.
- **Withdrawn**: the 1.1.0 reading "between the ILP and the greedy there is no measurable difference on this workload". Single runs measure neither.
- The mechanism is named and reproducible in four lines (`runs/icij/tie_break.py`), and so is the one-key fix.
- `corrige.neo4j_graph` empties the database in bounded transactions; one `DETACH DELETE` over the ICIJ graph exceeds the transaction memory limit.

## 1.2.1 — 2026-09-10
- **The greedy's choice is not stable.** Two identical runs of `-a Greedy` on the same graph with the same sealed journal kept 25 and 30 of the 60 blind rival edges. The 1.2.0 note quoted the first run alone; both are now published, and further repeats are running. It sharpens rather than changes the reading: on a blind two-edge violation the choice carries no information.

## 1.2.0 — 2026-09-10
- **A second graph, so that this is a bench and not a case study.** ICIJ Offshore Leaks, loaded from the dump ICIJ publishes, with three laws taken verbatim from pgrepair's own `icij-qualitative-study.toml` (gamma_1, gamma_2, gamma_3) and the typed relations its setup queries create. Truth by construction, `truths/truth-icij-offshoreleaks-2026-09-10.json`, sha256 `b14fa984ba4286ee…`.
- **A cross-check nobody arranged**: our census of gamma_1 on the untouched dump finds 18,000 violations; pgrepair, on the same dump with her own constraint, collects 18,000. Two implementations of one sentence, agreeing to the edge.
- Result, and it is the EUR-Lex result again on a graph that shares nothing with it: identical to a rule without a model on one-edge laws (521 of 521 visible, 0 of 521 invisible); ILP and Greedy return solutions of identical cost (weight 37,206, 18,603 deletions) differing on one pair; on the blind two-edge arm both are at chance (40 % and 41.7 %, ±12.5 points on 60 pairs). The gain over a plain rule is minimality, not discrimination.
- **Bug fixed, and it had silenced a witness**: an injected graph did not carry its truth's law module, so the rule-without-model witness applied the EUR-Lex laws to the ICIJ graph and caught nothing. T12 now holds the module to its graph.
- `measures/icij-second-graph-2026-09-10.json`, `runs/icij/arm.sh` (one clean arm: reload the dump, her setup, our journal, repair, read back).

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
