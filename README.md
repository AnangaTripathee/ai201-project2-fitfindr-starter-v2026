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

<!-- Three or four sentences: what a user asks for, and what they get back. -->



---

## Tool Inventory

### `search_listings`

- **What it does:** Finds the thrift listings in `data/listings.json` (loaded with `utils.data_loader.load_listings()`) that match a keyword description, a size and a price ceiling, best match first. It does not call the model.
- **Inputs:**
  - `description` (str): keywords such as `"vintage graphic tee"`. It is lowercased and split into words; filler words (`a`, `the`, `for`, `and`, `with`, `in`, `of`) are dropped.
  - `size` (str or None): a size such as `"M"`, `"8"`, `"US 8"` or `"W30"`. `None` skips the size filter. Both sizes are uppercased and split into tokens on spaces, `/` and parentheses. A listing passes when **every token of the requested size is a whole token of the listing's `size`**. So `"M"` matches `M`, `S/M` and `M/L` but not `XL (oversized)`; `"8"` matches `US 8` but not `US 8.5`; `"S"` does not match `US 9`. Listings whose size starts with `One Size` pass any size filter, because they fit anyone.
  - `max_price` (float or None): the price ceiling, inclusive (`price <= max_price`). `None` skips the price filter.
- **Returns:** a `list[dict]` of at most `config.SEARCH_RESULT_LIMIT` (10) listings. Each dict is the unchanged listing with all 11 fields: `id` (str), `title` (str), `description` (str), `category` (str), `style_tags` (list[str]), `size` (str), `condition` (str), `price` (float), `colors` (list[str]), `brand` (str or None) and `platform` (str). Text is lowercased and split into words on anything that isn't a letter or digit, so the tag `"graphic tee"` gives the words `graphic` and `tee`. Each keyword scores 2 if it is one of the words of the `title` or `style_tags`, and 1 if it appears only in the `description`, `category` or `colors`. A trailing plural `s` is ignored on both sides, so `tees` matches `tee`. A listing's score is the sum over all keywords. Listings scoring 0 are dropped. Results are sorted by score, highest first, with the cheaper item first on a tie. If `description` has no keywords left after the filler words are dropped, scoring is skipped: every listing that passes the size and price filters comes back, cheapest first.
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
- **Returns:** a `str` caption, with surrounding whitespace stripped. The prompt asks the model for 2 to 4 sentences under 400 characters, in a casual first-person voice, that mention the item's `title` (or a short form of it), its `price` as `$NN` and its `platform`, each once. It mentions `brand` only when brand is not `None`. It runs at `config.TEMPERATURE` (0.9), so the wording changes between runs.
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

---

## Sample Run

<!-- Two things go here.

     1. One FULL query and its output, pasted as text.
     2. Your three per-tool terminal tests — the command and what it printed. -->

**One full query**

```
$ python app.py ask '...'

```

**The three tools, tested one at a time**

```
$ python -c "from tools import search_listings; print(search_listings('graphic tee', max_price=30))"

```

```
$ python -c "from tools import suggest_outfit; ..."

```

```
$ python -c "from tools import create_fit_card; ..."

```

---

## How I Used AI

<!-- Two specific moments. What you asked, what came back, what you changed.

     "I used Claude to help me code" is not enough.

     "I gave Claude my search_listings spec. It returned None on no match
     instead of an empty list, so I changed it" is the level we want. -->

**Moment 1**

- *What I asked for:*
- *What came back:*
- *What I changed:*

**Moment 2**

- *What I asked for:*
- *What came back:*
- *What I changed:*

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
