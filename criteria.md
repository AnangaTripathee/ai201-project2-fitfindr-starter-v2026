# Acceptance criteria — FitFindr

Five criteria that say what "working" means for this agent, written in unit 3
**before** any results existed.

An acceptance criterion names a target: a number, a count, a rate, or something
a person could plainly observe. *"The agent handles errors"* is an opinion.
*"When search returns nothing, the agent stops before calling the second tool,
in 5 of 5 tries"* is a criterion.

Under each one, write a sentence or two on **why that target** and not a
stricter one. A reason that says something about your tools, your loop, or the
data earns credit; *"80% seemed reasonable"* does not.

> Missing your own targets next unit costs you nothing. Setting a target so
> easy you can't miss it does.

**Two were written for me. I wrote three.**

---

## 1. A matching query completes all three tools

Given a query that matches at least one listing, the agent completes all three
tool calls and returns a fit card — in at least 4 of 5 tries.

**Why this target:** Every run makes two model calls, and either one can come back
slow, rate-limited or malformed, so one bad try out of five can happen even when
the loop is correct. 5 of 5 would be scoring the model service as much as my code.
When I check this, a fit card only counts if it is a real caption from the model,
not the "Can't write a fit card…" fallback that `create_fit_card` returns when the
outfit text is empty.

---

## 2. An impossible query stops before the second tool

Given a query that matches no listings, the agent stops before calling
`suggest_outfit` and returns a message naming what to change — 5 of 5 tries.

**Why this target:** This path makes no model calls. Parsing, search and the
branch are all plain Python, so the same query gives the same result every time,
and any miss is a bug in my branch, not noise. When I check this, the message only
counts if it names a specific change, such as raising the price ceiling, trying a
different size or using broader keywords. A message that only says "price" or
"no results" fails.

---

## 3. The item search picked is the item `suggest_outfit` receives

Across these 5 different matching queries, the `id` that `suggest_outfit` receives
equals `session["selected_item"]["id"]` in 5 of 5 queries:

1. `vintage graphic tee under $30`
2. `90s track jacket in size M`
3. `silk slip dress in midi length under $40`
4. `platform sneakers size 8`
5. `denim jacket under $50`

The id is logged inside `suggest_outfit`, from its own `new_item` parameter. It is
never read from the session, so the check can fail. Separately, the outfit text
contains at least 2 words from the part of the item's title before the "—"
(case-insensitive) in at least 4 of 5 queries.

**Why this target:** The id match is plain Python with no model involved, so any
miss is a bug, and the target is 5 of 5. The title-word check depends on how the
model phrases things. Requiring the whole title would fail by design, because
titles like "Graphic Tee — 2003 Tour Bootleg Style" are rarely repeated exactly,
so I ask for 2 title words in 4 of 5.

---

## 4. The fit card is postable and varies

Run `create_fit_card` 5 times on `lst_006` with `CACHE_ENABLED` off. In at least
4 of 5 runs, the caption is 280 characters or fewer, contains at least 2 words
from the part of the title before the "—", and contains the price and the
platform. Also, at least 4 of the 5 captions are distinct strings.

**Why this target:** Every part of this can be counted. The prompt controls the
length, price and platform, so I expect nearly every run to pass, and I allow one
miss because the model can slip. Requiring 4 distinct captions is a real check
that the output varies, not just that a setting is on. Fixing the item to
`lst_006` means a missing brand can't change the result.

---

## 5. Search respects the price ceiling and the size

Run these 5 named queries:

1. `graphic tee size L under $30`
2. `top size M under $25` (only `S/M` listings qualify)
3. `bucket hat size M under $20` (a `One Size` listing)
4. `sneakers size 8 under $50` (`US 8` must match and `US 8.5` must not)
5. `jacket size S under $45`

Each query must return
at least 1 listing, and every returned listing must have `price <= max_price` and
a size that matches under the spec's token rule (`S/M` matches `M`; `One Size`
matches any size). 5 of 5 queries must pass. An empty result counts as a failure.

**Why this target:** This is deterministic filtering, so any miss is a bug, and I
allow none. Requiring at least 1 result stops a broken search that returns nothing
from passing, and naming the queries stops me from picking easy ones.

---

<!-- ─────────────────────────────────────────────────────────────────────────
     UNIT 4 — read this before you change anything above.

     If a criterion turns out to be BROKEN rather than merely unmet, you can
     revise it, and that earns credit. But never delete or edit the original
     line. Add the revision underneath it, like this:

         ## 4. Something about the fit card

         The fit card is different every time.

         **Why this target:** ...

         > **Revised in unit 4:** For 5 different items, the 5 fit cards share
         > no opening sentence.
         >
         > **Why revised:** "different" wasn't checkable — two cards that
         > differed by one word still counted. The new version is something I
         > can actually score.

     That's a revision because the criterion couldn't be MEASURED.

     Lowering a target because you missed it is not a revision, and it costs
     you the point:

         ✗ "I said the empty search stops it 5 of 5 times, but I got 3 of 5,
            so 3 of 5 is more realistic."

     A number you missed stays where it is, gets diagnosed, and gets a fix
     attempted. That's where the points are.
     ───────────────────────────────────────────────────────────────────────── -->
