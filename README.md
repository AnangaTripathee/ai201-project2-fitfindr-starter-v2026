# FitFindr

> ### 👋 Start here
>
> **New to this repo? Read [RUNNING.md](RUNNING.md) first** — setup, every
> command, and what to do when something breaks.
>
> Once `python test.py` passes:
>
> ```bash
> python app.py listings --full -n 6      # read the data (Milestone 1)
> python app.py fields                    # what you can filter on
> python app.py ask 'vintage graphic tee under $30'
> ```
>
> All three tools are stubs, so that last command will do nothing useful yet.
> That's the starting position.
>
> **The rest of this file is your submission.** Fill it in as you go.

---

<!-- ─────────────────────────────────────────────────────────────────────────
     HOW TO USE THIS FILE

     This is your submission. Fill each section in as you finish the milestone
     it belongs to — don't leave it all to the end.

     Unit 3 asks for the first five sections. Unit 4 adds the five below them.
     Leave the unit 4 sections alone until then; they're here so you know
     what's coming.

     Everything is pasted as TEXT. No screenshots, no images, no video links.
     A typed block of output gets full credit; a picture of the same output
     gets none.
     ───────────────────────────────────────────────────────────────────────── -->

<!-- ═══════════════════════ UNIT 3 — THE BUILD ═══════════════════════ -->

## What This Does

You type what you're hunting for in plain language, like `'vintage graphic tee under $30'` or `'jacket size S under $45'`. FitFindr pulls a price ceiling, a size and keywords out of that sentence, then searches 40 thrift listings from Depop, thredUp and Poshmark. It picks the best match and asks the model for one or two outfits that use pieces already in your wardrobe (or general styling ideas if your wardrobe is empty). Then it writes a short caption you could post about the find. If nothing matches, it stops before calling the model and tells you exactly what to change: the price ceiling, the size or the keywords.

---

## Tool Inventory

### `search_listings`

- **What it does:** Finds the thrift listings in `data/listings.json` (loaded with `utils.data_loader.load_listings()`) that match a keyword description, a size and a price ceiling, best match first. It does not call the model.
- **Inputs:**
  - `description` (str): keywords such as `"vintage graphic tee"`. It is lowercased and split into words; filler words (`a`, `the`, `for`, `and`, `with`, `in`, `of`) are dropped.
  - `size` (str or None): a size such as `"M"`, `"8"`, `"US 8"` or `"W30"`. `None` skips the size filter. Both sizes are uppercased and split into tokens on spaces, `/` and parentheses. A listing passes when **every token of the requested size is a whole token of the listing's `size`**. So `"M"` matches `M`, `S/M` and `M/L` but not `XL (oversized)`; `"8"` matches `US 8` but not `US 8.5`; `"S"` does not match `US 9`. Listings whose size starts with `One Size` pass any size filter, because they fit anyone.
  - `max_price` (float or None): the price ceiling, inclusive (`price <= max_price`). `None` skips the price filter.
- **Returns:** a `list[dict]` of at most `config.SEARCH_RESULT_LIMIT` (10) listings. Each dict is the unchanged listing with all 11 fields: `id` (str), `title` (str), `description` (str), `category` (str), `style_tags` (list[str]), `size` (str), `condition` (str), `price` (float), `colors` (list[str]), `brand` (str or None) and `platform` (str). Text is lowercased and split into words on anything that isn't a letter or digit, so the tag `"graphic tee"` gives the words `graphic` and `tee`. Each keyword scores 2 if it is one of the words of the `title` or `style_tags`, and 1 if it appears only in the `description`, `category` or `colors`. A trailing plural `s` is ignored on both sides of words longer than 3 letters, unless the word ends in `ss`, so `tees` matches `tee` but `dress` stays `dress`. A listing's score is the sum over all keywords. Listings scoring 0 are dropped. Results are sorted by score, highest first, with the cheaper item first on a tie. If `description` has no keywords left after the filler words are dropped, scoring is skipped: every listing that passes the size and price filters comes back, cheapest first.
- **When it has nothing:** returns `[]`, an empty list. It never returns `None` and never raises.

### `suggest_outfit`

- **What it does:** Asks the model, through `generate()`, for one or two outfits built around the new item, naming pieces the user already owns.
- **Inputs:**
  - `new_item` (dict): one listing dict, in the shape `search_listings` returns.
  - `wardrobe` (dict or list): either `{"items": [...]}` or the bare list of items. A dict with no `items` key counts as empty. Each item has `name`, `category`, `colors`, `style_tags` and `notes` (str or None).
- **Returns:** a non-empty `str` of plain text with one or two outfits. Each outfit names the new item by its `title` and the wardrobe pieces by their `name`, plus one line on why they work together.
- **When it has nothing:** if the wardrobe has no items, it returns a non-empty `str` of general styling advice for the item (what kinds of pieces and colours to pair it with), starting with `"No wardrobe saved yet — general styling ideas:"`. It never returns `""` and never raises because of an empty wardrobe. If the model can't be reached, `generate()` raises `ModelUnavailable`; this tool doesn't catch it, and the loop deals with it in unit 4.

### `create_fit_card`

- **What it does:** Asks the model, through `generate()`, for a short social-media caption about the find that someone would actually post.
- **Inputs:**
  - `outfit` (str): the outfit text `suggest_outfit` returned.
  - `new_item` (dict): the same listing dict that was passed to `suggest_outfit`.
- **Returns:** a `str` caption, with surrounding whitespace stripped. The prompt asks the model for 2 to 4 sentences under 280 characters, in a casual first-person voice, that mention the item's `title` (or a short form of it), its `price` as `$NN` and its `platform`, each once. It mentions `brand` only when brand is not `None`. It runs at `config.TEMPERATURE` (0.9), so the wording changes between runs.
- **When it has nothing:** if `outfit` is empty or whitespace, it returns `"Can't write a fit card for <title> yet — there's no outfit suggestion to describe."` without calling the model. It never raises because of an empty outfit.

---

## Planning Loop

**Branch rule:** If `search_listings` returns an empty list, `run_agent` puts a message in `session["error"]` naming what the user could change (raise the price ceiling, try a different size or drop the size, use fewer or broader keywords), then returns the session without calling `suggest_outfit` or `create_fit_card`, so `session["fit_card"]` stays `None`. Otherwise it stores the first result in `session["selected_item"]`, then calls `suggest_outfit` and then `create_fit_card`.

**Where it lives:** `agent.py::run_agent`

**How the query is parsed:** with regex, no model call.
- `max_price` comes from `under $30`, `below $30`, `less than 30` or a bare `$30`, as a float. It is `None` if there's no price.
- `size` comes from `size M` or `in size 8`. It is `None` if there's no size.
- The `description` is whatever is left after removing those phrases and the filler words `looking for`, `i want`, `find me` and `a`.

**What moves through the session:** in order:
1. `query`
2. `parsed` (`description`, `size`, `max_price`)
3. `search_results` (the list from `search_listings`)
4. Either `error`, on the empty path, or `selected_item` (`search_results[0]`)
5. `outfit_suggestion` (from `suggest_outfit`, which reads `selected_item` and `wardrobe` from the session)
6. `fit_card` (from `create_fit_card`, which reads `outfit_suggestion` and `selected_item` from the session)

Each tool's inputs are read back out of the session, never passed straight from the previous call.

**Seeing it:** `python app.py ask '...' --session` prints the final session dict. Setting the environment variable `FITFINDR_DEBUG=1` also prints the value the branch checks (`[debug] search_results has N item(s)`) just before the `if`.

---

## Sample Run

**One full query** (happy path). I ran it with the debug flag and `--session`, so the value the branch checks and the final session are printed too. In the session below, `search_results` is cut to its first entry; the real run printed all 10 listings. Everything else is exactly as printed.

```
$ FITFINDR_DEBUG=1 python app.py ask 'vintage graphic tee under $30' --session
[debug] search_results has 10 item(s)

--- final session ---
{
  "query": "vintage graphic tee under $30",
  "parsed": {
    "description": "vintage graphic tee",
    "size": null,
    "max_price": 30.0
  },
  "search_results": [
    {
      "id": "lst_002",
      "title": "Y2K Baby Tee — Butterfly Print",
      ... (cut: 10 listings in the real output; lst_002, lst_033, lst_006, lst_015, lst_012, lst_014, lst_034, lst_017, lst_020, lst_024)
    }
  ],
  "selected_item": {
    "id": "lst_002",
    "title": "Y2K Baby Tee — Butterfly Print",
    "description": "Super cute early 2000s baby tee with butterfly graphic. Fitted crop length. Tag says medium but fits like a small.",
    "category": "tops",
    "style_tags": [
      "y2k",
      "vintage",
      "graphic tee",
      "cottagecore"
    ],
    "size": "S/M",
    "condition": "excellent",
    "price": 18.0,
    "colors": [
      "white",
      "pink",
      "purple"
    ],
    "brand": null,
    "platform": "depop"
  },
  "wardrobe": "<10 items>",
  "outfit_suggestion": "Outfit 1:\nY2K Baby Tee — Butterfly Print\nBaggy straight-leg jeans, dark wash\nChunky white sneakers\nBlack crossbody bag\n\nThis works because the fitted, cropped butterfly tee creates a great balance with the oversized dark denim and chunky streetwear sneakers.\n\nOutfit 2:\nY2K Baby Tee — Butterfly Print\nWide-leg khaki trousers\nVintage black denim jacket\nBlack combat boots\nBrown leather belt\n\nThis works because the earthy khaki trousers and tough black jacket ground the sweet, girly butterfly print with a cool, vintage edge.",
  "fit_card": "Found this dream Y2K Baby Tee for just $18 and I’m obsessed with the butterfly print! Styling it two ways on depop today—dressed down with baggy denim or toughened up with trousers and boots. Which vibe are you stealing?",
  "error": null
}

  Found:    Y2K Baby Tee — Butterfly Print — $18.0 on depop

  Outfit:   Outfit 1:
Y2K Baby Tee — Butterfly Print
Baggy straight-leg jeans, dark wash
Chunky white sneakers
Black crossbody bag

This works because the fitted, cropped butterfly tee creates a great balance with the oversized dark denim and chunky streetwear sneakers.

Outfit 2:
Y2K Baby Tee — Butterfly Print
Wide-leg khaki trousers
Vintage black denim jacket
Black combat boots
Brown leather belt

This works because the earthy khaki trousers and tough black jacket ground the sweet, girly butterfly print with a cool, vintage edge.

  Fit card: Found this dream Y2K Baby Tee for just $18 and I’m obsessed with the butterfly print! Styling it two ways on depop today—dressed down with baggy denim or toughened up with trousers and boots. Which vibe are you stealing?

2 model calls this session, 697 prompt + 167 output tokens
```

`selected_item` is `lst_002`, which is `search_results[0]`. That is the item `suggest_outfit` and `create_fit_card` both received, read back from the session.

**The empty-search path** (the branch)

```
$ FITFINDR_DEBUG=1 python app.py ask 'designer ballgown size XXS under $5' --session
[debug] search_results has 0 item(s)

--- final session ---
{
  "query": "designer ballgown size XXS under $5",
  "parsed": {
    "description": "designer ballgown",
    "size": "XXS",
    "max_price": 5.0
  },
  "search_results": [],
  "selected_item": null,
  "wardrobe": "<10 items>",
  "outfit_suggestion": null,
  "fit_card": null,
  "error": "No listings matched 'designer ballgown' in size XXS under $5. You could: raise the price ceiling (listings run $12–$75; try 'under $40' instead of 'under $5'); try a different size or leave the size out (sizes in stock include S, M, L, XL, US 7–9 and W27–W32); use fewer or broader keywords, like 'dress' or 'jacket' instead of a specific style."
}

  No listings matched 'designer ballgown' in size XXS under $5. You could: raise the price ceiling (listings run $12–$75; try 'under $40' instead of 'under $5'); try a different size or leave the size out (sizes in stock include S, M, L, XL, US 7–9 and W27–W32); use fewer or broader keywords, like 'dress' or 'jacket' instead of a specific style.

0 model calls this session
```

**The three tools, tested one at a time**

```
$ python -c "from tools import search_listings; print(search_listings('graphic tee', max_price=30))"
[{'id': 'lst_002', 'title': 'Y2K Baby Tee — Butterfly Print', 'description': 'Super cute early 2000s baby tee with butterfly graphic. Fitted crop length. Tag says medium but fits like a small.', 'category': 'tops', 'style_tags': ['y2k', 'vintage', 'graphic tee', 'cottagecore'], 'size': 'S/M', 'condition': 'excellent', 'price': 18.0, 'colors': ['white', 'pink', 'purple'], 'brand': None, 'platform': 'depop'}, {'id': 'lst_033', 'title': 'Vintage Band Tee — Faded Grey', 'description': 'Faded grey band-style tee with distressed graphic. Crew neck. Fits boxy. Well-loved but no holes or major damage.', 'category': 'tops', 'style_tags': ['vintage', 'grunge', 'band tee', 'graphic tee', 'streetwear'], 'size': 'L', 'condition': 'fair', 'price': 19.0, 'colors': ['grey', 'charcoal'], 'brand': None, 'platform': 'depop'}, {'id': 'lst_006', 'title': 'Graphic Tee — 2003 Tour Bootleg Style', 'description': 'Vintage-style bootleg tee with faded graphic. Slightly boxy fit. 100% cotton, soft and worn-in.', 'category': 'tops', 'style_tags': ['graphic tee', 'vintage', 'grunge', 'streetwear', 'band tee'], 'size': 'L', 'condition': 'good', 'price': 24.0, 'colors': ['black'], 'brand': None, 'platform': 'depop'}, {'id': 'lst_017', 'title': 'Mesh Long-Sleeve Top — Black', 'description': 'Sheer black mesh long-sleeve. Great for layering under a graphic tee or over a bralette. Stretchy material, fits true to size.', 'category': 'tops', 'style_tags': ['y2k', 'grunge', 'goth', 'layering'], 'size': 'S/M', 'condition': 'excellent', 'price': 15.0, 'colors': ['black'], 'brand': None, 'platform': 'depop'}, {'id': 'lst_015', 'title': 'Vintage Graphic Hoodie — Faded Black', 'description': 'Faded black pullover hoodie with barely-visible vintage graphic on the chest. Cozy interior. Some pilling but adds to the worn-in look.', 'category': 'tops', 'style_tags': ['vintage', 'grunge', 'graphic', 'streetwear'], 'size': 'L', 'condition': 'fair', 'price': 26.0, 'colors': ['black', 'charcoal'], 'brand': None, 'platform': 'depop'}, {'id': 'lst_012', 'title': 'Oversized Crewneck Sweatshirt — Vintage Navy', 'description': 'Perfectly faded navy crewneck. Genuinely vintage — not manufactured distressed. Ribbed cuffs and hem. No graphics, clean.', 'category': 'tops', 'style_tags': ['vintage', 'basics', 'oversized', 'classic'], 'size': 'XL (fits oversized)', 'condition': 'good', 'price': 20.0, 'colors': ['navy'], 'brand': None, 'platform': 'thredUp'}, {'id': 'lst_011', 'title': 'Low-Rise Cargo Pants — Khaki', 'description': 'Y2K era low-rise cargo pants. Lots of pockets. Khaki color, slightly distressed at the hems. Great for layering with a long tee.', 'category': 'bottoms', 'style_tags': ['y2k', 'cargo', '2000s', 'streetwear'], 'size': 'W29', 'condition': 'fair', 'price': 27.0, 'colors': ['khaki', 'tan'], 'brand': None, 'platform': 'poshmark'}]
```

```
$ python -c "from tools import suggest_outfit; from utils.data_loader import get_example_wardrobe, load_listings; print(suggest_outfit(load_listings()[5], get_example_wardrobe()))"
Outfit 1:
Wear the Graphic Tee — 2003 Tour Bootleg Style tucked into your Baggy straight-leg jeans, dark wash. Layer the Vintage black denim jacket over top. Finish with your Black combat boots and the Black crossbody bag.
Why it works: The boxy tee paired with baggy denim and combat boots hits that effortless, full-grunge streetwear aesthetic.

Outfit 2:
Pair the Graphic Tee — 2003 Tour Bootleg Style with your Wide-leg khaki trousers, cinched at the waist using the Brown leather belt. Throw on the Oversized grey crewneck sweatshirt draped loosely over your shoulders, and complete the look with your Chunky white sneakers.
Why it works: Tucking the graphic tee into khaki trousers balances the oversized silhouette, mixing edgy streetwear with relaxed earth tones.
```

Empty wardrobe:

```
$ python -c "from tools import suggest_outfit; from utils.data_loader import get_empty_wardrobe, load_listings; print(suggest_outfit(load_listings()[5], get_empty_wardrobe()))"
No wardrobe saved yet — general styling ideas:
Hey there! That 2003 tour bootleg tee is an absolute score—$24 for that broken-in, 100% cotton feel is totally worth it.

Here is your first look: Pair the boxy black tee with some baggy, light-wash denim jeans and scuffed-up white canvas sneakers. Add a silver chain necklace or a beat-up canvas tote. This gives off an effortless, 90s skater-grunge vibe that is super easy to wear everyday.

For your second option: Tuck the tee into a plaid midi skirt or a black pleather mini skirt, and layer it with chunky black combat boots. Throw on an oversized thrifted leather blazer over top. This creates an edgy, downtown-cool streetwear look with a fun mix of hard and soft textures. Have fun styling it!
```

`create_fit_card`, empty-outfit guard (no model call):

```
$ python -c "from tools import create_fit_card; from utils.data_loader import load_listings; print(repr(create_fit_card('', load_listings()[5]))); print(repr(create_fit_card('   ', load_listings()[5])))"
"Can't write a fit card for Graphic Tee — 2003 Tour Bootleg Style yet — there's no outfit suggestion to describe."
"Can't write a fit card for Graphic Tee — 2003 Tour Bootleg Style yet — there's no outfit suggestion to describe."
```

The real model output from `create_fit_card` is the `fit_card` line in the full query above (222 characters, with the price and the platform).

**Three runs on the same input, to check the wording varies: not completed.** I started a test that ran `create_fit_card` 3 times on `lst_006`, first with `CACHE_ENABLED` on and then with `AI201_CACHE=0`. The rate limiter was still pacing calls after 5 minutes, and I stopped it because of my time limit, so I have no output to report. From reading the code: with `CACHE_ENABLED` on (the default), `generate()` returns the saved answer for an identical prompt, so three runs give word-for-word the same caption. With the cache off, each run makes a real call at `TEMPERATURE = 0.9`, so the wording should differ. That expectation is untested; criterion 4 is where I'll measure it in unit 4.

---

## How I Used AI

**Moment 1: `suggest_outfit` invented shoes**

- *What I asked for:* I had Claude write `suggest_outfit` from my Tool Inventory spec. The prompt tells the model to name the user's pieces exactly as written and to "only use pieces from that list". I then tested it from the terminal with the wardrobe passed as a bare list of just 3 items.
- *What came back:* Real outfits that used my jeans, khakis and tank top, but also "black chunky loafers or scuffed sneakers" and "retro trainers". None of those were in the 3-item list, so the model ignored the "only use pieces from that list" instruction.
- *What I changed:* Nothing in the code yet. I noticed it in the test output and flagged it for unit 4, where criterion 3 checks the outfit text. A likely fix is to tell the model to leave out shoes when the wardrobe has none, or to check the outfit text against the wardrobe names afterwards.

**Moment 2: "dress" became "dres"**

- *What I asked for:* My spec for `search_listings` said a trailing plural `s` is ignored, so `tees` matches `tee`. I had Claude build the search from that spec and test it with queries including `'silk slip dress midi length'`.
- *What came back:* Followed literally, that rule turns `dress` into `dres`. It still matched (both sides are stemmed the same way), but only by accident, and it would also mangle words like `glass` or `class`.
- *What I changed:* I changed the spec and the code so words ending in `ss` (and words of 3 letters or fewer) keep their `s`. The README now says `tees` matches `tee` but `dress` stays `dress`.

**Unit 4: who did what**

In this unit Claude Code (Claude Opus 5.5, in VS Code) did the implementation and all the test runs: the MCP registration and rewire, the failure handler and the `trace.step()` calls, the scenarios, the scorer (`results/score_run.py`), both eval runs, and the first draft of every unit 4 README section. I set the ground rules up front: honesty over looking good, no edits to criteria.md, only the three allowed kinds of code change, and stop and ask before anything graded. I made these decisions myself when it asked:

- For criteria 3 and 5, each Try column is one named query, and a query passes only if all 5 of its runs pass (the stricter of the two options it offered).
- The scorer is committed as evaluation tooling.
- The first "before" run was discarded rather than reported. It ran from about 11:01 to 13:59 with 34 of its roughly 59 model-calling tries hitting 503s, and it used the old error messages. The "before" eval was re-run from scratch once `test.py` passed again.
- The 503 handler message was split into "key rejected" and "service busy".
- The one improvement is the retry branch in `run_agent`, not a retry inside `generate.py`.

Two things Claude Code caught that I would want a reviewer to know about:

- Its own first version of the retry branch was missing a `break`, so a rejected key would still have been retried once. A stubbed test of five cases found that before the after-run.
- It checked that the denim-jacket failures were not caused by the prompt, by re-calling `suggest_outfit` on that item 3 times after the run (all succeeded).

*To fill in before submitting:* what I personally re-checked, for example the verdict counts against `results/score_before.txt` and `results/score_after.txt`, and whether the diagnoses make sense to me.

<!-- ═══════════════════════ UNIT 4 — THE TEST ═══════════════════════

     Don't fill these in during unit 3.
     ═══════════════════════════════════════════════════════════════════ -->

---

## Run Log — Before

<!-- Five criteria, five tries each, in this exact format.

     Five, because your criteria are written out of five. Mark each try PASS
     or FAIL, count the passes, and read that count against your target — a
     row targeting 4 of 5 with three PASS cells is MISSED (3/5).

     `python run_eval.py --label before` runs everything and writes the table
     into results/. Paste it here and fill in the verdicts. -->

Run with `python run_eval.py --label before` on commit `c9ba1b3`, 13 Oct 2026, 14:17–14:25, cache off, temperature 0.9. 70 tries, 123 model calls, 0 crashes. Raw files: [results/run_2026-10-13_1425_before.md](results/run_2026-10-13_1425_before.md) (the report), [results/run_before_console.txt](results/run_before_console.txt) (console) and [results/score_before.txt](results/score_before.txt) (scorer output).

| Criterion | Target | Try 1 | Try 2 | Try 3 | Try 4 | Try 5 | Verdict |
|---|---|---|---|---|---|---|---|
| 1. Matching query completes all three tools | ≥4 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 2. Impossible query stops before `suggest_outfit` | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 3. `suggest_outfit` gets the selected item (id 5/5) and uses its title (≥2 words, 4/5) | id 5 of 5; words ≥4 of 5 | PASS | PASS | PASS | PASS | FAIL | MISSED (id 4/5; words 4/5) |
| 4. Fit card on `lst_006` is postable and varies | ≥4 of 5 pass; ≥4 distinct | FAIL | PASS | PASS | FAIL | PASS | MISSED (3/5; 3 distinct) |
| 5. Search respects price ceiling and size | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |

**How the columns map for criteria 3 and 5.** Both criteria are written over 5 *named queries*, so for those two rows **Try k = named query k** from criteria.md. `run_eval.py` ran each query 5 times, and a query is marked PASS only if **all 5** of its runs passed. That is the strictest reading. All 25 runs per criterion are listed in [results/score_before.txt](results/score_before.txt). For criterion 3, the cell is PASS only if both parts passed for that query.

**How the cells were marked.** [results/score_run.py](results/score_run.py) marks every cell. It reads only the saved run report, and applies each criterion as it is written in criteria.md:

- C1: a fit card exists, there's no `error`, and the card isn't the "Can't write a fit card…" fallback.
- C2: `error` names a specific change, `outfit_suggestion` and `fit_card` are `None`, and the trace has no `suggest_outfit` step.
- C3: the `new_item.id` that `suggest_outfit` logs from inside the tool equals the `selected_item` id in the search step, and the outfit text contains ≥2 whole words from the part of the title before the "—".
- C4: the card is ≤280 chars, has ≥2 title words, `$24` and `depop`, and the 5 cards are counted for distinct strings.
- C5: ≥1 result, and every listing has `price <= max_price` and a matching size token.

For C5 the report logs only the result count and the first 3 titles, so the scorer re-calls the MCP tool with the exact inputs from the trace and checks that the count and titles match the log before checking each listing. Run it with `python results/score_run.py results/run_<stamp>_before.md`.

**Real output, one try per criterion.** All of it is from `results/run_2026-10-13_1425_before.md`, written by `run_eval.py::write_report`. The loop is `agent.py::run_agent`, the `[n]` trace lines come from `trace.py::step`, and the tools are in `tools.py`, with search reached through `mcp_server.py::search_listings`.

Criterion 1, try 1 (`vintage graphic tee under $30`): `tools.py::create_fit_card` produced the fit card.

```
- stopped early: no
- selected_item: Y2K Baby Tee — Butterfly Print ($18.0, depop)
- search_results: 10

Fit card:
Scored this butterfly Y2K Baby Tee for just $18 and I’m obsessed! It’s giving skater-girl casual with baggy denim, then grunge-chic with khaki trousers. Heading to depop to list more finds soon!

Trace:
[1] parse_query
      in:  vintage graphic tee under $30
      out: description='vintage graphic tee', size=None, max_price=30.0
[2] search_listings (via MCP)
      in:  description='vintage graphic tee', size=None, max_price=30.0
      out: 10 items: Y2K Baby Tee — Butterfly Print, Vintage Band Tee — Faded Grey, Graphic Tee — 2003 Tour Bootleg Style … +7 more
      →    branch: not empty, selected_item = lst_002
[3] suggest_outfit
      in:  new_item.id=lst_002 (Y2K Baby Tee — Butterfly Print), wardrobe=10 items
      out: Outfit 1: - Y2K Baby Tee — Butterfly Print - Baggy straight-leg jeans, dark wash - Chunky white sneakers - Bla…
[4] create_fit_card
      in:  outfit (718 chars), new_item.id=lst_002
      out: Scored this butterfly Y2K Baby Tee for just $18 and I’m obsessed! It’s giving skater-girl casual with baggy de…
```

Criterion 2, try 1 (`designer ballgown size XXS under $5`): `agent.py::_no_results_message` wrote the message, and `agent.py::run_agent` stopped at the branch.

```
- stopped early: yes — No listings matched 'designer ballgown' in size XXS under $5. You could: raise the price ceiling (listings run $12–$75; try 'under $40' instead of 'under $5'); try a different size or leave the size out (sizes in stock include S, M, L, XL, US 7–9 and W27–W32); use fewer or broader keywords, like 'dress' or 'jacket' instead of a specific style.
- selected_item: (none)
- search_results: 0

Trace:
[1] parse_query
      in:  designer ballgown size XXS under $5
      out: description='designer ballgown', size='XXS', max_price=5.0
[2] search_listings (via MCP)
      in:  description='designer ballgown', size='XXS', max_price=5.0
      out: [] (empty)
      →    branch: empty, stopping before suggest_outfit
```

Criterion 3, query 1, try 1: the id in step [3] is logged by `tools.py::_trace_outfit` from `suggest_outfit`'s own `new_item`, and step [2]'s `selected_item` comes from the session.

```
[2] search_listings (via MCP)
      in:  description='vintage graphic tee', size=None, max_price=30.0
      out: 10 items: Y2K Baby Tee — Butterfly Print, Vintage Band Tee — Faded Grey, Graphic Tee — 2003 Tour Bootleg Style … +7 more
      →    branch: not empty, selected_item = lst_002
[3] suggest_outfit
      in:  new_item.id=lst_002 (Y2K Baby Tee — Butterfly Print), wardrobe=10 items
      out: Outfit 1: - Y2K Baby Tee — Butterfly Print - Baggy straight-leg jeans, dark wash - Vintage black denim jacket …

scorer: id PASS words PASS lst_002->lst_002 words=['y2k', 'baby', 'tee']
```

Criterion 3, query 5 (`denim jacket under $50`), try 1: this is the failing cell. All 5 runs of this query looked like this.

```
- stopped early: yes — Found Denim Jacket — Light Wash, Cropped ($42 on poshmark), but couldn't write the outfit and the fit card: the model is busy or couldn't be reached right now. Try the same query again in a minute or two.
- selected_item: Denim Jacket — Light Wash, Cropped ($42.0, poshmark)
- search_results: 7

Trace:
[1] parse_query
      in:  denim jacket under $50
      out: description='denim jacket', size=None, max_price=50.0
[2] search_listings (via MCP)
      in:  description='denim jacket', size=None, max_price=50.0
      out: 7 items: Denim Jacket — Light Wash, Cropped, High-Waisted Denim Shorts — Cutoff, Denim Vest — Medium Wash, Studded … +4 more
      →    branch: not empty, selected_item = lst_007
[3] model unavailable
      out: service busy
      →    stopping; search result kept in session
```

Criterion 4: the three captions `tools.py::create_fit_card` actually produced for `lst_006` (tries 2, 3 and 5). Tries 1 and 4 stopped like the denim-jacket run above (`[3] model unavailable / out: service busy`), so they have no caption.

```
try 2 (212 chars): Scored this vintage 2003 tour Graphic Tee on depop for just $24! I'm styling it two ways: tucked into baggy dark denim for an effortless streetwear vibe, or loose over khakis with chunky sneaks for edgy contrast.
try 3 (191 chars): Scored this sick 2003 tour bootleg Graphic Tee for just $24 on depop! Giving major 90s grunge with baggy denim or cool high-low contrast with tailored khakis. Grab it before I change my mind!
try 5 (184 chars): Just scored this 2003 tour bootleg Graphic Tee on depop for $24! Obsessed with the heavy grunge vibe, whether I'm stomping around in combat boots or keeping it chill in khaki trousers.
```

Criterion 5, query 2 (`top size M under $25`), try 1: `mcp_server.py::search_listings` returned the results, which wrap `tools.py::search_listings`. Scorer line: `n=6 bad=[] matches_log=True` (6 listings, all ≤ $25, sizes `S/M` or `M`).

```
[1] parse_query
      in:  top size M under $25
      out: description='top', size='M', max_price=25.0
[2] search_listings (via MCP)
      in:  description='top', size='M', max_price=25.0
      out: 6 items: Mesh Long-Sleeve Top — Black, Crochet Halter Top — Cream, Henley Long Sleeve — Washed Burgundy … +3 more
      →    branch: not empty, selected_item = lst_017
```

---

## Verdicts and Diagnoses

<!-- MET or MISSED per criterion against LAST UNIT's target, plus a sentence on
     how you decided.

     Then, for every miss: which of the four places it happened — a tool, the
     loop's branch, the session, or the model's output — AND the mechanism.

     Not a diagnosis:  "The fit card was bad."
     A diagnosis:      "The fit card criterion missed on 2 of 5 items. Both had
                        an empty brand field. My prompt puts the brand in the
                        first sentence, so the card opened with a blank and read
                        like a fragment. The tool worked; the prompt assumed a
                        field that isn't always there."

     Look for a pattern. Three misses on the same tool is one problem, not
     three. -->

| # | Criterion | Target | Verdict | How I decided |
|---|---|---|---|---|
| 1 | Matching query completes all three tools | ≥4 of 5 | **MET (5/5)** | All 5 tries returned a real model caption (150–204 chars), with no `error` and not the fallback text. |
| 2 | Impossible query stops before `suggest_outfit` | 5 of 5 | **MET (5/5)** | All 5 tries had 2 trace steps (parse, search), `outfit_suggestion` and `fit_card` were `None`, and the message names three concrete changes. |
| 3 | `suggest_outfit` receives the selected item and uses its title | id 5 of 5; title words ≥4 of 5 | **MISSED** (id 4/5; words 4/5) | Queries 1–4 passed both parts in all 5 runs. Query 5 (`denim jacket under $50`) failed all 5 runs because `suggest_outfit` never ran, so no id was logged. The id part needs 5/5, so the criterion is missed even though the words part (4/5) meets its own target. |
| 4 | Fit card on `lst_006` is postable and varies | ≥4 of 5 pass; ≥4 distinct | **MISSED** (3/5; 3 distinct) | Tries 2, 3 and 5 passed every check and are 3 different strings. Tries 1 and 4 produced no caption at all. 3 < 4 on both parts. |
| 5 | Search respects price ceiling and size | 5 of 5 | **MET (5/5)** | All 5 named queries returned ≥1 listing in all 5 runs, with no listing over the ceiling or with a non-matching size. |

**Diagnoses**

There are two misses, and they are **one problem**. Every failed try in the run (7 of the 65 tries that call the model, which is 70 tries minus the 5 impossible-query tries that never reach the model) failed at the same place for the same reason.

- **Where:** the model's output. More precisely, the model call inside the **`suggest_outfit` tool, step [3]** of the loop: no output came back. The search, the branch and the session all worked. In every failed try, step [2] found the right item (`lst_007` for query 5, `lst_006` for criterion 4) and put it in `selected_item`.
- **Mechanism:** Gemini answered `503 UNAVAILABLE` ("This model is currently experiencing high demand"). `generate.py::generate` only retries an error if it looks like a rate limit (`"429"`, "resource exhausted", or "rate" + "limit"). A 503 matches none of those, so it is raised as `ModelUnavailable` on the **first attempt, with no retry**. My handler in `agent.py::run_agent` then did what it was built to do: it kept the search result, set `session["error"]` to the "model is busy" message and stopped. So `suggest_outfit` logged no id, there was no outfit text, and `create_fit_card` never ran.
- **Evidence:** all 7 failed tries end with the same two trace lines, `[3] model unavailable` / `out: service busy`, right after `[2] search_listings (via MCP)` (see the query 5 trace in the Run Log above). The failures were bunched together: all 5 runs of C3 query 5 in a row, then C4 tries 1 and 4. To check that this wasn't something about the denim-jacket prompt, I called `suggest_outfit` on `lst_007` with the same wardrobe 3 more times at 14:27, two minutes after the run. It succeeded 3 of 3 times ([results/diag_lst_007_suggest_outfit.txt](results/diag_lst_007_suggest_outfit.txt)). That diagnostic replaces no tries; the table above is exactly what the run produced. Earlier the same day, before this run, the service returned 503s for well over an hour (test.py failed with 503 at 14:06, and [results/trace_real_503_outage.txt](results/trace_real_503_outage.txt) is one of those runs).
- **How much the outage distorted the result:** a lot, for C3 and C4. Every try where the model did answer passed:
  - C3: 20 of 20 such runs had a matching id and ≥2 title words.
  - C4: 3 of 3 captions passed every check, and all 3 are distinct.

  So the misses say nothing bad about my prompts, my tools or my loop. They say the agent has no tolerance for a transient service error. That is still a real failure a user would see ("couldn't write the outfit and the fit card"), and it counts against the target as written.
- **No prompt, tool or loop misses** showed up in this run. I didn't find a mechanism other than the 503.

**Arguing the opposite verdict**

- **C1, MET → MISSED?** It's one query, run 5 times, during a period when the service was failing 7 tries out of 65. If the 503 burst had landed on these 5 tries instead of C3 query 5, C1 would have read 0/5. The pass partly reflects luck about when the burst hit. *Doesn't change the call:* the target is about these 5 tries, and they passed. But it shows that the same weakness threatens C1 too.
- **C2, MET → MISSED?** The path is deterministic, so 5 tries are really 1 test run 5 times, on one query. Also, the "use fewer or broader keywords" tip is added on every empty search, so part of the message is boilerplate. *Doesn't change the call:* the criterion asks for a message naming a specific change, and "raise the price ceiling… try 'under $40'" is specific. **This target was too easy, and it's the one I'd tighten:** 5 different impossible queries, each failing on a different filter (price only, size only, keywords only), with the message required to name the filter that actually emptied the result.
- **C3, MISSED → MET?** The criterion exists to test the session handoff from search to `suggest_outfit`, and that handoff was correct in 20 of 20 runs where `suggest_outfit` ran. Query 5 failed for a reason outside what the criterion measures. *Doesn't change the call:* the criterion says "in 5 of 5 queries". For query 5, `suggest_outfit` never received anything, so the match was never shown. Calling it MET would mean scoring the tries I wish had happened.
- **C4, MISSED → MET?** Every caption that exists is perfect: under 280 chars, title words, `$24`, `depop`, and 3 different strings. *Doesn't change the call:* the criterion is about 5 runs, and in 2 of them the user got no fit card. That's 3/5 against a 4/5 target.
- **C5, MET → MISSED?** It's deterministic like C2, and 3 of the 5 queries return exactly one listing, which is a thin test of the filter. Also, criteria.md's note on query 2 says "(only `S/M` listings qualify)", but plain `M` listings (`lst_020`, `lst_024`, `lst_030`) are also returned, and they match correctly under the token rule. The note is wrong about the data; the rule itself is fine. *Doesn't change the call:* the rule as written passed on every listing. I'm leaving the note in criteria.md unedited, because changing it is not my call to make silently.

None of the five criteria turned out to be unmeasurable, so I'm making **no revisions** to criteria.md.



---

## Loop Trace

<!-- One full run, printed step by step, with the MCP call visible in it.

     `python app.py ask '...' --trace` once you've added the trace.step()
     calls in Milestone 2.

     Worth pasting BOTH the happy path and the empty-search path. The empty
     one should be visibly shorter, because it stops. If your two traces are
     the same length, your branch isn't working — and this is the fastest way
     anyone will ever find that out. -->

Both runs used `python app.py ask '...' --trace`, saved as [results/trace_happy_path.txt](results/trace_happy_path.txt) and [results/trace_empty_search.txt](results/trace_empty_search.txt) and captured on commit `deb188b`. Step [2] is the MCP call. Steps [1], [2] and the `create_fit_card` step are `trace.step()` calls in `agent.py::run_agent`. Step [3] is recorded inside `tools.py::suggest_outfit` (see "Why suggest_outfit's trace line lives in tools.py" below). Since then, the improvement added one more possible step, `model unavailable / branch: busy, waiting 20s and retrying once`, which only appears when the model returns a 503.

**Happy path** (4 steps)

```
$ python app.py ask '90s track jacket in size M' --trace
[1] parse_query
      in:  90s track jacket in size M
      out: description='90s track jacket', size='M', max_price=None
[2] search_listings (via MCP)
      in:  description='90s track jacket', size='M', max_price=None
      out: 5 items: 90s Track Jacket — Navy/White Stripe, 90s Leather Bomber — Black, Bucket Hat — Reversible, Brown Plaid … +2 more
      →    branch: not empty, selected_item = lst_004
[3] suggest_outfit
      in:  new_item.id=lst_004 (90s Track Jacket — Navy/White Stripe), wardrobe=10 items
      out: Outfit One White ribbed tank top Baggy straight-leg jeans, dark wash Brown leather belt Chunky white sneakers …
[4] create_fit_card
      in:  outfit (585 chars), new_item.id=lst_004
      out: Scored this vintage Champion 90s Track Jacket for just $45 on poshmark! I'm styling it two ways: balanced with…

  Found:    90s Track Jacket — Navy/White Stripe — $45.0 on poshmark

  Outfit:   Outfit One
White ribbed tank top
Baggy straight-leg jeans, dark wash
Brown leather belt
Chunky white sneakers
90s Track Jacket — Navy/White Stripe

This look leans hard into effortless 90s streetwear, where the fitted tank balances the baggy denim while the sporty jacket ties the whole casual vibe together.

Outfit Two
Wide-leg khaki trousers
White ribbed tank top
Chunky white sneakers
Black crossbody bag
90s Track Jacket — Navy/White Stripe

Throwing the track jacket over these earthy trousers creates an easy high-low mix of athletic and minimal styles that feels totally fresh.

  Fit card: Scored this vintage Champion 90s Track Jacket for just $45 on poshmark! I'm styling it two ways: balanced with baggy denim and a tank, or dressed up with khaki trousers for the ultimate effortless streetwear vibe.

2 model calls this session, 713 prompt + 179 output tokens
```

**Empty search** (2 steps: it stops at the branch, before any model call)

```
$ python app.py ask 'designer ballgown size XXS under $5' --trace
[1] parse_query
      in:  designer ballgown size XXS under $5
      out: description='designer ballgown', size='XXS', max_price=5.0
[2] search_listings (via MCP)
      in:  description='designer ballgown', size='XXS', max_price=5.0
      out: [] (empty)
      →    branch: empty, stopping before suggest_outfit

  No listings matched 'designer ballgown' in size XXS under $5. You could: raise the price ceiling (listings run $12–$75; try 'under $40' instead of 'under $5'); try a different size or leave the size out (sizes in stock include S, M, L, XL, US 7–9 and W27–W32); use fewer or broader keywords, like 'dress' or 'jacket' instead of a specific style.

0 model calls this session
```

**On the MCP move:** `search_listings` is registered in `mcp_server.py` with `@mcp.tool()`. Its inputs are `description: str`, `size: str | None = None` and `max_price: float | None = None`, which match the Tool Inventory, so neither side needed fixing. Its description says what it searches, the units (US dollars, inclusive), the size rule, the fields it returns, and that it returns `[]` when nothing matches. `python mcp_client.py` lists it with `description: string`, `size: string (optional)` and `max_price: number (optional)`. In `agent.py::run_agent`, the direct `search_listings(...)` call became `call_tool("search_listings", {...})`. `suggest_outfit` and `create_fit_card` are still called directly.

**Did anything behave differently?** Not in what comes back. I compared the direct call and the MCP call on 5 queries: `vintage graphic tee` ≤ $30, `track jacket 90s` size M, the impossible `designer ballgown` XXS ≤ $5, `sneakers` size 8 ≤ $50, and an empty description. All 5 returned equal lists, including the empty `[]`, and the field types survived the round trip (`price` stayed a `float`, `brand` stayed `None`, `style_tags` stayed a list). The one difference is speed: about **1 ms direct vs about 2.3 s over MCP** (1.2 ms vs 2344 ms, measured once), because `mcp_client.call_tool` starts a fresh server process for every call.

**Why suggest_outfit's trace line lives in tools.py:** criterion 3 says the id must be logged *inside* `suggest_outfit`, from its own `new_item` parameter, and never read from the session, so that the check can actually fail. A trace line in `run_agent` would read `session["selected_item"]`, the same value it's compared against, so it could never disagree. `tools.py::_trace_outfit` therefore logs `new_item['id']` from inside the tool. That is the `[3] suggest_outfit … new_item.id=…` line.

### Failure modes, triggered on purpose

**1. Empty search.** I ran a query the data can't contain, before any handler was added. The branch already handled it: no crash and no model call, and it named what to change.

```
$ python app.py ask 'gold sequin tuxedo size XXS under $3'

  No listings matched 'gold sequin tuxedo' in size XXS under $3. You could: raise the price ceiling (listings run $12–$75; try 'under $40' instead of 'under $3'); try a different size or leave the size out (sizes in stock include S, M, L, XL, US 7–9 and W27–W32); use fewer or broader keywords, like 'dress' or 'jacket' instead of a specific style.

0 model calls this session
```

**2. Empty wardrobe.** This didn't crash or return `""`. `suggest_outfit` returns general styling advice under the header `No wardrobe saved yet — general styling ideas:`, and the fit card still gets written. No handler was needed. The output below is the eval's `empty wardrobe` diagnostic scenario, try 1, from `results/run_2026-10-13_1425_before.md`. All 5 tries completed with that header.

```
[3] suggest_outfit
      in:  new_item.id=lst_007 (Denim Jacket — Light Wash, Cropped), wardrobe=0 items
      out: No wardrobe saved yet — general styling ideas: Hey there! That Wrangler jacket is such a solid find. Structure…
[4] create_fit_card
      in:  outfit (737 chars), new_item.id=lst_007
      out: Scored this sweet Wrangler Denim Jacket on Poshmark for just $42! Obsessed with the light wash and structured …

Outfit suggestion:
No wardrobe saved yet — general styling ideas:
Hey there! That Wrangler jacket is such a solid find. Structured shoulders on a light wash denim make it super versatile.

For an easy everyday look, throw it over an oversized graphic tee in black or grey, paired with black biker shorts or straight-leg black jeans. Finish it off with chunky white sneakers and a canvas tote. The vibe is effortless, sporty, and very downtown streetwear.

For a cuter weekend outfit, layer it directly over a floral midi slip dress in olive green or pastel yellow. Add a pair of well-worn canvas high-top sneakers and a simple canvas shoulder bag. The vibe here is a fun, vintage-inspired mix of sweet and rugged. Both are super easy to build from basics!
```

(My first three manual tries of this failure mode, `'oversized crewneck sweatshirt under $25' --empty-wardrobe`, were blocked by real Gemini 503s. A fourth try, with the handler in place, completed with general styling advice.)

**3. Model unavailable.** Before any handler, a one-character change to the key made `run_agent` raise. `app.py`'s catch-all printed the line below and exited with code 1. The search result was lost, and `run_eval.py` would have logged the try as CRASHED:

```
$ python app.py ask 'cropped cardigan size S under $35'      # bad key, before the handler

ModelUnavailable: The model rejected your API key. Check GEMINI_API_KEY in your .env file, or create a fresh key at aistudio.google.com.

1 model calls this session
```

Real 503s failed the same way. One of them threw away an outfit that had already been generated, because `create_fit_card` failed after `suggest_outfit` had succeeded. So I added a `ModelUnavailable` handler to `run_agent`. My first version pasted the raw 503 error dict and told everyone to "try again in a minute", including people whose key was rejected and for whom retrying never helps. This real outage run was handled by that first version ([results/trace_real_503_outage.txt](results/trace_real_503_outage.txt)):

```
[3] model unavailable
      out: Couldn't reach the model: 503 UNAVAILABLE. {'error': {'code': 503, 'message': 'This model is currently experie…
      →    stopping; search result kept in session

  Found 90s Track Jacket — Navy/White Stripe ($45 on poshmark), but couldn't write the outfit and the fit card because the model is unavailable: Couldn't reach the model: 503 UNAVAILABLE. {'error': {'code': 503, 'message': 'This model is currently experiencing high demand. Spikes in demand are usually temporary. Please try again later.', 'status': 'UNAVAILABLE'}} Your search still worked. Try the same query again in a minute; if the message says your API key was rejected, fix GEMINI_API_KEY in .env first.
```

The final handler gives two separate messages and no raw JSON.

*Key rejected.* I backed up `.env`, changed one character of the key and ran a new query. Afterwards I restored the file, confirmed with `cmp` that it was byte-identical to the backup, and confirmed `.env` is still git-ignored ([results/failure_key_rejected.txt](results/failure_key_rejected.txt)):

```
$ python app.py ask 'leather bomber jacket under $80' --trace
...
[3] model unavailable
      out: key rejected
      →    stopping; search result kept in session

  Found 90s Leather Bomber — Black ($75 on depop), but couldn't write the outfit and the fit card: the model rejected your API key. Check GEMINI_API_KEY in your .env file (or create a new key at aistudio.google.com). Retrying won't help until the key is fixed.

1 model calls this session
```

*Service busy.* This one is simulated. I added a temporary line at the top of `suggest_outfit` that raised `ModelUnavailable` with the exact 503 text Gemini had returned, ran the query, then removed the line (`git diff tools.py` was empty afterwards). See [results/failure_service_busy_simulated.txt](results/failure_service_busy_simulated.txt):

```
$ python app.py ask 'cropped cardigan size S under $35' --trace
...
[3] model unavailable
      out: service busy
      →    stopping; search result kept in session

  Found Knit Cardigan — Chunky Brown ($35 on depop), but couldn't write the outfit and the fit card: the model is busy or couldn't be reached right now. Try the same query again in a minute or two.

0 model calls this session
```

Both of these were captured before the improvement. Since the improvement, a busy service gets one wait-and-retry before this message appears. A rejected key still stops at once.



---

## The Improvement

<!-- What you changed, why your diagnosis pointed at it, and the after-run in
     the same table format. One change, measured properly.

     `python run_eval.py --label after` -->

**What I changed:** I added a second branch to `agent.py::run_agent` (commit `f1ae509`). When a model call raises `ModelUnavailable` and the error is a busy service (a 503, "unavailable", a timeout), the loop records `model unavailable / branch: busy, waiting 20s and retrying once` in the trace, waits 20 seconds and tries again **once**. The retry only redoes the step that hadn't finished, so if the outfit is already in the session, only the fit card is retried. A rejected key still stops immediately, because waiting never fixes a bad key. If the second attempt is also busy, the run stops with the same "model is busy" message as before. Nothing else changed: same prompts, same tools, same scenarios, same pacing.

**Which failure it was meant to fix:** the only one the diagnosis found. In the before run, 7 tries (all 5 of C3 query 5, plus C4 tries 1 and 4) were lost to a transient 503 at `suggest_outfit`'s model call. `generate.py` doesn't retry a 503, so one busy response ended the whole run. I picked a branch in my loop over adding 503 to `generate.py`'s retry condition for two reasons: it's one of the improvement types the brief names, and every retry shows up in the trace, so the after-run could count exactly how often it fired.

**Checking the branch itself:** a 503 can't be produced on demand, so I tested the branch with stubbed tools that raise a 503 or a bad-key error. The wait was set to 0 for the test only, and there were no model calls. Results are in [results/retry_branch_stub_test.txt](results/retry_branch_stub_test.txt):

| Case | What happened |
|---|---|
| busy, then OK | 2 outfit calls, then the fit card; no error |
| busy twice | 2 outfit calls, then the "busy" message |
| key rejected | 1 call, then stops; no retry |
| busy only at the fit card | the outfit isn't redone (1 call), the fit card is retried (2 calls) |
| no errors | unchanged |

The first version of this test failed: a rejected key was still retried because of a missing `break`. I fixed that before committing.

### Run Log — Before and After

Before: `results/run_2026-10-13_1425_before.md` (commit `c9ba1b3`, 14:17–14:25). After: [results/run_2026-10-13_1440_after.md](results/run_2026-10-13_1440_after.md) (commit `f1ae509`, 14:31–14:40, 70 tries, 130 model calls, 0 crashes, console in [results/run_after_console.txt](results/run_after_console.txt), scored in [results/score_after.txt](results/score_after.txt)). Both runs used the same scorer, the same strict per-query mapping for criteria 3 and 5, cache off and temperature 0.9.

**Run Log — Before**

| Criterion | Target | Try 1 | Try 2 | Try 3 | Try 4 | Try 5 | Verdict |
|---|---|---|---|---|---|---|---|
| 1. Matching query completes all three tools | ≥4 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 2. Impossible query stops before `suggest_outfit` | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 3. `suggest_outfit` gets the selected item and uses its title | id 5 of 5; words ≥4 of 5 | PASS | PASS | PASS | PASS | FAIL | MISSED (id 4/5; words 4/5) |
| 4. Fit card on `lst_006` is postable and varies | ≥4 of 5 pass; ≥4 distinct | FAIL | PASS | PASS | FAIL | PASS | MISSED (3/5; 3 distinct) |
| 5. Search respects price ceiling and size | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |

**Run Log — After**

| Criterion | Target | Try 1 | Try 2 | Try 3 | Try 4 | Try 5 | Verdict |
|---|---|---|---|---|---|---|---|
| 1. Matching query completes all three tools | ≥4 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 2. Impossible query stops before `suggest_outfit` | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 3. `suggest_outfit` gets the selected item and uses its title | id 5 of 5; words ≥4 of 5 | PASS | PASS | PASS | PASS | PASS | MET (id 5/5; words 5/5) |
| 4. Fit card on `lst_006` is postable and varies | ≥4 of 5 pass; ≥4 distinct | PASS | PASS | PASS | PASS | PASS | MET (5/5; 5 distinct) |
| 5. Search respects price ceiling and size | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |

(Criteria 3 and 5: Try k = named query k, and a query passes only if all 5 of its runs pass. That's all 25 runs, listed in `results/score_after.txt`.)

**Real output from the after run** (`results/run_2026-10-13_1440_after.md`, written by `run_eval.py::write_report`). C3 query 5, the cell that failed before, try 1:

```
[1] parse_query
      in:  denim jacket under $50
      out: description='denim jacket', size=None, max_price=50.0
[2] search_listings (via MCP)
      in:  description='denim jacket', size=None, max_price=50.0
      out: 7 items: Denim Jacket — Light Wash, Cropped, High-Waisted Denim Shorts — Cutoff, Denim Vest — Medium Wash, Studded … +4 more
      →    branch: not empty, selected_item = lst_007
[3] suggest_outfit
      in:  new_item.id=lst_007 (Denim Jacket — Light Wash, Cropped), wardrobe=10 items
      out: Outfit One Denim Jacket — Light Wash, Cropped White ribbed tank top Baggy straight-leg jeans, dark wash Chunky…
[4] create_fit_card
      in:  outfit (598 chars), new_item.id=lst_007
      out: Scored this vintage Wrangler Denim Jacket on Poshmark for just $42! I'm obsessed with the grunge-meets-prep vi…
```

C4, all five `lst_006` captions from `tools.py::create_fit_card`, which are 5 distinct strings:

```
try 1 (226 chars): Scored this sick 2003 tour bootleg Graphic Tee for just $24 on depop and I’m obsessed. Gives off the ultimate grunge vibe whether I'm styling it baggy with dark denim or tucked into tailored khakis. Head to my shop to grab it!
try 2 (219 chars): Scored this 2003 bootleg Graphic Tee for just $24 on depop and I’m obsessed. I'm styling it two ways: grunge with dark double denim, and clean streetwear with khaki trousers. Both give off such effortless vintage vibes!
try 3 (214 chars): Scored this 2003 Tour Bootleg Style Graphic Tee on depop for just $24! Obsessed with styling it grunge with baggy denim and boots, or leaning into streetwear with khaki trousers. It’s the ultimate effortless piece.
try 4 (209 chars): Scored this 2003 Tour Bootleg Style Graphic Tee for just $24 on depop! Styling it two ways: grungy with baggy dark denim and combat boots, then leaning into streetwear with wide-leg khakis and a grey crewneck.
try 5 (193 chars): Scored this sick 2003 tour bootleg Graphic Tee on depop for just $24! Obsessed with how it brings grunge energy to baggy jeans and contrast layering. Totally nailing that moody streetwear vibe.
```

**Did it help, and how do I know:** The scores went from 3 MET to 5 MET, but **I can't credit that to my change.** The retry branch **fired 0 times** in the after run: there are no `retrying once` lines and no `model unavailable` lines at all in `results/run_after_console.txt`. Gemini returned no 503s during that run, so every try would have passed without the improvement too. The after-run measured a healthy service, not my fix. What I *can* show is that the branch behaves correctly when a 503 happens (the stub test above), and that the failure it targets was real (the 7 tries in the before run). Whether it would actually have rescued those 7 tries depends on whether the 503 bursts last less than 20 seconds. I didn't measure that. In the before run, five consecutive runs of one query all failed, which suggests some bursts last longer than one 20-second wait. This is the noise problem with outages: before and after can't be compared cleanly when the thing being fixed may not happen during the "after" window.



---

## What's Still Broken

<!-- For each criterion still missed: what you'd do, and why you stopped where
     you did. "I ran out of time" is fine if it's true. Pretending nothing is
     left is not. -->

No criterion is missed in the after run. That doesn't mean nothing is broken, and it would be misleading to stop there.

**1. C3 and C4 still depend on Gemini being healthy, and my fix is unproven against a real outage.** Both misses in the before run were 503s. The after run had none, so the retry branch never ran for real. A burst longer than one 20-second wait still ends the run with "the model is busy" and no fit card, and the before run looked like it had bursts that long (5 consecutive runs of one query all failed). *What I'd do:* add a test-only switch that makes `generate()` fail with a 503 on a set fraction of calls, then run the eval with and without the branch, so the comparison doesn't depend on Google's load that afternoon. I'd also log how long real 503 bursts last before choosing the wait. If bursts are longer than 20 s, a backoff (20 s, then 40 s) or a retry inside `generate.py` would be the better fix. *Why I stopped:* the unit allows one improvement, and I can't make Gemini return 503s on demand. Adding a fault-injection switch would be a second code change outside the allowed list.

**2. Three of my targets were too easy to tell me much.** C2 and C5 are deterministic, so 5 tries are 1 test repeated 5 times. C2 uses one impossible query, and 3 of C5's 5 queries return exactly one listing. C1 is one query. *What I'd do:* tighten C2 first. Use 5 different impossible queries, each emptied by a different filter (price only, size only, keywords only), and require the message to name the filter that actually caused it. Right now the "use fewer or broader keywords" tip is added to every empty-search message, even when the keywords were fine. *Why I stopped:* the rules say a target I set in unit 3 isn't changed just because it was easy, and a new criterion would need writing down before any results exist. I'd write it at the start of the next unit.

**3. Search relevance has no floor.** `'plaid mini skirt under $40'` picked a reversible **bucket hat** (`lst_034`) as the top result, because the data has no skirt and the word "plaid" alone scored. None of my criteria checks relevance, so this passes everything. *What I'd do:* require the item word, the last keyword ("skirt"), to match the title, tags or category. If it doesn't, return `[]`, so the empty-search branch can say "no skirts in stock". *Why I stopped:* it's a tool change outside this unit's one allowed improvement, and the diagnosis didn't point at it, because no criterion measured it.

**4. Each MCP search costs about 2.3 s** (vs about 1 ms direct), because `mcp_client.call_tool` starts a new server process for every call. That's fine for one query on the command line, but under `serve.py` every request would pay it. *What I'd do:* keep one client session open for the life of the process. *Why I stopped:* `mcp_client.py` is given plumbing, and the brief chose the simpler model on purpose for this unit.

**5. The unit-3 "invented shoes" problem (How I Used AI, Moment 1) is still unmeasured.** C3 checks that the outfit names the new item. It doesn't check that every other piece named is really in the wardrobe. In this unit's runs, every piece I spot-checked was a real wardrobe item (including "Black cropped zip hoodie", which I checked), but I didn't check all 100+ outfits. *What I'd do:* a criterion that compares every listed piece against the wardrobe names.



<!-- ═════════════════════════════════════════════════════════════════════

     SUBMISSION CHECKLIST — unit 3

       [ ] criteria.md has five numbered criteria, each with a target
       [ ] Each criterion has a reason underneath it
       [ ] All five unit 3 sections above have real content
       [ ] Tool Inventory: all three tools, inputs WITH TYPES, a specific
           return value, and the empty case
       [ ] Planning Loop names the branch rule and agent.py::run_agent
       [ ] Sample Run: one full query plus the three per-tool tests, as text
       [ ] At least four new commits
       [ ] Repository URL submitted — WRITE IT DOWN, you submit the same one
           next unit

     SUBMISSION CHECKLIST — unit 4

       [ ] mcp_server.py exists with one tool registered
           (or a written record of exactly where the rewire broke)
       [ ] Run Log — Before, five criteria, five tries each
       [ ] Real output pasted underneath, naming file and function
       [ ] A verdict on every criterion
       [ ] A diagnosis for every miss, naming a place AND a mechanism
       [ ] Loop Trace, with the MCP call visible in it
       [ ] All three failure modes triggered and handled
       [ ] One improvement, with Run Log — After in the same format
       [ ] What's Still Broken
       [ ] At least four new commits
       [ ] The SAME repository URL as last unit

     Do not delete and recreate this repository. Your commit history is what
     shows your criteria existed before your results did.
     ═════════════════════════════════════════════════════════════════════ -->

---

📖 **How to run this project: [RUNNING.md](RUNNING.md)**
