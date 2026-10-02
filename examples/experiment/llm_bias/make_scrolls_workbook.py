"""One Excel workbook for all of Test 6: every person's whole scroll in every round, post by post, with both AIs' reactions.

    python make_scrolls_workbook.py           # writes data/llm_bias/two_ai/test6_every_scroll.xlsx

Sheets: README (what every column means), Bias data, By subreddit, By interest, By voting habit,
Each person (own vs other AI's posts, split those ways), Scrolls (one row per round per person per post, in the order they saw them),
People (the 100 people, the exact text the AI read, live counts of their reactions over all rounds), Posts (every post
in full, with live vote counts). Counts are Excel formulas (COUNTIFS on the Scrolls sheet), so they stay right if you
filter or edit; Excel, Numbers and Google Sheets calculate them when the file opens.
"""

import ast
import os
import sys

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import authors  # noqa: E402
from topics import TOPICS  # noqa: E402

D = os.path.join(authors.DATA, "two_ai")
OUT = os.path.join(D, "test6_every_scroll.xlsx")
A, B = "gemma4:e2b", "gemma3:1b"
ACT = {"like": "upvote", "dislike": "downvote", "nothing": "nothing"}
CARE = {-2: "dislikes it", -1: "bored by it", 0: "doesn't care", 1: "enjoys it", 2: "loves it"}
HABIT = {"generous": "upvotes almost everything", "typical": "typical", "harsh": "hard to please"}
TOPIC_ORDER = ["personal_finance", "cars", "farming", "cooking", "tech"]
F = Font(name="Arial", size=10)
FB = Font(name="Arial", size=10, bold=True)
HEAD = PatternFill("solid", start_color="DDE3EA")


def short(ai):
    return ai.split(":")[0]


def write_sheet(ws, headers, rows, widths, wrap_cols=()):
    ws.append(headers)
    for c in ws[1]:
        c.font, c.fill = FB, HEAD
        c.alignment = Alignment(wrap_text=True, vertical="top")
    for r in rows:
        ws.append(r)
    for row in ws.iter_rows(min_row=2):
        for c in row:
            c.font = F
            c.alignment = Alignment(vertical="top", wrap_text=c.column in wrap_cols)
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions


def formulas(ws, n_rows, cols):
    for i in range(2, n_rows + 2):
        for col, fm in cols(i).items():
            ws[f"{col}{i}"] = fm
            ws[f"{col}{i}"].font = F


def bias_tab(wb, at, name, title, note, key_headers, cats):
    """One row per category per (AI playing the people, whose posts): counts, %s, and own-minus-other upvote %."""
    S = "Scrolls!"
    k = len(key_headers)
    wd = wb.create_sheet(name, at)
    last = get_column_letter(k + 11)
    wd["A1"], wd["A2"] = title, note
    wd["A1"].font = Font(name="Arial", size=13, bold=True)
    wd["A2"].font = F
    wd["A2"].alignment = Alignment(wrap_text=True, vertical="top")
    wd.merge_cells(f"A2:{last}2")
    wd.row_dimensions[2].height = 70
    wd.append([])
    wd.append(key_headers + ["AI playing the people", "Whose posts", "Own or other's?", "Upvoted", "Downvoted", "Nothing",
                             "Total reactions", "Upvoted %", "Downvoted %", "Nothing %", "Upvoted %: own minus other's"])
    for c in wd[4]:
        c.font, c.fill = FB, HEAD
        c.alignment = Alignment(wrap_text=True, vertical="top")
    col = lambda n: get_column_letter(k + n)  # n = 1.. for the columns after the key columns
    up, dn, no, tot, upp = col(4), col(5), col(6), col(7), col(8)
    react = {A: f"{S}$O:$O", B: f"{S}$Q:$Q"}
    i = 5
    for labels, crit in cats:
        for player, author in [(A, A), (A, B), (B, B), (B, A)]:
            base = f'{crit},{S}$L:$L,"{short(author)}",{react[player]}'
            own = player == author
            wd.append(labels + [short(player), f"{short(author)}'s posts", "own" if own else "other AI's",
                                f'=COUNTIFS({base},"upvote")', f'=COUNTIFS({base},"downvote")',
                                f'=COUNTIFS({base},"nothing")', f"=SUM({up}{i}:{no}{i})", f"={up}{i}/{tot}{i}",
                                f"={dn}{i}/{tot}{i}", f"={no}{i}/{tot}{i}", f"={upp}{i}-{upp}{i + 1}" if own else None])
            for c in wd[i]:
                c.font = FB if labels[0] == "All 15 rounds" else F
                if c.column >= k + 8:
                    c.number_format = "0.0%"
            i += 1
    for n, w in enumerate([14] * k + [14, 16, 13, 10, 10, 10, 11, 11, 12, 11, 14], 1):
        wd.column_dimensions[get_column_letter(n)].width = w
    if k == 2:
        wd.column_dimensions["B"].width = 20
    wd.freeze_panes = "A5"
    wd.auto_filter.ref = f"A4:{last}{i - 1}"


def time_tab(wb, at, R, P):
    """How long Test 6 took on the laptop, round by round, plus a fill-in Spark time/cost estimate."""
    t = pd.read_csv(os.path.join(D, "timing.csv"), parse_dates=["started", "finished"])
    g4, g3 = (t[t.judge == ai].set_index("round") for ai in (A, B))
    ws = wb.create_sheet("Time & cost", at)
    INPUT = PatternFill("solid", start_color="FFFF00")
    BLUE = Font(name="Arial", size=10, color="0000FF")

    def put(cell, v, font=F, fmt=None, fill=None):
        ws[cell] = v
        ws[cell].font = font
        if fmt:
            ws[cell].number_format = fmt
        if fill:
            ws[cell].fill = fill

    put("A1", "How long Test 6 took on Gordon's laptop, and what it might take on the Spark",
        Font(name="Arial", size=13, bold=True))
    put("A2", "Each round: first gemma4's run writes all the round's posts (both AIs' posts), then gemma4 plays the 100 "
              "people, then gemma3 plays the same 100 people. Blue numbers are measured times copied from "
              "data/llm_bias/two_ai/timing.csv; black numbers are formulas.")
    ws["A2"].alignment = Alignment(wrap_text=True, vertical="top")
    ws.merge_cells("A2:K2")
    ws.row_dimensions[2].height = 42
    hdr = ["Round", "Started", "Finished", "Writing posts (min)", "gemma4 playing the people (min)",
           "gemma3 playing the people (min)", "Whole round (min)", "Votes (both AIs)", "Seconds per vote",
           "Break before next round (min)", "Note"]
    for j, h in enumerate(hdr):
        c = ws.cell(row=4, column=j + 1, value=h)
        c.font, c.fill, c.alignment = FB, HEAD, Alignment(wrap_text=True, vertical="top")
    first, rounds = 5, sorted(g4.index)
    for n, r in enumerate(rounds):
        i = first + n
        put(f"A{i}", int(r))
        put(f"B{i}", g4.started[r].to_pydatetime().replace(microsecond=0), BLUE, "yyyy-mm-dd hh:mm")
        put(f"C{i}", g3.finished[r].to_pydatetime().replace(microsecond=0), BLUE, "yyyy-mm-dd hh:mm")
        write = float(g4.post_writing_min[r])
        put(f"D{i}", round(write, 2), BLUE, "0.0")
        # gemma4's run includes the post writing; its voting time is the rest
        put(f"E{i}", round(float(g4.world_wall_min[r]) - write, 2), BLUE, "0.0")
        put(f"F{i}", round(float(g3.world_wall_min[r]), 2), BLUE, "0.0")
        put(f"G{i}", f"=SUM(D{i}:F{i})", fmt="0.0")
        put(f"H{i}", int(g4.decisions[r] + g3.decisions[r]), BLUE, "#,##0")
        put(f"I{i}", f"=(E{i}+F{i})*60/H{i}", fmt="0.000")
        if n + 1 < len(rounds):
            put(f"J{i}", f"=(B{i + 1}-C{i})*1440", fmt="0.0")
    last = first + len(rounds) - 1
    gaps = [g4.started[rounds[n + 1]] - g3.finished[rounds[n]] for n in range(len(rounds) - 1)]
    pause = first + gaps.index(max(gaps))
    put(f"K{pause}", "Pause: the first 11 rounds were done; 4 more were started later. Not part of the run.")
    tot = last + 1
    put(f"A{tot}", "Total", FB)
    for c in "DEFG":
        put(f"{c}{tot}", f"=SUM({c}{first}:{c}{last})", FB, "0.0")
    put(f"H{tot}", f"=SUM(H{first}:H{last})", FB, "#,##0")
    put(f"I{tot}", f"=(E{tot}+F{tot})*60/H{tot}", FB, "0.000")
    put(f"J{tot}", f"=SUM(J{first}:J{last})-J{pause}", FB, "0.0")
    put(f"K{tot}", "Breaks = checks between rounds, not counting the pause")

    r0 = tot + 2
    put(f"A{r0}", "Totals in hours", FB)
    rows = [("Work (all 15 rounds)", f"=G{tot}/60"),
            ("Breaks between rounds", f"=J{tot}/60"),
            ("Analysis at the end (reproduce script)", 10 / 60),
            ("One full run, start to finish", f"=SUM(B{r0 + 1}:B{r0 + 3})")]
    for k, (lab, v) in enumerate(rows, 1):
        put(f"A{r0 + k}", lab, FB if k == 4 else F)
        put(f"B{r0 + k}", v, FB if k == 4 else (BLUE if k == 3 else F), "0.00")
    put(f"C{r0 + 3}", "About 10 minutes (estimate)")
    put(f"C{r0 + 2}", "The reproduce script skips most of these; kept here to be safe")

    r1 = r0 + 6
    put(f"A{r1}", "How much work the AIs did (from reactions.csv and posts.csv)", FB)
    work = [("Votes", len(R)),
            ("Posts written OK (6 lost their partner post, so 738 were shown)", int(P.ok.sum())),
            ("Post tries (including retries)", int(P.attempts.sum())),
            ("Tokens the AIs read (about ¾ of a word each)", int(R.prompt_tokens.sum())),
            ("Tokens the AIs wrote: votes + reasons", int(R.eval_tokens.sum())),
            ("Tokens the AIs wrote: posts", int(P.eval_tokens.sum()))]
    for k, (lab, v) in enumerate(work, 1):
        put(f"A{r1 + k}", lab)
        put(f"B{r1 + k}", v, BLUE, "#,##0")

    r2 = r1 + len(work) + 2
    put(f"A{r2}", "Spark estimate: fill in the yellow cells", FB)
    put(f"A{r2 + 1}", "Laptop: seconds per vote")
    put(f"B{r2 + 1}", f"=I{tot}", fmt="0.000")
    put(f"A{r2 + 2}", "Spark: seconds per vote (from the 5-minute check run)")
    put(f"B{r2 + 2}", 0.367, BLUE, "0.000", INPUT)
    put(f"C{r2 + 2}", "← put the Spark's number here (0.367 = same speed as the laptop)")
    put(f"A{r2 + 3}", "Spark is this many times faster")
    put(f"B{r2 + 3}", f"=B{r2 + 1}/B{r2 + 2}", fmt="0.0")
    put(f"A{r2 + 4}", "Spark hours for one full run")
    put(f"B{r2 + 4}", f"=B{r0 + 1}/B{r2 + 3}+B{r0 + 2}+B{r0 + 3}", FB, "0.00")
    put(f"C{r2 + 4}", "Work ÷ speed-up, plus breaks and analysis (those don't speed up). Assumes post writing speeds up like voting")
    put(f"A{r2 + 5}", "Cost per hour on the Spark ($)")
    put(f"B{r2 + 5}", 0, BLUE, "$#,##0.00", INPUT)
    put(f"C{r2 + 5}", "← put the hourly price here")
    put(f"A{r2 + 6}", "Estimated cost of one full run ($)")
    put(f"B{r2 + 6}", f"=B{r2 + 4}*B{r2 + 5}", FB, "$#,##0.00")
    for col, w in zip("ABCDEFGHIJK", [44, 17, 17, 11, 13, 13, 11, 10, 10, 12, 40]):
        ws.column_dimensions[col].width = w
    ws.freeze_panes = "A5"


def main():
    R = pd.read_csv(os.path.join(D, "reactions.csv"))
    P = pd.read_csv(os.path.join(D, "posts.csv"))
    U = pd.read_csv(os.path.join(D, "users.csv"))
    U["aff"] = U.topic_affinity.apply(ast.literal_eval)
    users = U.set_index("id")
    rows, qrow = [], []
    for rnd in sorted(R["round"].unique()):
        V = R[R["round"] == rnd]
        posts = P[(P["round"] == rnd) & P.ok & P.key.isin(set(V.post_key))].copy()
        posts["pid"] = posts.apply(
            lambda p: f"R{rnd:02d} {TOPICS[p.topic]['sub']} #{p.slot_in_topic + 1} by {short(p.author)}", axis=1)
        g4 = V[V.played_by == A].set_index(["user_id", "post_key"])
        g3 = V[V.played_by == B].set_index(["user_id", "post_key"])
        # the scroll order is the same for both AIs; check it rather than assume it
        both = g4[["topic_rank", "pos_in_topic"]].join(g3[["topic_rank", "pos_in_topic"]], rsuffix="_3")
        assert (both.topic_rank == both.topic_rank_3).all() and (both.pos_in_topic == both.pos_in_topic_3).all()
        pmap = posts.set_index("key")
        for u in sorted(V.user_id.unique()):
            mine = g4.loc[u].sort_values(["topic_rank", "pos_in_topic"])
            p = users.loc[u]
            for n, (key, r) in enumerate(mine.iterrows(), 1):
                post = pmap.loc[key]
                r3 = g3.loc[(u, key)]
                rows.append([int(rnd), int(u), p.realname, int(p.age), p.profession, HABIT[p.voting], n,
                             TOPICS[post.topic]["sub"], int(r.topic_rank) + 1, CARE[int(r.affinity)], post.pid,
                             short(post.author), post.title, post.body,
                             ACT.get(r.action, "(no answer)"), r.reason if isinstance(r.reason, str) else "",
                             ACT.get(r3.action, "(no answer)"), r3.reason if isinstance(r3.reason, str) else "", None])
        posts["order"] = posts.topic.map(TOPIC_ORDER.index)
        posts["aorder"] = posts.author.map({A: 0, B: 1})
        for p in posts.sort_values(["order", "slot_in_topic", "aorder"]).itertuples():
            qrow.append([p.pid, int(rnd), TOPICS[p.topic]["sub"], int(p.slot_in_topic) + 1, short(p.author)] +
                        list(ast.literal_eval(p.brief).values()) + [p.title, int(p.words), p.body] + [None] * 8)
    assert len(rows) * 2 == len(R)

    wb = Workbook()
    rd = wb.active
    rd.title = "README"
    S = "Scrolls!"
    # Scrolls
    ws = wb.create_sheet("Scrolls")
    hdr = ["Round", "Person #", "Name", "Age", "Job", "Voting habit", "Scroll position (1 = first post they saw)",
           "Subreddit", "Subreddit's place in their scroll (1 = favourite)", "How much they care about this subreddit",
           "Post ID", "Written by", "Post title", "Post text (exactly what they read)", f"When {short(A)} played them",
           f"{short(A)}'s reason", f"When {short(B)} played them", f"{short(B)}'s reason", "Did both AIs do the same?"]
    write_sheet(ws, hdr, rows, [7, 9, 18, 6, 22, 22, 11, 18, 12, 16, 34, 10, 45, 70, 14, 40, 14, 55, 12])
    formulas(ws, len(rows), lambda i: {"S": f'=IF(O{i}=Q{i},"same","different")'})
    # People (all rounds together)
    wp = wb.create_sheet("People")
    ph = ["Person #", "Name", "Username", "Age", "Gender", "Job", "Lives in", "Voting habit"] + \
         [TOPICS[t]["sub"] for t in TOPIC_ORDER] + \
         ["Posts seen (all 15 rounds)",
          f"{short(A)} played them: upvotes", "downvotes", "nothing", f"{short(B)} played them: upvotes", "downvotes", "nothing",
          f"{short(A)} played them: upvotes on {short(A)}'s posts", f"…on {short(B)}'s posts",
          f"{short(B)} played them: upvotes on {short(B)}'s posts", f"…on {short(A)}'s posts",
          "Posts where both AIs did the same", "Exact description the AI was given"]
    prow = [[int(u), p.realname, p.username, int(p.age), p.gender, p.profession, p.place, HABIT[p.voting]] +
            [CARE[p.aff[t]] for t in TOPIC_ORDER] + [None] * 12 + [p.persona] for u, p in users.sort_index().iterrows()]
    write_sheet(wp, ph, prow, [9, 18, 16, 6, 10, 22, 22, 20] + [14] * 5 + [12] * 12 + [90])
    formulas(wp, len(prow), lambda i: {
        "N": f"=COUNTIFS({S}$B:$B,$A{i})",
        "O": f'=COUNTIFS({S}$B:$B,$A{i},{S}$O:$O,"upvote")', "P": f'=COUNTIFS({S}$B:$B,$A{i},{S}$O:$O,"downvote")',
        "Q": f'=COUNTIFS({S}$B:$B,$A{i},{S}$O:$O,"nothing")', "R": f'=COUNTIFS({S}$B:$B,$A{i},{S}$Q:$Q,"upvote")',
        "S": f'=COUNTIFS({S}$B:$B,$A{i},{S}$Q:$Q,"downvote")', "T": f'=COUNTIFS({S}$B:$B,$A{i},{S}$Q:$Q,"nothing")',
        "U": f'=COUNTIFS({S}$B:$B,$A{i},{S}$L:$L,"{short(A)}",{S}$O:$O,"upvote")',
        "V": f'=COUNTIFS({S}$B:$B,$A{i},{S}$L:$L,"{short(B)}",{S}$O:$O,"upvote")',
        "W": f'=COUNTIFS({S}$B:$B,$A{i},{S}$L:$L,"{short(B)}",{S}$Q:$Q,"upvote")',
        "X": f'=COUNTIFS({S}$B:$B,$A{i},{S}$L:$L,"{short(A)}",{S}$Q:$Q,"upvote")',
        "Y": f'=COUNTIFS({S}$B:$B,$A{i},{S}$S:$S,"same")'})
    # Posts
    wq = wb.create_sheet("Posts")
    qh = ["Post ID", "Round", "Subreddit", "Pair # (both AIs wrote one from the same job card)", "Written by",
          "Job card: subject", "Job card: kind of post", "Job card: posting as", "Title", "Words", "Full text",
          f"{short(A)}'s people: upvotes", "downvotes", "nothing", f"{short(B)}'s people: upvotes", "downvotes", "nothing",
          f"Score from {short(A)}'s people (up − down)", f"Score from {short(B)}'s people (up − down)"]
    write_sheet(wq, qh, qrow, [36, 7, 18, 12, 10, 34, 30, 30, 45, 7, 80] + [12] * 8)
    formulas(wq, len(qrow), lambda i: {
        "L": f'=COUNTIFS({S}$K:$K,$A{i},{S}$O:$O,"upvote")', "M": f'=COUNTIFS({S}$K:$K,$A{i},{S}$O:$O,"downvote")',
        "N": f'=COUNTIFS({S}$K:$K,$A{i},{S}$O:$O,"nothing")', "O": f'=COUNTIFS({S}$K:$K,$A{i},{S}$Q:$Q,"upvote")',
        "P": f'=COUNTIFS({S}$K:$K,$A{i},{S}$Q:$Q,"downvote")', "Q": f'=COUNTIFS({S}$K:$K,$A{i},{S}$Q:$Q,"nothing")',
        "R": f"=L{i}-M{i}", "S": f"=O{i}-P{i}"})
    # Bias tabs: how each AI's people reacted to its own posts vs the other AI's posts, split different ways
    note = ("'AI playing the people' = which AI pretended to be the 100 people. Each row counts that AI's reactions to one "
            "AI's posts. The people never knew who wrote a post. Percentages are out of all its reactions to those posts "
            "(the 2 unreadable answers are left out). 'Own minus other's' = how many more percent of its own posts that AI "
            "upvoted than of the other AI's posts (below zero = it upvoted the other AI's posts more). All numbers are "
            "formulas counting the Scrolls sheet.")
    rounds = [(["All 15 rounds"], f'{S}$A:$A,">=1"')] + [([r], f"{S}$A:$A,{r}") for r in range(1, 16)]
    bias_tab(wb, 1, "Bias data", "How each AI reacted to its OWN posts vs the OTHER AI's posts, round by round", note,
             ["Round"], rounds)
    bias_tab(wb, 2, "By subreddit", "Own vs other AI's posts, in each subreddit (all 15 rounds)", note, ["Subreddit"],
             [([TOPICS[t]["sub"]], f'{S}$H:$H,"{TOPICS[t]["sub"]}"') for t in TOPIC_ORDER])
    bias_tab(wb, 3, "By interest", "Own vs other AI's posts, by how much the person cares about the post's subreddit "
             "(all 15 rounds)", note, ["How much the person cares about the subreddit"],
             [([CARE[k]], f'{S}$J:$J,"{CARE[k]}"') for k in sorted(CARE)])
    bias_tab(wb, 4, "By voting habit", "Own vs other AI's posts, by the person's voting habit (all 15 rounds)", note,
             ["Voting habit"], [([HABIT[k]], f'{S}$F:$F,"{HABIT[k]}"') for k in ["generous", "typical", "harsh"]])
    bias_tab(wb, 5, "Each person", "Own vs other AI's posts, for each of the 100 people (all 15 rounds)", note,
             ["Person #", "Name"], [([int(u), p.realname], f"{S}$B:$B,{int(u)}") for u, p in users.sort_index().iterrows()])
    time_tab(wb, 6, R, P)
    # README
    lines = [
        ("Test 6: every person's scroll in every round, post by post", FB),
        (f"15 rounds; in each, 100 people scroll every post of that round (46–50 posts). {len(rows):,} rows on the Scrolls "
         f"sheet; each row is one person seeing one post, with both AIs' reactions side by side (so all "
         f"{len(R):,} votes are here).", F),
        ("", F),
        ("How a round worked", FB),
        (f"Both AIs ({short(A)} and {short(B)}) wrote 5 new posts for each of the 5 subreddits from the same job cards. Then "
         f"{short(A)} pretended to be each person and scrolled every post, and later {short(B)} pretended to be the same "
         "person and scrolled the same posts in the same order. For each post the AI answered upvote, downvote or "
         "nothing, with a short reason.", F),
        ("The AI playing a person sees only: the person's description (People sheet, last column), the subreddit, the "
         "title and the post text. Never who wrote it, other people's votes or anything it voted before. Every vote is a "
         "fresh question.", F),
        ("", F),
        ("Sheets", FB),
        ("Bias data: for each round (and all rounds together), how many of each AI's posts each AI's people upvoted, "
         "downvoted or ignored, as counts and percentages. Own posts vs the other AI's posts.", F),
        ("Time & cost: how long every round took on the laptop, total hours, how much work the AIs did, and a "
         "fill-in estimate of hours and dollars on the Spark.", F),
        ("By subreddit / By interest / By voting habit / Each person: the same counts and percentages over all 15 rounds, "
         "split by the post's subreddit, by how much the person cares about that subreddit, by the person's voting habit, "
         "and for each of the 100 people.", F),
        ("Scrolls: one row per round per person per post, in the exact order that person saw them. Filter 'Round' and "
         "'Person #' to follow one person through one round; filter only 'Person #' to see them across all 15 rounds; "
         "filter 'Did both AIs do the same?' to see where the two AIs disagree about the same person.", F),
        ("People: the 100 people (the same 100 every round), how much each cares about each subreddit, the exact "
         "description the AI was given, and counts of their reactions over all 15 rounds (formulas over Scrolls).", F),
        ("Posts: every post of every round in full, its job card, and how each AI's 100 people reacted (formulas).", F),
        ("", F),
        ("Words used", FB),
        ("Scroll position: 1 = the first post the person saw that round. People see their favourite subreddit first and "
         "their least favourite last; inside a subreddit the posts are shuffled (a different shuffle per person and round).", F),
        ("How much they care: dislikes it / bored by it / doesn't care / enjoys it / loves it (fixed for each person).", F),
        ("Voting habit: upvotes almost everything / typical / hard to please (part of the description the AI reads).", F),
        ("Post ID: round, subreddit, pair number and author, e.g. 'R03 r/cars #2 by gemma4'. The post with the same "
         "round and pair number by the other AI was written from the same job card.", F),
        ("Fewer than 50 posts in a round: a few posts failed to write, so that round has 46 or 48.", F),
        ("'(no answer)': the AI's answer could not be read even after retrying (2 votes in the whole test, both round 13).", F),
        ("", F),
        ("Source: data/llm_bias/two_ai/reactions.csv, posts.csv and users.csv (GitHub KGordo11/oasis, branch llm-bias). "
         "Made by examples/experiment/llm_bias/make_scrolls_workbook.py.", F),
    ]
    for i, (t, font) in enumerate(lines, 1):
        rd[f"A{i}"] = t
        rd[f"A{i}"].font = Font(name="Arial", size=13, bold=True) if i == 1 else font
        rd[f"A{i}"].alignment = Alignment(wrap_text=True, vertical="top")
    rd.column_dimensions["A"].width = 130
    wb.calculation.fullCalcOnLoad = True
    wb.save(OUT)
    print(f"{len(rows):,} scroll rows, {len(qrow)} posts, {os.path.getsize(OUT) // 1024 // 1024} MB -> {OUT}")


if __name__ == "__main__":
    main()
