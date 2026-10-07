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

| Criterion | Target | Try 1 | Try 2 | Try 3 | Try 4 | Try 5 | Verdict |
|---|---|---|---|---|---|---|---|
| 1.  |  |  |  |  |  |  |  |
| 2.  |  |  |  |  |  |  |  |
| 3.  |  |  |  |  |  |  |  |
| 4.  |  |  |  |  |  |  |  |
| 5.  |  |  |  |  |  |  |  |

**Real output from one try**, pasted as text, naming the file and function
that produced it:

```

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
| 1 |  |  |  |  |
| 2 |  |  |  |  |
| 3 |  |  |  |  |
| 4 |  |  |  |  |
| 5 |  |  |  |  |

**Diagnoses**



---

## Loop Trace

<!-- One full run, printed step by step, with the MCP call visible in it.

     `python app.py ask '...' --trace` once you've added the trace.step()
     calls in Milestone 2.

     Worth pasting BOTH the happy path and the empty-search path. The empty
     one should be visibly shorter, because it stops. If your two traces are
     the same length, your branch isn't working — and this is the fastest way
     anyone will ever find that out. -->

**Happy path**

```

```

**Empty search**

```

```

**On the MCP move:** <!-- what changed in your code, and whether anything
behaved differently afterwards. If the rewire didn't work, say exactly where it
broke — the error text and the last thing that worked. That earns the point in
full. -->



---

## The Improvement

<!-- What you changed, why your diagnosis pointed at it, and the after-run in
     the same table format. One change, measured properly.

     `python run_eval.py --label after` -->

**What I changed:**

**Which failure it was meant to fix:**

### Run Log — After

| Criterion | Target | Try 1 | Try 2 | Try 3 | Try 4 | Try 5 | Verdict |
|---|---|---|---|---|---|---|---|
| 1.  |  |  |  |  |  |  |  |
| 2.  |  |  |  |  |  |  |  |
| 3.  |  |  |  |  |  |  |  |
| 4.  |  |  |  |  |  |  |  |
| 5.  |  |  |  |  |  |  |  |

**Did it help, and how do I know:**

<!-- If it made things worse, say that. Honestly reported, that earns full
     credit and is more interesting than one that worked. -->



---

## What's Still Broken

<!-- For each criterion still missed: what you'd do, and why you stopped where
     you did. "I ran out of time" is fine if it's true. Pretending nothing is
     left is not. -->



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
