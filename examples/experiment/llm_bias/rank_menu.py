"""Part 2's menu from part 1's data (Gordon 10-23): least-used actions at the top, most-used at the bottom.

    python3 examples/experiment/llm_bias/rank_menu.py data/llm_bias/v3/r101 data/llm_bias/v3_flipped/r101/menu.txt

Counts every action the 3 AIs picked on post screens (where the menu is shown) in all 9 reading cells of part 1,
noise-floor re-reads left out. Same lines word for word as the V1 menu (+ MESSAGES in a live world); sections are
ordered by their total, lines inside a section by their own total, ties keep the V1 order. Prints the counts.
Stdlib only (runs on the Spark).
"""
import glob, json, os, re, sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import live_world  # noqa: E402
import run_v2 as R  # noqa: E402


def names(line):
    """The action names a menu line offers: '- follow / unfollow / mute / unmute  (needs ...)' -> 4 names."""
    head = re.split(r":|  \(", line[2:], maxsplit=1)[0]
    return [n.strip() for n in head.split("/")]


def sections(menu):
    out = []
    for line in menu.split("\n"):
        if line.startswith("- "):
            out[-1][1].append(line)
        else:
            out.append((line, []))
    return out


def rank(counts, live):
    secs = sections(R.MENU + ("\n" + live_world.MESSAGES_SECTION if live else ""))
    tot = lambda line: sum(counts[n] for n in names(line))  # noqa: E731
    secs = [(h, sorted(lines, key=tot)) for h, lines in secs]  # sorted() is stable: ties keep the V1 order
    secs.sort(key=lambda s: sum(tot(l) for l in s[1]))
    return "\n".join(h + "\n" + "\n".join(lines) for h, lines in secs)


def main(rd, out):
    files = [f for f in glob.glob(os.path.join(rd, "reading_*.jsonl")) if "_d" not in os.path.basename(f).split("__")[1]]
    assert len(files) == 9, f"part 1 needs all 9 reading cells, found {len(files)} in {rd}"
    counts, live, screens = Counter(), False, 0
    for f in files:
        for l in open(f):
            x = json.loads(l)
            live |= "screen" in x
            if x.get("screen", "post") == "post":
                screens += 1
                counts.update(a["action"] for a in x["actions"])
    menu = rank(counts, live)
    for n in R.ACTION_NAMES + (["open_messages"] if live else []):
        assert n in menu, n
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    open(out, "w").write(menu + "\n")
    print(f"{screens} post screens, {sum(counts.values())} actions picked; least used first:")
    order = [n for line in menu.split("\n") if line.startswith("- ") for n in names(line)]
    for n in order:
        print(f"  {counts[n]:7d}  {n}")
    print(f"\nmenu written to {out}:\n{menu}")


if __name__ == "__main__":
    main(*sys.argv[1:3])
