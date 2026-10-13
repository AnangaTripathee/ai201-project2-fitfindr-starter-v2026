"""
The runs your test needs. ← UNIT 4, MILESTONE 3

Each of your five criteria needs something run against it. A criterion about
the empty-search branch needs an impossible query. One about the fit card needs
the same item run more than once. Working that out is Milestone 3's first step,
and this file is where you write it down.

`run_eval.py` runs everything here five times and writes the run log — five
because your criteria are written out of five.

Three scenarios are filled in to show the shape. Add or change whatever your
own criteria need — these are a starting point, not a fixed set.
"""

SCENARIOS = [
    {
        # A query the data can match. Criterion 1.
        "name": "matching query completes",
        "query": "vintage graphic tee under $30",
        "wardrobe": "example",
        "criterion": 1,
    },
    {
        # A query nothing can match. Criterion 2 — the branch.
        "name": "impossible query stops early",
        "query": "designer ballgown size XXS under $5",
        "wardrobe": "example",
        "criterion": 2,
    },
    {
        # A user with nothing saved. One of unit 4's three failure modes.
        "name": "empty wardrobe",
        "query": "denim jacket under $50",
        "wardrobe": "empty",
        "criterion": None,
    },
    # Criterion 3 — the five named queries from criteria.md. The id that
    # suggest_outfit logs in the trace (from its own new_item) is compared with
    # selected_item, and the outfit text is checked for 2 title words.
    {"name": "c3 q1 vintage graphic tee", "query": "vintage graphic tee under $30",
     "wardrobe": "example", "criterion": 3},
    {"name": "c3 q2 90s track jacket", "query": "90s track jacket in size M",
     "wardrobe": "example", "criterion": 3},
    {"name": "c3 q3 silk slip dress", "query": "silk slip dress in midi length under $40",
     "wardrobe": "example", "criterion": 3},
    {"name": "c3 q4 platform sneakers", "query": "platform sneakers size 8",
     "wardrobe": "example", "criterion": 3},
    {"name": "c3 q5 denim jacket", "query": "denim jacket under $50",
     "wardrobe": "example", "criterion": 3},
    {
        # Criterion 4 — the fit card on lst_006. This query's top result is
        # lst_006 (checked: no tie), so the five tries are five fit cards on
        # the same item, cache off.
        "name": "c4 fit card on lst_006",
        "query": "bootleg tour graphic tee",
        "wardrobe": "example",
        "criterion": 4,
    },
    # Criterion 5 — the five named size/price queries from criteria.md.
    {"name": "c5 q1 graphic tee L", "query": "graphic tee size L under $30",
     "wardrobe": "example", "criterion": 5},
    {"name": "c5 q2 top M", "query": "top size M under $25",
     "wardrobe": "example", "criterion": 5},
    {"name": "c5 q3 bucket hat M", "query": "bucket hat size M under $20",
     "wardrobe": "example", "criterion": 5},
    {"name": "c5 q4 sneakers 8", "query": "sneakers size 8 under $50",
     "wardrobe": "example", "criterion": 5},
    {"name": "c5 q5 jacket S", "query": "jacket size S under $45",
     "wardrobe": "example", "criterion": 5},
]

WARDROBES = ("example", "empty")


def validate() -> list[str]:
    """Complain about anything malformed, before a long run rather than during."""
    problems = []
    for i, scenario in enumerate(SCENARIOS, 1):
        if not scenario.get("query", "").strip():
            problems.append(f"scenario {i} has no query")
        if scenario.get("wardrobe") not in WARDROBES:
            problems.append(
                f"scenario {i} has wardrobe {scenario.get('wardrobe')!r} — "
                f"it should be one of {WARDROBES}"
            )
    return problems
