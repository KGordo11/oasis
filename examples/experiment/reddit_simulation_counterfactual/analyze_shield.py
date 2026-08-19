"""Compare the shielded down-condition run against the existing unshielded
down-condition baseline from Simulation 2.

Reuses the same keyword disagreement/correction classifier from
COUNTERFACTUAL_EXPERIMENT_REPORT.md Step E6 for continuity with the prior
report, and adds two metrics the shield paper itself flags as unmeasured
(page 9, Limitations): final vote-score trajectory, and engagement
(action-type mix / do_nothing rate) -- i.e. whether the shield protects
users without also killing engagement.
"""
import sqlite3

KEYWORDS = ["disagree", "incorrect", "actually", "not true", "mistake",
            "error", "wrong", "false", "surprised", "debated"]

DBS = {
    "up (unshielded, Sim 2 baseline)": "data/counterfactual_36_up.db",
    "up (shielded, run 1)": "data/counterfactual_36_up_shielded.db",
    "up (shielded, run 2)": "data/counterfactual_36_up_shielded_run2.db",
    "control (unshielded, Sim 2 baseline)": "data/counterfactual_36_control.db",
    "control (shielded, run 1)": "data/counterfactual_36_control_shielded.db",
    "control (shielded, run 2)": "data/counterfactual_36_control_shielded_run2.db",
    "down (unshielded, Sim 2 baseline)": "data/counterfactual_36_down.db",
    "down (shielded, run 1)": "data/counterfactual_36_down_shielded.db",
    "down (shielded, run 2)": "data/counterfactual_36_down_shielded_run2.db",
    "down (shielded, run 3)": "data/counterfactual_36_down_shielded_run3.db",
    "down (shielded, run 4)": "data/counterfactual_36_down_shielded_run4.db",
}


def disagreement_rate(conn):
    rows = conn.execute("""
        SELECT content FROM comment
        WHERE post_id IN (SELECT post_id FROM post WHERE user_id = 0)
    """).fetchall()
    total = len(rows)
    disputing = [r[0] for r in rows
                 if r[0] and any(k in r[0].lower() for k in KEYWORDS)]
    return len(disputing), total


def vote_score(conn):
    row = conn.execute("""
        SELECT COUNT(*), ROUND(AVG(num_likes), 2), ROUND(AVG(num_dislikes), 2),
               ROUND(AVG(num_likes - num_dislikes), 2)
        FROM post WHERE user_id = 0
    """).fetchone()
    return row


def engagement(conn):
    rows = conn.execute("""
        SELECT action, COUNT(*) FROM trace
        WHERE action != 'sign_up'
        GROUP BY action ORDER BY COUNT(*) DESC
    """).fetchall()
    total = sum(c for _, c in rows)
    return rows, total


def main():
    print("=" * 72)
    for label, path in DBS.items():
        print(f"\n--- {label} ({path}) ---")
        try:
            conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
            conn.execute("SELECT 1 FROM post LIMIT 1")
        except sqlite3.OperationalError as e:
            print(f"  Could not open: {e}")
            continue

        disputing, total = disagreement_rate(conn)
        pct = (100 * disputing / total) if total else 0.0
        print(f"  Disagreement/correction language: {disputing}/{total} "
              f"comments ({pct:.0f}%)")

        n, avg_likes, avg_dislikes, avg_score = vote_score(conn)
        print(f"  Vote score on treated posts: n={n}, avg_likes={avg_likes}, "
              f"avg_dislikes={avg_dislikes}, avg_score={avg_score}")

        rows, action_total = engagement(conn)
        print(f"  Engagement: {action_total} non-signup actions total")
        for action, count in rows:
            print(f"    {action:16s} {count:4d} "
                  f"({100*count/action_total:.0f}%)")

        conn.close()
    print("\n" + "=" * 72)


if __name__ == "__main__":
    main()
