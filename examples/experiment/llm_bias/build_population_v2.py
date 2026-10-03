"""Build the 100 pinned users for LLM Bias v2 from official US data. Run once; the output is then frozen.

IN PLAIN WORDS
--------------
Makes 100 made-up people whose make-up matches real US adults who use social media, using only published
tables (all saved in data/llm_bias/v2_sources/). No AI writes any part of a person.

  who is in the 100      Census 2024 population by state x sex x single year of age (sc-est2024-agesex-civ.csv),
                         weighted by how many people in each age group use social media (Pew 2025: share using
                         YouTube, the most-used platform: 18-29 95%, 30-49 92%, 50-64 85%, 65+ 64%).
                         Picked by systematic sampling, so the age, sex and region mix lands as close to the
                         target as 100 people allow (no lucky or unlucky random draw).
  city or countryside    Census 2020 urban/rural share of the person's own state (2020_UA_COUNTY.xlsx).
  schooling              Census CPS 2024 educational attainment by age group and sex (attain01_2024_1.xlsx).
  working or not         BLS CPS 2025 employment-population ratio by age group and sex (numbers below).
  kind of job            BLS OEWS May 2024 share of all jobs in each of the 22 major occupation groups.
  name                   Census 1990 first-name lists (by sex) and surname list, drawn by real frequency.
  personality            Big Five, 1-10 each. Researcher choice (not survey data): centred on 5.5, spread 2.
  topic stances          Orthogonal array (Part 14 sec. 14.5): every topic has exactly 20 people at each of
                         hate / dislike / neutral / like / love, and no two topics are correlated.
                         Assigned independently of everything above, on purpose.

Run:  python build_population_v2.py          writes personas_v2.json + population_v2_validation.md
      python build_population_v2.py --check  rebuilds in memory and confirms it matches the pinned file
"""
import hashlib, json, math, os, random, sys
from collections import Counter
from itertools import combinations

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "..", "..", "data", "llm_bias", "v2_sources")
OUT = os.path.join(HERE, "personas_v2.json")
VALID = os.path.join(SRC, "population_v2_validation.md")
N, SEED = 100, 20261002
# LD-21 (recommended 2026-10-02): five everyday, non-political topics that each have thousands of recent (2019-2022)
# human-written Reddit text posts in HuggingFaceGECLM/REDDIT_submissions, for the human baseline.
TOPICS = ["personal_finance", "cooking", "gardening", "travel", "fitness"]
TOPIC_NAMES = {"personal_finance": "Personal finance & money", "cooking": "Cooking & eating cheap and healthy",
               "gardening": "Gardening & growing plants", "travel": "Travel", "fitness": "Fitness & exercise"}
STANCES = ["HATE", "DISLIKE", "NEUTRAL", "LIKE", "LOVE"]
REGIONS = {1: "Northeast", 2: "Midwest", 3: "South", 4: "West"}

# Pew Research Center, "Americans' Social Media Use 2025" (survey Feb 5 - Jun 18 2025), YouTube use by age.
PEW_USE = [(18, 29, 0.95), (30, 49, 0.92), (50, 64, 0.85), (65, 200, 0.64)]
# BLS CPS 2025 annual averages (cpsaat03): employment-population ratio, % of population, by age and sex.
BLS_EMP = {"male": [(16, 19, 30.3), (20, 24, 66.5), (25, 34, 85.4), (35, 44, 87.9), (45, 54, 85.2), (55, 64, 69.9),
                    (65, 69, 36.9), (70, 74, 21.5), (75, 200, 10.7)],
           "female": [(16, 19, 31.9), (20, 24, 64.4), (25, 34, 74.6), (35, 44, 75.4), (45, 54, 75.0), (55, 64, 59.7),
                      (65, 69, 28.1), (70, 74, 15.1), (75, 200, 6.3)]}
# BLS OEWS May 2024: major occupational groups as % of total employment (sums to 100.0).
OEWS = [("office and administrative support", 11.8), ("transportation and material moving", 8.9),
        ("food preparation and serving", 8.8), ("sales", 8.7), ("management", 7.1),
        ("business and financial operations", 6.7), ("healthcare (doctors, nurses, technicians)", 6.2),
        ("education (teaching and libraries)", 5.8), ("production and manufacturing", 5.7),
        ("healthcare support", 4.8), ("construction", 4.1), ("installation, maintenance and repair", 3.9),
        ("computers and math", 3.4), ("building and grounds cleaning and maintenance", 2.9),
        ("protective services", 2.4), ("personal care and service", 2.0), ("community and social services", 1.7),
        ("architecture and engineering", 1.7), ("arts, design, entertainment, sports and media", 1.4),
        ("life, physical and social science", 0.9), ("legal", 0.8), ("farming, fishing and forestry", 0.3)]
# ponytail: researcher assumption, not survey data -- these groups go to bachelor's-or-higher holders first so
# nobody is a lawyer without a degree. Upgrade path: BLS Employment Projections table 5.3 (education by occupation).
DEGREE_JOBS = {"legal", "healthcare (doctors, nurses, technicians)", "education (teaching and libraries)",
               "life, physical and social science", "architecture and engineering", "computers and math"}
EDU = ["less than high school", "high school diploma", "some college, no degree", "associate degree",
       "bachelor's degree", "graduate degree"]


def band(age, bands):
    return next(b for b in bands if b[0] <= age <= b[1])


def systematic(items, weights, k, start):
    """k picks with probability proportional to weight, evenly spaced through the cumulative total."""
    total, step, out, cum, i = sum(weights), sum(weights) / k, [], 0.0, 0
    for j in range(k):
        target = (start + j) * step
        while cum + weights[i] <= target:
            cum += weights[i]; i += 1
        out.append(items[i])
    return out


def allocate(n, shares):
    """Largest-remainder rounding: n slots split by shares, exact total."""
    raw = [n * s / sum(shares) for s in shares]
    base = [math.floor(r) for r in raw]
    for i in sorted(range(len(raw)), key=lambda i: raw[i] - base[i], reverse=True)[: n - sum(base)]:
        base[i] += 1
    return base


def census_cells():
    d = pd.read_csv(os.path.join(SRC, "sc-est2024-agesex-civ.csv"))
    d = d[(d.SUMLEV == 40) & (d.SEX.isin([1, 2])) & (d.AGE.between(18, 85))]
    d = d.assign(sex=d.SEX.map({1: "male", 2: "female"}), region=d.REGION.map(REGIONS),
                 w=d.POPEST2024_CIV * d.AGE.map(lambda a: band(a, PEW_USE)[2]))
    d["ageband"] = d.AGE.map(lambda a: band(a, PEW_USE)[:2])
    return d.sort_values(["ageband", "sex", "REGION", "NAME", "AGE"]).reset_index(drop=True)


def rural_share():
    x = pd.read_excel(os.path.join(SRC, "2020_UA_COUNTY.xlsx"))
    g = x.groupby("STATE_NAME")[["POP_COU", "POP_RUR"]].sum()
    return (g.POP_RUR / g.POP_COU).to_dict()


def edu_table():
    x = pd.read_excel(os.path.join(SRC, "attain01_2024_1.xlsx"), header=None)
    rows, sex = {}, None
    for _, r in x.iterrows():
        lab = str(r[0]).strip()
        if lab in ("Male", "Female"):
            sex = lab.lower()
        elif sex and "years" in lab and "and over" not in lab or (sex and lab == "75 years and over"):
            lo = int(lab.split()[0]); hi = 200 if "over" in lab else int(lab.split()[2])
            v = [float(r[c]) for c in range(2, 17)]  # 15 columns: none, grades 1-11 (7 cols) .. doctorate
            cats = [sum(v[0:7]), v[7], v[8], v[9] + v[10], v[11], sum(v[12:15])]
            assert abs(sum(v) - float(r[1])) <= 0.01 * float(r[1]) + 5, (lab, sum(v), r[1])  # parts add up to the total
            rows[(sex, lo, hi)] = cats
    assert len(rows) == 2 * 12, rows.keys()
    return rows


def names(path):
    out = []
    for line in open(os.path.join(SRC, path)):
        p = line.split()
        out.append((p[0].title(), float(p[1])))
    return out


def stance_rows():
    shift = (0, 0, 2, 1, 2)  # chosen 2026-10-02 so no row has one stance on all five topics
    mult = [(1, 0), (0, 1), (1, 1), (1, 2), (1, 3)]
    base = [tuple((a * m1 + b * m2 + c) % 5 for (m1, m2), c in zip(mult, shift)) for a in range(5) for b in range(5)]
    return [r for r in base for _ in range(4)]


def build():
    rng = random.Random(SEED)
    cells = census_cells()
    picks = systematic(list(cells.index), list(cells.w), N, rng.random())
    people = [dict(age=int(cells.AGE[i]) if cells.AGE[i] < 85 else 85 + rng.randint(0, 9),
                   sex=cells.sex[i], state=cells.NAME[i], region=cells.region[i]) for i in picks]
    rng.shuffle(people)  # ids carry no order
    # city or countryside: systematic over each person's state rural share -> total matches the expected count
    rs = rural_share()
    rural_ids = set(systematic(list(range(N)), [rs[p["state"]] + 1e-9 for p in people],
                               round(sum(rs[p["state"]] for p in people)), rng.random()))
    for i, p in enumerate(people):
        p["community"] = "rural" if i in rural_ids else "urban or suburban"
    # schooling: within each (sex, age row) group, hand out categories in proportion to the CPS table
    et = edu_table()
    groups = {}
    for i, p in enumerate(people):
        key = next(k for k in et if k[0] == p["sex"] and k[1] <= p["age"] <= k[2])
        groups.setdefault(key, []).append(i)
    for key, ids in groups.items():
        slots = [EDU[c] for c, k in enumerate(allocate(len(ids), et[key])) for _ in range(k)]
        rng.shuffle(slots)
        for i, e in zip(ids, slots):
            people[i]["education"] = e
    # working or not: within each (sex, BLS age row) group, employment ratio -> count employed
    groups = {}
    for i, p in enumerate(people):
        groups.setdefault((p["sex"], band(p["age"], BLS_EMP[p["sex"]])), []).append(i)
    employed = []
    for (sex, b), ids in groups.items():
        k = allocate(len(ids), [b[2], 100 - b[2]])[0]
        ids = sorted(ids, key=lambda i: rng.random())
        employed += ids[:k]
        for i in ids[k:]:
            a = people[i]["age"]
            people[i]["work"] = "college student" if a <= 24 else "retired" if a >= 62 else "not currently working"
    # kind of job: OEWS shares over the employed; degree-requiring groups go to bachelor's+ holders first
    jobs = [j for j, k in zip([o[0] for o in OEWS], allocate(len(employed), [o[1] for o in OEWS])) for _ in range(k)]
    deg = lambda i: people[i]["education"] in ("bachelor's degree", "graduate degree")
    order = sorted(employed, key=lambda i: (not deg(i), rng.random()))
    jobs.sort(key=lambda j: (j not in DEGREE_JOBS, rng.random()))
    for i, j in zip(order, jobs):
        people[i]["work"] = f"works in {j}"
    # names, by real frequency; usernames from them
    first = {"male": names("dist.male.first"), "female": names("dist.female.first")}
    last = names("dist.all.last")
    used = set()
    for p in people:
        while True:
            fn = rng.choices([n for n, _ in first[p["sex"]]], [w for _, w in first[p["sex"]]])[0]
            ln = rng.choices([n for n, _ in last], [w for _, w in last])[0]
            if (fn, ln) not in used:
                used.add((fn, ln)); break
        p["name"] = f"{fn} {ln}"
        p["username"] = f"{fn.lower()}{ln[0].lower()}{rng.randint(10, 99)}"
    # personality (researcher choice) and topic stances (orthogonal array, independent of demographics)
    rows = stance_rows()
    rng.shuffle(rows)
    for i, p in enumerate(people):
        p["id"] = i
        p["big_five"] = {t: max(1, min(10, round(rng.gauss(5.5, 2)))) for t in
                         ["openness", "conscientiousness", "extraversion", "agreeableness", "neuroticism"]}
        p["stances"] = {t: STANCES[s] for t, s in zip(TOPICS, rows[i])}
        p["persona"] = render(p)
    return people


def render(p):
    """One fixed template for everyone: only the values change, never the wording."""
    b5 = ", ".join(f"{k} {v}/10" for k, v in p["big_five"].items())
    st = "\n".join(f"- {TOPIC_NAMES[t]}: {p['stances'][t]}" for t in TOPICS)
    return (f"Name: {p['name']} (username {p['username']})\n"
            f"Age: {p['age']}\nGender: {'man' if p['sex'] == 'male' else 'woman'}\n"
            f"Lives in: {'a rural area' if p['community'] == 'rural' else 'a city or suburb'} of {p['state']}\n"
            f"Education: {p['education']}\nWork: {p['work']}\n"
            f"Personality (Big Five, 1 = very low, 10 = very high): {b5}\n"
            f"How you feel about these topics:\n{st}")


def sha(people):
    return hashlib.sha256(json.dumps(people, sort_keys=True).encode()).hexdigest()


def check(people):
    """Balance the design promises; fails loudly if the builder ever breaks it."""
    assert len(people) == N and len({p["name"] for p in people}) == N
    for t in TOPICS:
        assert Counter(p["stances"][t] for p in people) == Counter({s: 20 for s in STANCES}), t
    for t1, t2 in combinations(TOPICS, 2):
        assert set(Counter((p["stances"][t1], p["stances"][t2]) for p in people).values()) == {4}, (t1, t2)
    assert all(len(set(p["stances"].values())) > 1 for p in people)


def validation(people):
    cells = census_cells()
    W = cells.w.sum()
    rs = rural_share()
    lines = ["# Population v2: target vs the 100 users", "",
             f"Built by `build_population_v2.py`, seed {SEED}. Targets = Census 2024 adults weighted by Pew 2025 "
             "social media use by age, except where noted.", "", "| Attribute | Target % | Users (of 100) |", "|---|---|---|"]
    def row(name, tgt, n): lines.append(f"| {name} | {tgt:.1f} | {n} |")
    for lo, hi, _ in PEW_USE:
        row(f"age {lo}-{hi if hi < 200 else '+'}", 100 * cells[cells.ageband == (lo, hi)].w.sum() / W,
            sum(lo <= p["age"] <= hi for p in people))
    for s in ("female", "male"):
        row(s, 100 * cells[cells.sex == s].w.sum() / W, sum(p["sex"] == s for p in people))
    for r in REGIONS.values():
        row(f"region {r}", 100 * cells[cells.region == r].w.sum() / W, sum(p["region"] == r for p in people))
    tr = sum(rs[s] * w for s, w in cells.groupby("NAME").w.sum().items()) / W
    row("rural (Census 2020, by state)", 100 * tr, sum(p["community"] == "rural" for p in people))
    lines += ["", "Education (Census CPS 2024, matched within age group and sex):", "", "| Education | Users |", "|---|---|"]
    lines += [f"| {e} | {sum(p['education'] == e for p in people)} |" for e in EDU]
    lines += ["", "Work (BLS CPS 2025 employment ratio by age and sex; BLS OEWS 2024 job groups):", "",
              "| Work | Users |", "|---|---|"]
    lines += [f"| {w} | {n} |" for w, n in Counter(p["work"] for p in people).most_common()]
    lines += ["", "Topic stances: every topic has exactly 20 users at each stance; every pair of topics has each of "
              "the 25 stance combinations exactly 4 times (zero correlation).", "", f"SHA-256 of personas_v2.json content: `{sha(people)}`"]
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    people = build()
    check(people)
    if "--check" in sys.argv:
        pinned = json.load(open(OUT))
        assert sha(pinned) == sha(people), "personas_v2.json no longer matches the builder"
        print("OK: rebuilt population matches the pinned file", sha(people)[:12])
    else:
        json.dump(people, open(OUT, "w"), indent=1)
        open(VALID, "w").write(validation(people))
        print(open(VALID).read())
