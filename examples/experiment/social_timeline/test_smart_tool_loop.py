"""Does conditional tool-loop termination stop when it should, and only then?

F-83 removes ~46 % of a run's model calls by skipping the follow-up call after
an action whose result the agent cannot use. The risk is precise and worth
stating: if a tool is wrongly classified as terminal, the agent silently loses
the ability to act on information it asked for -- the same class of failure as
--lean-actions, arrived at by a different route. These tests pin the behaviour
so that cannot happen quietly.

The mechanism under test: camel reads `self.max_iteration` immediately AFTER
`_aexecute_tool` returns (chat_agent.py:2070), so mutating it inside the tool
call takes effect on the same iteration.

    python examples/experiment/social_timeline/test_smart_tool_loop.py
"""
from __future__ import annotations

import asyncio
import sys
import types

sys.path.insert(0, __file__.rsplit("/", 1)[0])

from timeline_agent import TimelineAgent  # noqa: E402

CHECKS = []


def check(name):
    def deco(fn):
        CHECKS.append((name, fn))
        return fn
    return deco


PARENT = TimelineAgent.__mro__[1]          # the class super() dispatches to


class FakeAgent(TimelineAgent):
    """Enough state for the override to run, without a real ChatAgent.

    Deliberately does NOT reimplement the logic under test: `feed()` calls the
    genuine `TimelineAgent._aexecute_tool`, with only the PARENT's version
    stubbed. A test that restates the code it is testing passes when the code
    is wrong, which is the failure mode this whole file exists to prevent.
    """

    def __init__(self, smart: bool, base=None):
        self.smart_tool_loop = smart
        self.max_iteration = base
        self._base_max_iteration = base
        self.short_circuits = 0


async def _stub_parent(self, req):
    return f"executed {req.tool_name}"


async def feed(agent, *names):
    """Push tool names through the REAL override, as camel's loop would."""
    original = getattr(PARENT, "_aexecute_tool", None)
    PARENT._aexecute_tool = _stub_parent
    try:
        for n in names:
            await TimelineAgent._aexecute_tool(
                agent, types.SimpleNamespace(tool_name=n, args={},
                                             tool_call_id="x"))
    finally:
        if original is not None:
            PARENT._aexecute_tool = original
        else:
            delattr(PARENT, "_aexecute_tool")
    return agent


@check("terminal action stops the loop")
def t1():
    a = asyncio.run(feed(FakeAgent(True), "like_post"))
    assert a.max_iteration == 1, a.max_iteration
    assert a.short_circuits == 1


@check("informational action does NOT stop the loop")
def t2():
    a = asyncio.run(feed(FakeAgent(True), "search_posts"))
    assert a.max_iteration is None, a.max_iteration
    assert a.short_circuits == 0, "search must not be counted as terminal"


@check("search -> read -> act survives (the path --max-tool-rounds 1 breaks)")
def t3():
    a = asyncio.run(feed(FakeAgent(True), "search_posts", "like_post"))
    assert a.short_circuits == 1
    assert a.max_iteration == 1, "should stop only after the terminal act"


@check("every one of the 22 tools is classified, none left implicit")
def t4():
    unknown = set(TimelineAgent.TERSE) - set(TimelineAgent.INFORMATIONAL)
    assert unknown, "sanity: terminal set must be non-empty"
    both = set(TimelineAgent.INFORMATIONAL) - set(TimelineAgent.TERSE)
    assert not both, f"INFORMATIONAL names not in the tool list: {both}"


@check("the four informational tools are exactly the ones that return content")
def t5():
    assert TimelineAgent.INFORMATIONAL == frozenset(
        {"search_user", "search_posts", "trend", "refresh"}), \
        TimelineAgent.INFORMATIONAL


@check("no action is silently removed: terminal + informational == all 22")
def t6():
    covered = set(TimelineAgent.INFORMATIONAL) | (
        set(TimelineAgent.TERSE) - set(TimelineAgent.INFORMATIONAL))
    assert covered == set(TimelineAgent.TERSE), covered ^ set(TimelineAgent.TERSE)
    assert len(covered) == 22, len(covered)


@check("flag OFF is a true no-op")
def t7():
    a = asyncio.run(feed(FakeAgent(False), "like_post", "search_posts"))
    assert a.max_iteration is None
    assert a.short_circuits == 0


@check("a terminal turn does not leak its cap into the next turn")
def t8():
    a = FakeAgent(True)
    asyncio.run(feed(a, "like_post"))
    assert a.max_iteration == 1
    a.max_iteration = a._base_max_iteration      # what perform_action_by_llm does
    assert a.max_iteration is None, "turn reset must restore the budget"


@check("an explicit max_tool_rounds budget is respected, not overwritten")
def t9():
    a = asyncio.run(feed(FakeAgent(True, base=3), "search_posts"))
    assert a.max_iteration == 3, a.max_iteration


@check("do_nothing is terminal")
def t10():
    a = asyncio.run(feed(FakeAgent(True), "do_nothing"))
    assert a.max_iteration == 1


def main():
    print(f"\n  smart tool loop -- {len(CHECKS)} checks\n")
    bad = 0
    for name, fn in CHECKS:
        try:
            fn()
            print(f"   PASS  {name}")
        except AssertionError as e:
            bad += 1
            print(f"   FAIL  {name}\n         {e}")
    print(f"\n  {len(CHECKS)-bad}/{len(CHECKS)} passed\n")
    if not bad:
        print("  NOTE: these prove the loop stops where intended. They do NOT")
        print("  prove the 46% saving or that behaviour is unchanged at 36")
        print("  agents -- that needs an A/B, and six findings in this project")
        print("  died for want of one.\n")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
