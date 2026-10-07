"""
The three FitFindr tools.

Each one is a standalone function you can call and test on its own, before any
of them are wired into the loop. Build and test them one at a time — three
untested tools joined by a loop is one problem that looks like six, because you
can't tell which layer is lying to you.

    search_listings(description, size, max_price)  → list[dict]
    suggest_outfit(new_item, wardrobe)             → str
    create_fit_card(outfit, new_item)              → str

All three are stubs right now. They run and they do nothing — that's the
starting position and it's deliberate.

⚠️ Before you write any of them, fill in the **Tool Inventory** section of your
README (Milestone 2). Four lines per tool: what it does, each input with its
type, exactly what it returns, and what it returns when it has nothing to give.
That last line is what your loop branches on. "Returns a list" earns nothing —
the description has to say what is *in* the list.
"""

import re

import config
from generate import generate
from utils.data_loader import load_listings


# ── Tool 1: search_listings ───────────────────────────────────────────────────

def search_listings(
    description: str,
    size: str | None = None,
    max_price: float | None = None,
) -> list[dict]:
    """
    Search the listings data for items matching a description, and optionally a
    size and a price ceiling.

    This is the tool that doesn't call the model, which makes it the easiest one
    to test and the one to move onto MCP in unit 4.

    Args:
        description: keywords describing what the user wants
                     (e.g. "vintage graphic tee").
        size:        a size string to filter by, or None to skip size filtering.
                     Match case-insensitively — "M" should match "S/M".

                     ⚠️ Read the sizes in the data before you reach for a plain
                     substring test. `"s" in "us 9"` is True, and so is
                     `"l" in "xl"`. A filter that returns shoes when someone
                     asked for a small top reads like a broken search, and it
                     will quietly cost you in unit 4 when you test criterion 1.
                     What counts as a size match is part of your spec — decide
                     it and write it into your Tool Inventory.
        max_price:   maximum price, inclusive, or None to skip price filtering.

    Returns:
        A list of matching listing dicts, best match first.
        **Returns an empty list when nothing matches — an empty list, not None,
        and not an exception.** Your loop branches on this.

    Each listing dict has these fields:
        id, title, description, category, style_tags (list), size,
        condition, price (float), colors (list), brand (str or None), platform

    Note that `brand` is None for most listings. That is deliberate and
    realistic — thrift listings often have no brand. If something you write
    assumes a brand is always there, you will find out in unit 4.

    TODO:
        1. Load every listing with load_listings().
        2. Filter by max_price and by size, when each is provided.
        3. Score what's left by keyword overlap with `description`.
        4. Drop anything scoring zero.
        5. Sort by score, highest first, and return the listing dicts —
           at most config.SEARCH_RESULT_LIMIT of them.

    Test it from a terminal before you move on:
        python -c "from tools import search_listings; print(search_listings('graphic tee', max_price=30))"
    """
    keywords = [w for w in _words(description) if w not in _FILLER]

    results = []
    for listing in load_listings():
        if max_price is not None and listing["price"] > max_price:
            continue
        if size and not _size_matches(size, listing["size"]):
            continue

        # Title and tags are what the listing is; description, category and
        # colors are supporting detail, so they count for less.
        strong = _words(listing["title"]) | _words(" ".join(listing["style_tags"]))
        weak = _words(listing["description"]) | _words(listing["category"]) | _words(" ".join(listing["colors"]))
        score = sum(2 if w in strong else 1 if w in weak else 0 for w in keywords)

        # No keywords left (e.g. "size M under $30") means keep everything the
        # filters let through, rather than quietly returning nothing.
        if keywords and score == 0:
            continue
        results.append((score, listing))

    results.sort(key=lambda pair: (-pair[0], pair[1]["price"]))
    return [listing for _, listing in results[: config.SEARCH_RESULT_LIMIT]]


_FILLER = {"a", "the", "for", "and", "with", "in", "of"}


def _stem(word: str) -> str:
    """Drop one trailing plural 's' so 'tees' matches 'tee'. Keeps 'ss' words like 'dress'."""
    return word[:-1] if len(word) > 3 and word.endswith("s") and not word.endswith("ss") else word


def _words(text: str) -> set[str]:
    """Lowercase, split on anything that isn't a letter or digit, and stem."""
    return {_stem(w) for w in re.split(r"[^a-z0-9]+", text.lower()) if w}


def _size_tokens(size: str) -> set[str]:
    return {t for t in re.split(r"[\s/()]+", size.upper()) if t}


def _size_matches(wanted: str, listing_size: str) -> bool:
    """
    Whole-token match, not substring: "M" matches "S/M" but not "XL", and
    "8" matches "US 8" but not "US 8.5". One-size items fit any request.
    """
    if listing_size.upper().startswith("ONE SIZE"):
        return True
    return _size_tokens(wanted) <= _size_tokens(listing_size)


# ── Tool 2: suggest_outfit ────────────────────────────────────────────────────

def suggest_outfit(new_item: dict, wardrobe: dict | list) -> str:
    """
    Given a thrifted item and the user's wardrobe, suggest one or two outfits.

    This one calls the model, through `generate()`. You don't need to think
    about rate limits — the adapter handles pacing for you.

    Args:
        new_item: a listing dict — the item the user is considering.
        wardrobe: a wardrobe dict with an 'items' key holding a list of items.
                  **It may be empty.** Handle that.

    Returns:
        A non-empty string with outfit suggestions.
        With an empty wardrobe, return general styling advice rather than
        raising or returning "". Unit 4 has you trigger the empty wardrobe on
        purpose, so decide now what it should do.

    TODO:
        1. Check whether wardrobe['items'] is empty.
        2. If it is, ask the model for general styling ideas for this item.
        3. If it isn't, format the wardrobe items into the prompt and ask for
           specific combinations naming pieces the user already owns.
        4. Return the model's response.

    Test it from a terminal before you move on:
        python -c "from tools import suggest_outfit; from utils.data_loader import get_example_wardrobe, load_listings; print(suggest_outfit(load_listings()[0], get_example_wardrobe()))"
    """
    # The spec accepts either {"items": [...]} or the bare list.
    items = wardrobe.get("items", []) if isinstance(wardrobe, dict) else (wardrobe or [])
    item_text = _describe_item(new_item)

    if not items:
        prompt = (
            f"Someone is thinking about buying this thrifted item:\n{item_text}\n\n"
            "They haven't saved any of their own clothes yet. Give two short, "
            "general outfit ideas for it: what kinds of pieces, colours and shoes "
            "go with it, and the vibe each outfit gives. Plain text, no markdown "
            "headings, under 120 words."
        )
        advice = generate(prompt, system=_STYLIST)
        return f"No wardrobe saved yet — general styling ideas:\n{advice or _FALLBACK_ADVICE}"

    wardrobe_text = "\n".join(
        f"- {w['name']} ({w['category']}; colors: {', '.join(w['colors'])}; "
        f"style: {', '.join(w['style_tags'])}"
        + (f"; note: {w['notes']}" if w.get("notes") else "")
        + ")"
        for w in items
    )
    prompt = (
        f"Someone is thinking about buying this thrifted item:\n{item_text}\n\n"
        f"Here is what they already own:\n{wardrobe_text}\n\n"
        "Suggest one or two outfits built around the new item. Call the new item "
        f'"{new_item["title"]}". Name each piece they already own exactly as '
        "written above, and only use pieces from that list. After each outfit, "
        "add one line on why it works. Plain text, no markdown headings, under "
        "150 words."
    )
    return generate(prompt, system=_STYLIST) or _FALLBACK_ADVICE


_STYLIST = "You are a friendly thrift-store stylist. Be specific and practical."
_FALLBACK_ADVICE = "Pair it with simple basics in neutral colours and let it be the statement piece."


def _describe_item(item: dict) -> str:
    """The listing as prompt text. brand is None for most listings, so it's only included when present."""
    lines = [
        f"Title: {item['title']}",
        f"Category: {item['category']}",
        f"Colors: {', '.join(item['colors'])}",
        f"Style: {', '.join(item['style_tags'])}",
        f"Size: {item['size']}",
        f"Condition: {item['condition']}",
        f"Price: ${item['price']:.0f}",
        f"Platform: {item['platform']}",
        f"Description: {item['description']}",
    ]
    if item.get("brand"):
        lines.insert(1, f"Brand: {item['brand']}")
    return "\n".join(lines)


# ── Tool 3: create_fit_card ───────────────────────────────────────────────────

def create_fit_card(outfit: str, new_item: dict) -> str:
    """
    Write a short caption someone would actually post about the find.

    This calls the model too.

    Args:
        outfit:   the outfit suggestion string from suggest_outfit().
        new_item: the listing dict for the item.

    Returns:
        A two-to-four sentence caption.
        If `outfit` is empty or whitespace, return a descriptive message rather
        than raising.

    The caption should read like a real post rather than a product description,
    mention the item and its price and platform once each, and be specific about
    the vibe.

    It should also come out **differently for different inputs**. If you run
    this three times on the same item and get three word-for-word identical
    strings, it's one of two things, and both are near the top of `config.py`:

        • CACHE_ENABLED — the adapter handed back an answer it already had
        • TEMPERATURE   — at 0.0 the model gives the same words every time

    TODO:
        1. Guard against an empty or whitespace-only `outfit`.
        2. Build a prompt with the item details and the outfit.
        3. Call generate() and return the response.

    Test it from a terminal before you move on:
        python -c "from tools import create_fit_card; from utils.data_loader import load_listings; print(create_fit_card('jeans and white sneakers', load_listings()[0]))"
    """
    if not outfit or not outfit.strip():
        return f"Can't write a fit card for {new_item['title']} yet — there's no outfit suggestion to describe."

    short_title = new_item["title"].split("—")[0].strip()
    brand_rule = (
        f"Mention the brand ({new_item['brand']}) once."
        if new_item.get("brand")
        else "Don't mention a brand."
    )
    prompt = (
        f"Write a caption for a social media post about a thrift find.\n\n"
        f"Item: {short_title}\n"
        f"Price: ${new_item['price']:.0f}\n"
        f"Platform: {new_item['platform']}\n"
        f"How I'm styling it: {outfit}\n\n"
        f"Rules: 2 to 4 sentences, under 280 characters in total. Casual and "
        f'first person, like a real post, not a product description. Say '
        f'"{short_title}", the price as ${new_item["price"]:.0f} and '
        f"{new_item['platform']}, each exactly once. {brand_rule} Be specific "
        f"about the vibe. Return only the caption."
    )
    # Temperature comes from config.TEMPERATURE (0.9), so wording varies run to run.
    return generate(prompt).strip()
