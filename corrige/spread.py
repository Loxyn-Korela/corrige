"""R10: a repairer whose answer moves between identical runs has not been measured by one run.

    python3 -m corrige.spread <truth.json> <journal.json> <candidate...> [--out measures/x.json]

Judges several candidates of the same run design and reports, per candidate name, the spread of
every repair count across runs, next to what a coin would give on that arm. An arm whose figure is
identical on every run is one where information existed and the repairer used it. An arm whose
figure moves is one where the choice was a tie-break, and a single run reported as a score reads as
skill. The instrument is meant to tell those two apart, which is why this is not optional.

Discovered on 2026-09-10: pgrepair breaks a tie with min() over a Python set of
(element_id, EntityType) pairs, and Python randomises hash(str) per process. See
runs/icij/tie_break.py.
"""
import sys, json, math, collections, statistics
from . import canon, judge as J


def _coin(n):
    """What a fair coin gives on n independent two-edge ties: mean and 95 % band."""
    sd = math.sqrt(n * 0.25)
    return {"expected": n / 2, "sd": round(sd, 2),
            "band_95": [round(n / 2 - 1.96 * sd), round(n / 2 + 1.96 * sd)]}


def reading(kept):
    """What a list of per-run figures licenses us to say. One run licenses nothing."""
    if len(kept) < 2:
        return None, "not repeated: one run establishes nothing about whether the choice was made or drawn"
    if len(set(kept)) == 1:
        return True, "identical on every run: the choice used information"
    return False, "moves between identical runs: the choice was a tie-break, and no single run is a score"


def spread(truth, journal, candidates):
    by_name = collections.defaultdict(list)
    for cand in candidates:
        by_name[cand["candidate"]["name"]].append(J.judge(truth, cand, journal)["repair"])
    out = {}
    for name, reps in sorted(by_name.items()):
        arms = {}
        for arm in sorted({k for r in reps for k in r if k.startswith("cycles/")}):
            of = sum(1 for e in journal["injected"] if e.get("cycle_with") and ("cycles/" + e.get("arm", "informed")) == arm)
            kept = [r.get(arm, {}).get("true edge kept", 0) for r in reps]
            stable, why = reading(kept)
            arms[arm] = {"of": of, "true_edges_kept_per_run": kept,
                         "min": min(kept), "max": max(kept),
                         "median": statistics.median(kept),
                         "stable": stable, "coin": _coin(of), "reading": why}
        out[name] = {"runs": len(reps), "arms": arms,
                     "wrongly_broken_per_run": [r["wrongly_broken"] for r in reps],
                     "visible_caught_per_run": [r.get("visible", {}).get("caught", 0) for r in reps]}
    return out


def main():
    argv, args, skip = sys.argv[1:], [], False
    for a in argv:
        if skip:
            skip = False
        elif a == "--out":
            skip = True          # its value is a destination, not a candidate
        elif not a.startswith("--"):
            args.append(a)
    truth = json.load(open(args[0], encoding="utf-8"))
    journal = json.load(open(args[1], encoding="utf-8"))
    cands = [json.load(open(p, encoding="utf-8")) for p in args[2:]]
    res = spread(truth, journal, cands)
    if "--out" in sys.argv:
        canon.write(sys.argv[sys.argv.index("--out") + 1], {"truth": truth["id"], "journal_sha256": journal["sha256"], "spread": res})
    for name, d in res.items():
        print(f"{name} — {d['runs']} runs")
        for arm, a in d["arms"].items():
            flag = "NOT REPEATED" if a["stable"] is None else "stable" if a["stable"] else "MOVES"
            print(f"   {arm:16} {a['true_edges_kept_per_run']} of {a['of']}  [{flag}]  coin {a['coin']['expected']:.0f}, band {a['coin']['band_95']}")


if __name__ == "__main__":
    main()
