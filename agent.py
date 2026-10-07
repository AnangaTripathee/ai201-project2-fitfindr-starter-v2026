"""
The FitFindr planning loop.

This is the file that makes FitFindr an agent rather than a script. It decides
which tool to run next based on what the last one returned.

If your loop calls all three tools no matter what comes back, you have a list
of function calls. A loop looks at the last result before it picks the next
step. **That branch is the graded part of this unit.**

Build and test your three tools in `tools.py` first. Then come here.

    python agent.py          runs both example paths below
"""

import os
import re

import config
import trace
from tools import search_listings, suggest_outfit, create_fit_card
from generate import ModelUnavailable


# ── session state ─────────────────────────────────────────────────────────────

def new_session(query: str, wardrobe: dict) -> dict:
    """
    A fresh session for one user interaction.

    The session is the single source of truth for a run. Every tool result goes
    in here, and the next tool reads it back out.

    You could pass values straight from one call to the next. It would work,
    and you would not be able to test it — you can't print a variable you have
    already overwritten. Going through the session is what makes the state
    visible, and unit 4 has you write a criterion about exactly that.

    Add fields if you need them.
    """
    return {
        "query": query,              # what the user typed
        "parsed": {},                # description / size / max_price you pulled out of it
        "search_results": [],        # everything search_listings returned
        "selected_item": None,       # the one you chose — goes into suggest_outfit
        "wardrobe": wardrobe,        # the user's wardrobe
        "outfit_suggestion": None,   # what suggest_outfit returned
        "fit_card": None,            # what create_fit_card returned
        "error": None,               # set when the run ended early
    }


# ── planning loop ─────────────────────────────────────────────────────────────

def run_agent(query: str, wardrobe: dict) -> dict:
    """
    Run the loop once and return the finished session.

    Args:
        query:    what the user asked for, in plain language
                  (e.g. "vintage graphic tee under $30, size M").
        wardrobe: a wardrobe dict — get_example_wardrobe() or
                  get_empty_wardrobe() from utils/data_loader.py.

    Returns:
        The session dict. **Check session["error"] first** — if it isn't None,
        the run ended early and the later fields will still be None.

    ─────────────────────────────────────────────────────────────────────────
    TODO — build this, following the branch rule you wrote in Milestone 2.

      1. Start a session with new_session().

      2. Count the times round the loop, and call trace.check_iterations(count)
         on each one before you go again. It raises when the count passes
         MAX_ITERATIONS in config.py — see trace.py.

      3. Parse the query into a description, a size, and a max_price. Regex,
         string splitting, or asking the model are all fine — say which you
         chose in your README. Put the result in session["parsed"].

      4. Call search_listings() with what you parsed.
         Put the results in session["search_results"].

         ⚠️ THIS IS THE BRANCH. If nothing came back:
              - put a message in session["error"] saying what the user could
                change — "No results" is not that message
              - return the session
              - do NOT call suggest_outfit with nothing

      5. Choose an item — the first result is fine. Put it in
         session["selected_item"].

      6. Call suggest_outfit() with the selected item and the wardrobe.
         Put the result in session["outfit_suggestion"].

      7. Call create_fit_card() with the outfit and the item.
         Put the result in session["fit_card"].

      8. Return the session.

    ─────────────────────────────────────────────────────────────────────────
    IN UNIT 4 you come back and add two things:

      • Trace calls. One per step. `trace.step("search_listings", inputs=...,
        returned=...)` — see trace.py. Your README needs the output.

      • A handler for ModelUnavailable, so a bad key produces a message rather
        than a stack trace. The import is already at the top of this file.
    """
    session = new_session(query, wardrobe)
    steps = 0

    # Step 1: parse the query with regex (no model call).
    steps += 1
    trace.check_iterations(steps)
    session["parsed"] = parse_query(query)

    # Step 2: search, reading the parsed values back out of the session.
    steps += 1
    trace.check_iterations(steps)
    parsed = session["parsed"]
    session["search_results"] = search_listings(
        parsed["description"], parsed["size"], parsed["max_price"]
    )

    if DEBUG:
        print(f"[debug] search_results has {len(session['search_results'])} item(s)")

    # THE BRANCH: nothing found means stop here, before any model call.
    if not session["search_results"]:
        session["error"] = _no_results_message(session["parsed"])
        return session

    session["selected_item"] = session["search_results"][0]

    # Step 3: outfit, from what's in the session — not from a local variable.
    steps += 1
    trace.check_iterations(steps)
    session["outfit_suggestion"] = suggest_outfit(
        session["selected_item"], session["wardrobe"]
    )

    # Step 4: fit card, again read back from the session.
    steps += 1
    trace.check_iterations(steps)
    session["fit_card"] = create_fit_card(
        session["outfit_suggestion"], session["selected_item"]
    )
    return session


# Set FITFINDR_DEBUG=1 to print the value the branch checks.
DEBUG = os.getenv("FITFINDR_DEBUG") == "1"


def parse_query(query: str) -> dict:
    """
    Pull max_price, size and description out of plain text with regex.

        "vintage graphic tee under $30, size M"
        → {"description": "vintage graphic tee", "size": "M", "max_price": 30.0}
    """
    text = query.lower()

    max_price = None
    price = re.search(r"(?:under|below|less than|max)?\s*\$\s*(\d+(?:\.\d+)?)", text) or \
        re.search(r"(?:under|below|less than)\s+(\d+(?:\.\d+)?)", text)
    if price:
        max_price = float(price.group(1))
        text = text.replace(price.group(0), " ")

    size = None
    size_match = re.search(r"(?:in\s+)?size\s+([a-z0-9./]+(?:\s*\d+(?:\.\d+)?)?)", text)
    if size_match:
        size = size_match.group(1).strip().upper()
        text = text.replace(size_match.group(0), " ")

    for filler in ("looking for", "i want", "find me"):
        text = text.replace(filler, " ")
    words = [w for w in re.split(r"[^a-z0-9]+", text) if w and w != "a"]
    return {"description": " ".join(words), "size": size, "max_price": max_price}


def _no_results_message(parsed: dict) -> str:
    """Say what was searched and name concrete things to change, not just 'no results'."""
    searched = f"'{parsed['description'] or 'anything'}'"
    if parsed["size"]:
        searched += f" in size {parsed['size']}"
    if parsed["max_price"] is not None:
        searched += f" under ${parsed['max_price']:.0f}"

    tips = []
    if parsed["max_price"] is not None:
        tips.append(f"raise the price ceiling (listings run $12–$75; try 'under $40' instead of 'under ${parsed['max_price']:.0f}')")
    if parsed["size"]:
        tips.append(f"try a different size or leave the size out (sizes in stock include S, M, L, XL, US 7–9 and W27–W32)")
    tips.append("use fewer or broader keywords, like 'dress' or 'jacket' instead of a specific style")
    return f"No listings matched {searched}. You could: " + "; ".join(tips) + "."


# ── running it directly ───────────────────────────────────────────────────────

def _show(session: dict) -> None:
    if session["error"]:
        print(f"  stopped: {session['error']}")
        print(f"  fit_card is {session['fit_card']!r} — it should still be None here")
        return

    item = session["selected_item"] or {}
    print(f"  found:    {item.get('title')} — ${item.get('price')} on {item.get('platform')}")
    print(f"  outfit:   {session['outfit_suggestion']}")
    print(f"  fit card: {session['fit_card']}")


if __name__ == "__main__":
    from utils.data_loader import get_example_wardrobe

    print("=== A query the data can match ===")
    _show(run_agent(
        query="looking for a vintage graphic tee under $30",
        wardrobe=get_example_wardrobe(),
    ))

    print("\n=== A query it can't ===")
    _show(run_agent(
        query="designer ballgown size XXS under $5",
        wardrobe=get_example_wardrobe(),
    ))

    print(
        "\nThe second one should stop before the fit card. If both paths look "
        "the same,\nthe branch isn't doing anything yet."
    )
