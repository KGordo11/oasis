"""Pick the real, human-written Reddit posts that serve as the human baseline in LLM Bias v2. Run once.

IN PLAIN WORDS
--------------
Source: HuggingFaceGECLM/REDDIT_submissions (Pushshift dumps, 2006 - Jan 2023), one split per subreddit.
A post is kept only if it is:
  * from 1 Jan 2019 to 31 Oct 2022 -- recent, but before ChatGPT (30 Nov 2022), so a human certainly wrote it
  * a text post (no link, no image), not removed or deleted, not marked adult
  * 40 to 400 words, with no web links in the text
  * upvoted at least 5 times on Reddit (filters spam and empty posts, not quality)
  * free of "EDIT:" / "UPDATE:" notes, which only real Reddit posts carry and would give the author away
Then a fixed 400 per subreddit are drawn with a fixed seed. Text is HTML-unescaped and otherwise left exactly as
the person wrote it.

    python human_pool_v2.py <folder with the downloaded <Subreddit>_<n>.parquet files>
writes data/llm_bias/v2_sources/human_pool.jsonl
"""
import glob, html, json, os, random, re, sys

import duckdb

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "..", "..", "data", "llm_bias", "v2_sources", "human_pool.jsonl")
SUBS = {"personal_finance": "personalfinance", "cooking": "EatCheapAndHealthy", "gardening": "gardening",
        "travel": "travel", "fitness": "Fitness"}
PER_SUB, SEED = 400, 20261002
START, END = 1546300800, 1667260800  # 2019-01-01 00:00 UTC .. 2022-11-01 00:00 UTC
TELLS = re.compile(r"\b(edit|update|eta)\s*\d*\s*[:\-]", re.I)


def main(folder):
    c = duckdb.connect()
    out = []
    for topic, sub in SUBS.items():
        files = sorted(glob.glob(os.path.join(folder, f"{sub}_*.parquet")))
        assert files, f"no files for {sub}"
        rows = c.execute(f"""
            select id, title, selftext, try_cast(created_utc as double) ts, try_cast(score as int) score
            from read_parquet({files}, union_by_name=true)
            where try_cast(created_utc as double) >= {START} and try_cast(created_utc as double) < {END}
              and is_self = 'True' and selftext not in ('', '[removed]', '[deleted]')
              and coalesce(over_18, 'False') = 'False' and coalesce(removed_by_category, '') = ''
              and try_cast(score as int) >= 5 and selftext not like '%http%' and selftext not like '%www.%'
            order by id""").fetchall()
        keep = []
        for pid, title, body, ts, score in rows:
            body, title = html.unescape(body).replace("&#x200B;", "").strip(), html.unescape(title).strip()
            if 40 <= len(body.split()) <= 400 and not TELLS.search(body) and not TELLS.search(title):
                keep.append({"id": pid, "topic": topic, "subreddit": f"r/{sub}", "title": title, "body": body,
                             "created_utc": int(ts), "reddit_score": score, "words": len(body.split())})
        rng = random.Random(f"{SEED}|{topic}")
        pick = rng.sample(keep, PER_SUB)
        print(f"{sub}: {len(rows)} candidates, {len(keep)} pass every filter, {len(pick)} drawn")
        out += pick
    with open(OUT, "w") as f:
        for r in out:
            f.write(json.dumps(r) + "\n")
    print("wrote", OUT)


if __name__ == "__main__":
    main(sys.argv[1])
