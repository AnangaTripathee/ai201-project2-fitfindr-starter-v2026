# Data notes (Milestone 1)

Notes from reading `data/listings.json` and `data/wardrobe_schema.json` through
`python app.py fields` and `python app.py listings --full -n 6`, before writing
any tools.

## Listings: 40 records

| Field | Type | Notes |
|---|---|---|
| `id` | str | `lst_001` … `lst_040` |
| `title` | str | e.g. "Graphic Tee — 2003 Tour Bootleg Style" |
| `description` | str | one or two sentences, often mentions fit ("fits like a small") |
| `category` | str | tops (15), bottoms (10), outerwear (8), shoes (4), accessories (3) |
| `style_tags` | list[str] | e.g. `["graphic tee", "vintage", "grunge"]`; some tags are two words |
| `size` | str | mixed formats, see below |
| `condition` | str | excellent, good, fair |
| `price` | float | $12.00 to $75.00 |
| `colors` | list[str] | e.g. `["black"]` |
| `brand` | str or None | **None for 32 of 40**, so nothing can assume a brand |
| `platform` | str | depop (18), thredUp (11), poshmark (11) |

### Size formats (why a plain substring test won't work)

- Letter sizes: `S`, `M`, `L`, `XL`
- Ranges: `S/M`, `M/L`, `L/XL`
- Letter plus a note: `XL (oversized)`, `XL (fits oversized)`
- Shoes: `US 7`, `US 8`, `US 8.5`, `US 9`
- Waist (and inseam): `W27` … `W32`, `W30 L30`
- One size: `One Size`, `One Size (adjustable)`, `One Size / Oversized`

`"s" in "us 9"` and `"l" in "xl"` are both True, so size has to be matched
token by token, not as a substring.

## Wardrobe

`get_example_wardrobe()` returns `{"items": [...]}` with 10 items. Each item has:
`id` (str), `name` (str), `category` (str), `colors` (list[str]),
`style_tags` (list[str]), `notes` (str or None).

`get_empty_wardrobe()` returns the same shape with nothing in it:

```python
{"items": []}
```

The loader strips the `_note` key, so both wardrobes are exactly `{"items": [...]}`.
