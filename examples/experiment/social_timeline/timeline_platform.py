"""TimelinePlatform: an instrumented, personalized OASIS platform.

Subclasses `Platform` so that `oasis/` stays byte-identical (decision D-1).
`env.py:103` accepts a `Platform` instance directly, so no upstream change is
needed to use this.

WHAT IT CHANGES
---------------
1. Ranking (D-13). Implements the TWHIN interest-based algorithm in-process
   using mean-pooled embeddings, because upstream's pooler path is
   non-deterministic and near-non-discriminative (bugs B-1/B-2, see
   embedding.py). Also captures per-(user, post) scores, which the upstream
   function does not return but which `rec_history` requires in order to
   answer "why did this post reach this user".

2. Exposure instrumentation (fixes finding F-4). Upstream runs
   `DELETE FROM rec` on every refresh (platform.py:383), so what an agent saw
   in any previous round is unrecoverable. Two accumulating tables fix that:

     rec_candidates -- the full scored candidate pool per user per round,
                       i.e. what COULD have been shown, with the score that
                       ranked it. Supports "why was this NOT shown".
     rec_history    -- what was ACTUALLY returned to the agent by refresh(),
                       with feed position and which source surfaced it.
                       One row per exposure event, so repeat exposures are
                       counted rather than collapsed -- the simulation turns
                       on how OFTEN one user sees another.

   Note the distinction: update_rec_table() produces only the candidate pool.
   refresh() decides the actual feed by random-sampling that pool and unioning
   it with follow-injected posts. Logging only the former would misreport what
   agents saw.

3. DM privacy (D-7). A group that has exactly two members is treated as a
   de-facto DM and further joins are refused, so emergent private
   conversations stay private.

A NAMING TRAP WORTH KNOWING
---------------------------
The `user` table has both `user_id` (1-based primary key) and `agent_id`.
Every OTHER table's `user_id` column actually stores the **agent_id**
(platform.py:407 -- `user_id = agent_id`). Upstream's rec insertion relies on
0-based positional indices coinciding with agent_id (finding F-12). This class
keys on `agent_id` explicitly everywhere instead, which removes that whole
class of off-by-one bug rather than reproducing it.

THE SCORING FORMULA, STATED PRECISELY
-------------------------------------
    profile(u) = bio(u)  [+ " # Recent post: " + most_recent_post(u)]
    age(p)     = current_time_step - created_at(p)
    recency(p) = log((271.8 - age(p)) / 100)
    sim(u, p)  = cosine(embed(profile(u)), embed(content(p)))
    score(u,p) = sim(u, p) * recency(p)

    Posts authored by u are excluded. The top `max_rec_post_len` posts by
    score become u's candidate pool.

`recency` follows upstream (recsys.py:470-472) and decays from 1.0 at age 0
toward 0 at age 171.8, beyond which it is undefined; ages past the cliff are
clamped and counted rather than allowed to produce NaN.
"""

from __future__ import annotations

import math
import os
import sys

# These modules sit alongside this file and are imported by name, so the
# directory must be importable regardless of the caller's cwd.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from oasis.social_platform.platform import Platform
from oasis.social_platform.recsys import reset_globals
from oasis.social_platform.typing import ActionType, RecsysType

from embedding import cosine_matrix, embed, get_embedder

# Upstream's recency constants (recsys.py:470-472), named rather than inlined.
RECENCY_NUMERATOR = 271.8
RECENCY_DIVISOR = 100.0
RECENCY_AGE_CLIFF = RECENCY_NUMERATOR - 1.0  # beyond this, log arg <= 0
RECENCY_FLOOR = 1e-6


class TimelinePlatform(Platform):
    """Personalized, fully instrumented platform. See module docstring."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # TWHIN keeps per-run state in module globals that persist across
        # calls and are cleared only here (finding F-7). Without this, a
        # second run in the same process inherits the first run's state.
        reset_globals()

        self._create_instrumentation_tables()

        # Counters surfaced at the end of a run so silent degradation shows up
        # as a number rather than as a plausible-looking result.
        self.stats = {
            "rounds_ranked": 0,
            "recency_clamped": 0,
            "empty_candidate_pools": 0,
            "refresh_calls": 0,
            "exposures_logged": 0,
            "dm_joins_refused": 0,
        }

    # ---------------------------------------------------------------- tables

    def _create_instrumentation_tables(self):
        """Create the accumulating tables. Additive only; no upstream table
        is altered."""
        self.db_cursor.executescript("""
            CREATE TABLE IF NOT EXISTS rec_candidates (
                round      INTEGER NOT NULL,
                agent_id   INTEGER NOT NULL,
                post_id    INTEGER NOT NULL,
                author_id  INTEGER,
                rank       INTEGER,
                sim        REAL,
                recency    REAL,
                score      REAL,
                PRIMARY KEY (round, agent_id, post_id)
            );

            CREATE TABLE IF NOT EXISTS rec_history (
                exposure_id   INTEGER PRIMARY KEY AUTOINCREMENT,
                round         INTEGER NOT NULL,
                agent_id      INTEGER NOT NULL,
                post_id       INTEGER NOT NULL,
                author_id     INTEGER,
                feed_position INTEGER,
                source        TEXT,
                score         REAL
            );

            CREATE TABLE IF NOT EXISTS round_boundary (
                round      INTEGER PRIMARY KEY,
                started_at TEXT,
                n_posts    INTEGER,
                n_follows  INTEGER
            );

            CREATE INDEX IF NOT EXISTS idx_rec_history_agent
                ON rec_history(agent_id, round);
            CREATE INDEX IF NOT EXISTS idx_rec_history_author
                ON rec_history(author_id);
        """)
        self.db.commit()

    # ------------------------------------------------------------- profiles

    def _build_profiles(self, user_rows, post_rows):
        """Return (agent_ids, profile_texts).

        Mirrors upstream's evolving-profile mechanism (recsys.py:509-520):
        a user's interest profile is their bio plus their most recent post, so
        interests drift toward what they actually talk about.
        """
        latest_post = {}
        for post in post_rows:
            # post rows arrive in insertion order, so later rows win.
            latest_post[post["user_id"]] = post["content"]

        agent_ids, texts = [], []
        for row in user_rows:
            agent_id = row["agent_id"]
            bio = (row["bio"] or "").strip() or "This user has no profile."
            recent = latest_post.get(agent_id)
            if recent:
                bio = f"{bio} # Recent post: {recent}"
            agent_ids.append(agent_id)
            texts.append(bio)
        return agent_ids, texts

    def _recency(self, age: int) -> float:
        """Upstream's log recency decay, clamped instead of allowed to NaN."""
        if age >= RECENCY_AGE_CLIFF:
            self.stats["recency_clamped"] += 1
            return RECENCY_FLOOR
        value = math.log((RECENCY_NUMERATOR - age) / RECENCY_DIVISOR)
        return max(value, RECENCY_FLOOR)

    # --------------------------------------------------------------- ranking

    async def update_rec_table(self):
        """Rank posts for every agent, then persist both the candidate pool
        and the round boundary. Called once per round by env.step()."""
        from oasis.social_platform.database import fetch_table_from_db

        round_no = int(self.sandbox_clock.time_step)
        user_rows = fetch_table_from_db(self.db_cursor, "user")
        post_rows = fetch_table_from_db(self.db_cursor, "post")

        self.db_cursor.execute("SELECT COUNT(*) FROM follow")
        n_follows = self.db_cursor.fetchone()[0]
        self.pl_utils._execute_db_command(
            "INSERT OR REPLACE INTO round_boundary "
            "(round, started_at, n_posts, n_follows) VALUES (?, ?, ?, ?)",
            (round_no, str(round_no), len(post_rows), n_follows), commit=True)

        if not post_rows:
            # Round 0: nobody has posted yet. An empty feed here is correct,
            # not a failure -- agents bootstrap by posting.
            self.pl_utils._execute_db_command("DELETE FROM rec", commit=True)
            return

        agent_ids, profile_texts = self._build_profiles(user_rows, post_rows)
        post_ids = [p["post_id"] for p in post_rows]
        authors = [p["user_id"] for p in post_rows]
        contents = [p["content"] or "" for p in post_rows]

        ages = []
        for p in post_rows:
            try:
                ages.append(round_no - int(p["created_at"]))
            except (TypeError, ValueError):
                ages.append(0)
        recency = [self._recency(a) for a in ages]

        user_vecs = embed(profile_texts)
        post_vecs = embed(contents)
        sims = cosine_matrix(user_vecs, post_vecs)

        self._assert_algorithm_ran(sims)

        rec_rows, candidate_rows = [], []
        for u_idx, agent_id in enumerate(agent_ids):
            scored = []
            for p_idx, post_id in enumerate(post_ids):
                if authors[p_idx] == agent_id:
                    continue  # never recommend a user their own post
                sim = float(sims[u_idx, p_idx])
                scored.append((sim * recency[p_idx], sim, p_idx))

            if not scored:
                self.stats["empty_candidate_pools"] += 1
                continue

            scored.sort(key=lambda t: t[0], reverse=True)
            top = scored[:self.max_rec_post_len]
            for rank, (score, sim, p_idx) in enumerate(top):
                rec_rows.append((agent_id, post_ids[p_idx]))
                candidate_rows.append(
                    (round_no, agent_id, post_ids[p_idx], authors[p_idx],
                     rank, sim, recency[p_idx], score))

        # Upstream wipes `rec` each round; that is preserved. The history now
        # lives in rec_candidates/rec_history instead of being lost.
        self.pl_utils._execute_db_command("DELETE FROM rec", commit=True)
        if rec_rows:
            self.pl_utils._execute_many_db_command(
                "INSERT INTO rec (user_id, post_id) VALUES (?, ?)",
                rec_rows, commit=True)
            self.pl_utils._execute_many_db_command(
                "INSERT OR REPLACE INTO rec_candidates (round, agent_id, "
                "post_id, author_id, rank, sim, recency, score) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                candidate_rows, commit=True)

        self.stats["rounds_ranked"] += 1

    def _assert_algorithm_ran(self, sims):
        """Fail loudly rather than silently degrading.

        Bug F-3 (RecsysType.TWITTER falling through to random.random()) and
        Sim 3's fail-open shield both produced plausible numbers from a broken
        mechanism. This makes that impossible to miss.
        """
        import torch

        _, model = get_embedder()
        if model is None:
            raise RuntimeError(
                "embedding model is not loaded -- ranking would be random")
        if sims.numel() == 0:
            return
        if torch.isnan(sims).any():
            raise RuntimeError("similarity matrix contains NaN")
        spread = float(sims.max() - sims.min())
        if spread < 1e-6:
            raise RuntimeError(
                f"similarity matrix is degenerate (spread={spread:.2e}); "
                f"every post scores identically, so ranking is meaningless")

    # --------------------------------------------------------------- refresh

    async def refresh(self, agent_id: int):
        """Upstream refresh(), instrumented to record true exposure.

        Behaviour is preserved exactly (platform.py:258-326); the only
        additions are the source attribution and the rec_history writes.
        """
        import random

        from oasis.social_platform.platform import datetime  # noqa: F401

        round_no = int(self.sandbox_clock.time_step)
        if self.recsys_type == RecsysType.REDDIT:
            current_time = self.sandbox_clock.time_transfer(
                __import__("datetime").datetime.now(), self.start_time)
        else:
            current_time = self.sandbox_clock.get_time_step()

        try:
            user_id = agent_id
            self.pl_utils._execute_db_command(
                "SELECT post_id FROM rec WHERE user_id = ?", (user_id, ))
            rec_post_ids = [row[0] for row in self.db_cursor.fetchall()]

            selected_post_ids = rec_post_ids
            if len(selected_post_ids) >= self.refresh_rec_post_count:
                selected_post_ids = random.sample(
                    selected_post_ids, self.refresh_rec_post_count)
            from_recsys = set(selected_post_ids)

            from_following = set()
            if self.recsys_type != RecsysType.REDDIT:
                self.pl_utils._execute_db_command(
                    "SELECT post.post_id, post.user_id, post.content, "
                    "post.created_at, post.num_likes FROM post "
                    "JOIN follow ON post.user_id = follow.followee_id "
                    "WHERE follow.follower_id = ? "
                    "ORDER BY post.num_likes DESC "
                    "LIMIT ?", (user_id, self.following_post_count))
                following_posts = self.db_cursor.fetchall()
                from_following = {row[0] for row in following_posts}
                selected_post_ids = list(from_following | from_recsys)

            if not selected_post_ids:
                return {"success": False, "message": "No posts found."}

            placeholders = ", ".join("?" for _ in selected_post_ids)
            self.pl_utils._execute_db_command(
                f"SELECT post_id, user_id, original_post_id, content, "
                f"quote_content, created_at, num_likes, num_dislikes, "
                f"num_shares FROM post WHERE post_id IN ({placeholders})",
                selected_post_ids)
            results = self.db_cursor.fetchall()
            if not results:
                return {"success": False, "message": "No posts found."}
            results_with_comments = self.pl_utils._add_comments_to_posts(
                results)

            self._log_exposure(round_no, agent_id, results, from_recsys,
                               from_following)

            action_info = {"posts": results_with_comments}
            self.pl_utils._record_trace(user_id, ActionType.REFRESH.value,
                                        action_info, current_time)
            self.stats["refresh_calls"] += 1
            return {"success": True, "posts": results_with_comments}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _log_exposure(self, round_no, agent_id, results, from_recsys,
                      from_following):
        """Record one row per post actually shown to this agent this refresh.

        Rows are appended, never deduplicated: seeing the same post three
        times is a materially different fact from seeing it once, and
        exposure frequency is what drives the propagation this simulation
        exists to study.
        """
        scores = {}
        self.pl_utils._execute_db_command(
            "SELECT post_id, score FROM rec_candidates "
            "WHERE round = ? AND agent_id = ?", (round_no, agent_id))
        for post_id, score in self.db_cursor.fetchall():
            scores[post_id] = score

        rows = []
        for position, row in enumerate(results):
            post_id, author_id = row[0], row[1]
            in_rec = post_id in from_recsys
            in_fol = post_id in from_following
            source = ("both" if in_rec and in_fol
                      else "recsys" if in_rec
                      else "following" if in_fol
                      else "unknown")
            rows.append((round_no, agent_id, post_id, author_id, position,
                         source, scores.get(post_id)))

        if rows:
            self.pl_utils._execute_many_db_command(
                "INSERT INTO rec_history (round, agent_id, post_id, "
                "author_id, feed_position, source, score) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)", rows, commit=True)
            self.stats["exposures_logged"] += len(rows)

    # ------------------------------------------------------------ DM privacy

    async def join_group(self, agent_id: int, group_id: int):
        """Refuse joins that would break up a de-facto DM (D-7).

        OASIS cannot express a targeted DM, so a two-member group is the
        closest thing that can emerge on its own. Letting a third party walk
        into one would make private conversation impossible to observe.
        """
        self.pl_utils._execute_db_command(
            "SELECT COUNT(*) FROM group_members WHERE group_id = ?",
            (group_id, ))
        row = self.db_cursor.fetchone()
        if row and row[0] == 2:
            self.stats["dm_joins_refused"] += 1
            return {
                "success": False,
                "error": ("This is a private conversation between two "
                          "people and cannot be joined."),
            }
        return await super().join_group(agent_id, group_id)
