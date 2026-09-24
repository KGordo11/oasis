"""The hard-coded persona bank for the LLM Bias project.

IN PLAIN WORDS
--------------
This makes the PEOPLE. Each one is a fixed record -- name, age, job, where they
live, a Big Five personality, which of the 15 topics they love / like / ignore /
dislike, what they want from a post, and how freely they vote. Person #7 is the
same person in every run, forever, which is what lets runs be compared.

The bank is written ONCE to `personas_bank.json` and committed. Runs read the
file; they never rebuild it. `python personas.py --check` verifies the committed
file still matches what the builder produces.

WHY NO LLM WRITES THE PERSONAS
------------------------------
The hypothesis is that a model playing a persona prefers posts that model wrote.
If llama3.1 had written the persona descriptions, a llama-written persona prompt
could itself nudge the judge toward llama-style text -- a contamination with no
clean way to remove afterwards. So every persona here is assembled from
attribute pools by a seeded random generator and fixed sentence templates.
No model authored a word of it.

WHAT WAS TAKEN FROM OASIS AND THE REFERENCE SIMS
------------------------------------------------
* OASIS's reddit profile schema (`data/reddit/user_data_36.json`): realname,
  username, bio, persona, age, gender, mbti, country, profession,
  interested_topics. Every record carries all ten, so the bank also loads into
  stock OASIS agent generators.
* The Big Five 1-10 scores with a one-line gloss, as in the reference repos'
  `user_profiles.json` (MultiAgent4Collusion, MutiAgent4Fraud).
* Sim 4's lesson (personas.py there, F-38/F-112): OASIS's generated reddit
  personas are 0.963 cosine-similar to one another -- near-identical characters.
  A persona only matters if it is DIFFERENT, so interests here are explicit,
  signed and spread across 15 topics, and the prompt states them plainly.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import random

from topics import TOPICS

HERE = os.path.dirname(os.path.abspath(__file__))
BANK_PATH = os.path.join(HERE, "personas_bank.json")
BANK_SEED = 20260923
BANK_SIZE = 1000

FIRST_M = ["James", "Robert", "Michael", "David", "Carlos", "Wei", "Ahmed", "Tyler", "Dale", "Marcus",
           "Luis", "Kenji", "Ethan", "Samuel", "Andre", "Patrick", "Raj", "Hank", "Owen", "Victor",
           "Darnell", "Nikolai", "Tomas", "Brian", "Jamal", "Kyle", "Grant", "Mateo", "Felix", "Omar"]
FIRST_F = ["Mary", "Linda", "Sarah", "Emily", "Maria", "Mei", "Fatima", "Brittany", "Donna", "Keisha",
           "Rosa", "Yuki", "Hannah", "Grace", "Aaliyah", "Colleen", "Priya", "Judy", "Megan", "Elena",
           "Tanya", "Ingrid", "Lucia", "Amber", "Nadia", "Kayla", "Ruth", "Sofia", "Chloe", "Leila"]
FIRST_NB = ["Alex", "Jordan", "Sam", "Riley", "Casey", "Quinn", "Avery", "Rowan"]
LAST = ["Miller", "Garcia", "Nguyen", "Okafor", "Schmidt", "Hernandez", "Kowalski", "Chen", "Johnson",
        "Patel", "O'Brien", "Rossi", "Yamamoto", "Brooks", "Haddad", "Larsen", "Dubois", "Mensah",
        "Reyes", "Novak", "Walker", "Kim", "Friedman", "Silva", "Hughes", "Petrov", "Morales", "Bauer",
        "Ali", "Thompson", "Lindqvist", "Adeyemi", "Castillo", "Murphy", "Sato", "Fischer"]

PLACES = [("rural Montana", "United States"), ("suburban Ohio", "United States"),
          ("Houston, Texas", "United States"), ("Brooklyn, New York", "United States"),
          ("a small town in Georgia", "United States"), ("Phoenix, Arizona", "United States"),
          ("Minneapolis", "United States"), ("the Central Valley of California", "United States"),
          ("Seattle", "United States"), ("rural Iowa", "United States"), ("Miami", "United States"),
          ("Toronto", "Canada"), ("rural Saskatchewan", "Canada"), ("Manchester", "United Kingdom"),
          ("a village in Yorkshire", "United Kingdom"), ("Dublin", "Ireland"), ("Sydney", "Australia"),
          ("outback Queensland", "Australia"), ("Auckland", "New Zealand"), ("Berlin", "Germany"),
          ("Chicago", "United States"), ("Denver", "United States"), ("Nashville", "United States"),
          ("Portland, Maine", "United States")]

# profession -> topics it pulls toward (+) or away from (-). Keeps people coherent:
# a rancher leans farming, a line cook leans cooking.
PROFESSIONS = {
    "cattle rancher": {"farming": 2, "cars": 1}, "grain farmer": {"farming": 2, "small_business": 1},
    "auto mechanic": {"cars": 2, "diy": 1}, "long-haul truck driver": {"cars": 2, "travel": 1},
    "line cook": {"cooking": 2}, "restaurant owner": {"cooking": 2, "small_business": 2},
    "software developer": {"tech": 2, "gaming": 1}, "IT support technician": {"tech": 2},
    "financial advisor": {"personal_finance": 2, "small_business": 1}, "bank teller": {"personal_finance": 1},
    "accountant": {"personal_finance": 2}, "real estate agent": {"personal_finance": 1, "small_business": 1},
    "high school teacher": {"parenting": 1, "science_space": 1}, "kindergarten teacher": {"parenting": 2},
    "registered nurse": {"fitness": 1}, "paramedic": {"fitness": 1}, "personal trainer": {"fitness": 2},
    "electrician": {"diy": 2}, "carpenter": {"diy": 2}, "plumber": {"diy": 1, "small_business": 1},
    "graphic designer": {"tech": 1, "movies_tv": 1}, "journalist": {"movies_tv": 1},
    "retail store manager": {"small_business": 1}, "warehouse worker": {"gaming": 1},
    "stay-at-home parent": {"parenting": 2, "cooking": 1}, "college student": {"gaming": 1, "tech": 1},
    "retired machinist": {"diy": 1, "cars": 1}, "retired postal worker": {"travel": 1},
    "veterinary technician": {"pets": 2}, "dog groomer": {"pets": 2, "small_business": 1},
    "lab researcher": {"science_space": 2, "tech": 1}, "pharmacist": {"fitness": 1},
    "sales representative": {"sports": 1, "travel": 1}, "flight attendant": {"travel": 2},
    "barista": {"cooking": 1}, "construction foreman": {"diy": 1, "cars": 1},
    "social worker": {"parenting": 1}, "freelance photographer": {"travel": 1, "tech": 1},
    "insurance adjuster": {"cars": 1, "personal_finance": 1}, "landscaper": {"diy": 1, "farming": 1},
}
EDUCATION = ["high school diploma", "some college", "trade school certificate", "associate degree",
             "bachelor's degree", "master's degree"]
INCOME = ["tight, living paycheck to paycheck", "modest but stable", "comfortable", "well-off"]
MBTI = ["INTJ", "INTP", "ENTJ", "ENTP", "INFJ", "INFP", "ENFJ", "ENFP",
        "ISTJ", "ISFJ", "ESTJ", "ESFJ", "ISTP", "ISFP", "ESTP", "ESFP"]

BIG5 = {  # trait -> (low gloss, mid gloss, high gloss)
    "Openness": ("prefers the familiar and practical", "open to new ideas when they make sense",
                 "curious and drawn to new ideas"),
    "Conscientiousness": ("easygoing and spontaneous", "reasonably organised",
                          "disciplined, organised and detail-focused"),
    "Extraversion": ("quiet and reserved", "sociable in small doses", "outgoing and talkative"),
    "Agreeableness": ("blunt and sceptical of others", "fair but not a pushover",
                      "warm, trusting and supportive"),
    "Neuroticism": ("calm and hard to rattle", "occasionally stressed", "anxious and easily irritated"),
}
LENGTH_TASTE = ["short, get-to-the-point posts", "posts with enough detail to be useful",
                "long, thorough posts"]
TONE_TASTE = ["humour and a casual voice", "a serious, no-nonsense voice", "an honest, personal voice",
              "a calm, practical voice"]
EVIDENCE_TASTE = ["hard numbers and specifics", "real personal stories", "step-by-step practical advice",
                  "a strong, clear opinion"]
PET_PEEVES = ["humblebragging", "posts that sound like an advertisement", "vague posts with no details",
              "people who ask questions they could have searched", "preachy lecturing",
              "clickbait titles", "whining without trying to fix anything", "overly polished corporate-sounding writing",
              "know-it-alls", "fake-sounding stories", "walls of text", "doom and gloom"]
VOTING = {  # style -> description shown to the model
    "generous": "You upvote freely whenever a post is decent, and you almost never downvote.",
    "typical": "You upvote posts you genuinely like and downvote ones that annoy you or waste your time.",
    "harsh": "You rarely upvote; you downvote anything low-effort, boring or off-putting.",
}
AFFINITY_WORDS = {2: "love", 1: "enjoy", 0: "are indifferent to", -1: "are bored by", -2: "dislike"}


def _gloss(score, trait):
    lo, mid, hi = BIG5[trait]
    return lo if score <= 3 else hi if score >= 8 else mid


def _username(rng, first, last, used):
    styles = [lambda: f"{first.lower()}{rng.randint(10, 99)}",
              lambda: f"{first[0].lower()}{last.lower().replace(chr(39), '')}{rng.randint(1, 999)}",
              lambda: f"{rng.choice(['quiet', 'rusty', 'blue', 'old', 'lucky', 'tired', 'north', 'wild'])}"
                      f"{rng.choice(['maple', 'fox', 'river', 'wrench', 'kettle', 'pine', 'hawk', 'stone'])}"
                      f"{rng.randint(1, 99)}"]
    while True:
        u = rng.choice(styles)()
        if u not in used:
            used.add(u)
            return u


def build_bank(n=BANK_SIZE, seed=BANK_SEED):
    rng = random.Random(seed)
    topic_ids = list(TOPICS)
    used, out = set(), []
    for i in range(n):
        g = rng.choices(["male", "female", "non-binary"], weights=[48, 48, 4])[0]
        first = rng.choice(FIRST_M if g == "male" else FIRST_F if g == "female" else FIRST_NB)
        last = rng.choice(LAST)
        age = rng.randint(18, 78)
        prof = rng.choice(list(PROFESSIONS))
        if age >= 66 and not prof.startswith("retired"):
            prof = rng.choice(["retired machinist", "retired postal worker", prof])
        if age <= 22 and rng.random() < 0.5:
            prof = "college student"
        place, country = rng.choice(PLACES)
        # topic affinity: base draw, then the profession pull, then age/place pulls
        aff = {t: rng.choices([-2, -1, 0, 1, 2], weights=[10, 20, 35, 25, 10])[0] for t in topic_ids}
        for t, d in PROFESSIONS[prof].items():
            aff[t] += d
        if "rural" in place or "village" in place or "outback" in place or "Valley" in place:
            aff["farming"] += 1
        if age >= 60:
            aff["gaming"] -= 1
        if 28 <= age <= 50 and rng.random() < 0.5:
            aff["parenting"] += 1
        aff = {t: max(-2, min(2, v)) for t, v in aff.items()}
        # guarantee at least one love and one dislike, so every persona has an edge
        if max(aff.values()) < 2:
            aff[max(aff, key=lambda t: (aff[t], rng.random()))] = 2
        if min(aff.values()) > -2:
            aff[min(aff, key=lambda t: (aff[t], rng.random()))] = -2
        big5 = {t: rng.randint(1, 10) for t in BIG5}
        voting = rng.choices(list(VOTING), weights=[25, 55, 20])[0]
        name = f"{first} {last}"
        loves = [TOPICS[t]["name"] for t in topic_ids if aff[t] == 2]
        p = {
            "id": i,
            "username": _username(rng, first, last, used),
            "realname": name,
            "age": age, "gender": g, "country": country, "place": place,
            "profession": prof, "education": rng.choice(EDUCATION), "income": rng.choice(INCOME),
            "mbti": rng.choice(MBTI), "big_five": big5,
            "topic_affinity": aff,
            "taste": {"length": rng.choice(LENGTH_TASTE), "tone": rng.choice(TONE_TASTE),
                      "evidence": rng.choice(EVIDENCE_TASTE)},
            "pet_peeve": rng.choice(PET_PEEVES),
            "voting": voting,
        }
        p["interested_topics"] = [TOPICS[t]["name"] for t in topic_ids if aff[t] >= 1]
        p["bio"] = f"{prof.capitalize()} from {place}. Into {', '.join(loves[:2])}."
        p["persona"] = render_persona(p)
        out.append(p)
    return out


def render_persona(p):
    """The persona paragraph. Plain template, identical wording for everyone."""
    b5 = "; ".join(f"{t.lower()} {s}/10 ({_gloss(s, t)})" for t, s in p["big_five"].items())
    groups = {}
    for t, v in p["topic_affinity"].items():
        groups.setdefault(v, []).append(TOPICS[t]["name"])
    interest = " ".join(f"You {AFFINITY_WORDS[v]} {', '.join(groups[v])}."
                        for v in (2, 1, -1, -2) if v in groups)
    return (
        f"You are {p['realname']} (username u/{p['username']}), a {p['age']}-year-old {p['gender']} "
        f"{p['profession']} living in {p['place']}. Education: {p['education']}. Money situation: {p['income']}. "
        f"MBTI {p['mbti']}. Big Five personality: {b5}.\n"
        f"Interests: {interest}\n"
        f"In a post you value {p['taste']['length']}, {p['taste']['tone']}, and {p['taste']['evidence']}. "
        f"Your pet peeve is {p['pet_peeve']}.\n"
        f"Voting habit: {VOTING[p['voting']]}"
    )


def bank_hash(bank):
    return hashlib.sha256(json.dumps(bank, sort_keys=True).encode()).hexdigest()[:12]


def load_bank(path=BANK_PATH):
    with open(path) as f:
        return json.load(f)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true", help="(re)write personas_bank.json")
    ap.add_argument("--check", action="store_true", help="verify the committed file matches the builder")
    a = ap.parse_args()
    bank = build_bank()
    if a.write:
        with open(BANK_PATH, "w") as f:
            json.dump(bank, f, indent=1)
        print(f"wrote {len(bank)} personas, hash {bank_hash(bank)}")
    if a.check:
        ok = bank_hash(load_bank()) == bank_hash(bank)
        print("bank matches builder" if ok else "BANK DIFFERS FROM BUILDER")
        raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
