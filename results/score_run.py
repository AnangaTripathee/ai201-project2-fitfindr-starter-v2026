"""Score a run_eval.py report against criteria.md. Reads only the saved report,
except criterion 5's per-listing check, which re-calls the MCP tool with the
exact inputs logged in the trace (search is deterministic) and confirms the
count and first titles match what the report logged.

usage: python results/score_run.py results/run_..._before.md   (from the repo root)
"""
import re
import sys

sys.path.insert(0, ".")

FALLBACK = "Can't write a fit card"


def sections(text):
    parts = re.split(r"^### ", text, flags=re.M)[1:]
    out = {}
    for p in parts:
        name, body = p.split("\n", 1)
        tries = re.split(r"^\*\*Try (\d+)\*\*", body, flags=re.M)
        out[name.strip()] = [parse_try(tries[i + 1]) for i in range(1, len(tries) - 1, 2)]
    return out


def block(label, body):
    m = re.search(rf"^{label}:\n\n```\n(.*?)\n```", body, flags=re.M | re.S)
    return m.group(1) if m else None


def parse_try(body):
    t = {"crashed": block("Crashed", body) if body.lstrip().startswith("Crashed") else None}
    m = re.search(r"^- stopped early: (.*)$", body, flags=re.M)
    t["error"] = None if not m or m.group(1) == "no" else m.group(1)[len("yes — "):]
    m = re.search(r"^- search_results: (\d+)", body, flags=re.M)
    t["n_results"] = int(m.group(1)) if m else None
    t["outfit"] = block("Outfit suggestion", body)
    t["fit_card"] = block("Fit card", body)
    t["trace"] = block("Trace", body) or ""
    m = re.search(r"selected_item = (lst_\d+)", t["trace"])
    t["selected_id"] = m.group(1) if m else None
    m = re.search(r"\] suggest_outfit\n\s+in:\s+new_item\.id=(lst_\d+)", t["trace"])
    t["outfit_id"] = m.group(1) if m else None
    m = re.search(r"\] search_listings \(via MCP\)\n\s+in:\s+(.*)\n\s+out:\s+(.*)", t["trace"])
    t["search_in"], t["search_out"] = (m.group(1), m.group(2)) if m else (None, None)
    t["steps"] = re.findall(r"^\[\d+\] (.+)$", t["trace"], flags=re.M)
    return t


def title_words(title):
    return [w for w in re.findall(r"[a-z0-9]+", title.split("—")[0].lower())]


def has_word(text, w):
    return re.search(rf"(?<![a-z0-9]){re.escape(w)}(?![a-z0-9])", text.lower()) is not None


def main(path):
    from utils.data_loader import load_listings
    L = {x["id"]: x for x in load_listings()}
    S = sections(open(path, encoding="utf-8").read())
    rows = {}

    # C1
    c1 = []
    for t in S["matching query completes"]:
        ok = not t["crashed"] and not t["error"] and t["fit_card"] and not t["fit_card"].startswith(FALLBACK)
        c1.append((ok, f"error={t['error'][:70] if t['error'] else None!r} card_len={len(t['fit_card'] or '')}"))
    rows[1] = c1

    # C2
    c2 = []
    for t in S["impossible query stops early"]:
        specific = bool(t["error"]) and any(k in t["error"] for k in ("raise the price ceiling", "different size", "broader keywords"))
        stopped = t["outfit"] is None and t["fit_card"] is None and "suggest_outfit" not in t["steps"]
        c2.append((specific and stopped and not t["crashed"], f"steps={t['steps']} specific={specific}"))
    rows[2] = c2

    # C3: per query, all 5 tries scored; column = query
    c3_id, c3_words = [], []
    for name in [n for n in S if n.startswith("c3 ")]:
        per = []
        for t in S[name]:
            id_ok = t["outfit_id"] is not None and t["outfit_id"] == t["selected_id"]
            words = title_words(L[t["selected_id"]]["title"]) if t["selected_id"] else []
            found = [w for w in words if t["outfit"] and has_word(t["outfit"], w)]
            per.append((id_ok, len(found) >= 2, f"{t['selected_id']}->{t['outfit_id']} words={found} err={bool(t['error'])}"))
        c3_id.append((name, per)); c3_words.append(name)
    rows[3] = c3_id

    # C4
    c4 = []
    cards = []
    for t in S["c4 fit card on lst_006"]:
        card = t["fit_card"] or ""
        cards.append(card)
        item = L["lst_006"]
        words = [w for w in title_words(item["title"]) if has_word(card, w)]
        checks = {
            "is_lst_006": t["selected_id"] == "lst_006",
            "len<=280": 0 < len(card) <= 280,
            "2 title words": len(words) >= 2,
            "price $24": "$24" in card,
            "platform": "depop" in card.lower(),
        }
        c4.append((all(checks.values()) and not t["error"], f"len={len(card)} {checks}"))
    distinct = len(set(c for c in cards if c))
    rows[4] = (c4, distinct)

    # C5
    from mcp_client import call_tool
    c5 = []
    for name in [n for n in S if n.startswith("c5 ")]:
        per = []
        for t in S[name]:
            m = re.match(r"description='(.*)', size=(.*), max_price=(.*)", t["search_in"] or "")
            desc, size, price = m.group(1), eval(m.group(2)), eval(m.group(3))
            res = call_tool("search_listings", {"description": desc, "size": size, "max_price": price})
            from tools import _size_matches
            same = len(res) == t["n_results"] and all(x["title"] in t["search_out"] for x in res[:3])
            bad = [(x["id"], x["size"], x["price"]) for x in res if x["price"] > price or not _size_matches(size, x["size"])]
            per.append((len(res) >= 1 and not bad and same, f"n={len(res)} bad={bad} matches_log={same}"))
        c5.append((name, per))
    rows[5] = c5

    P = lambda b: "PASS" if b else "FAIL"
    print("C1:", [P(ok) for ok, _ in rows[1]], f"{sum(ok for ok, _ in rows[1])}/5")
    for ok, d in rows[1]: print("    ", P(ok), d)
    print("C2:", [P(ok) for ok, _ in rows[2]], f"{sum(ok for ok, _ in rows[2])}/5")
    for ok, d in rows[2]: print("    ", P(ok), d)
    print("C3 (one column per query; a query passes a part only if all 5 of its tries pass):")
    id_cols = [all(i for i, _, _ in per) for _, per in rows[3]]
    w_cols = [all(w for _, w, _ in per) for _, per in rows[3]]
    w_cols_try1 = [per[0][1] for _, per in rows[3]]
    print("   id match :", [P(x) for x in id_cols], f"{sum(id_cols)}/5 (target 5/5)")
    print("   2 words  :", [P(x) for x in w_cols], f"{sum(w_cols)}/5 (target 4/5)  [try-1-only view: {sum(w_cols_try1)}/5]")
    for name, per in rows[3]:
        print("    ", name)
        for i, w, d in per: print("        id", P(i), "words", P(w), d)
    c4, distinct = rows[4]
    print("C4:", [P(ok) for ok, _ in c4], f"{sum(ok for ok, _ in c4)}/5 (target 4/5); distinct captions {distinct}/5 (target 4)")
    for ok, d in c4: print("    ", P(ok), d)
    print("C5 (one column per query):")
    cols = [all(ok for ok, _ in per) for _, per in rows[5]]
    print("   ", [P(x) for x in cols], f"{sum(cols)}/5 (target 5/5)")
    for name, per in rows[5]:
        print("    ", name, [d for _, d in per][0], "| all tries pass:", all(ok for ok, _ in per))


if __name__ == "__main__":
    main(sys.argv[1])
