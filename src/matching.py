from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Iterable, Optional

BRAND_TOKENS = frozenset(
    {
        "royal", "canin", "feringa", "cosma", "premiere", "zooroyal",
        "mjamjam", "animonda", "leonardo", "wolfsblut", "royalcanin",
    }
)

WET_FOOD_TOKENS = frozenset(
    {"sosse", "sauce", "nassfutter", "gelee", "jelly", "mousse", "ragout", "pastete"}
)
DRY_FOOD_TOKENS = frozenset({"trockenfutter", "trocken"})

STOP_WORDS = frozenset({"in", "mit", "und", "fuer", "fur", "the", "a", "an", "im", "von"})

TOKEN_ALIASES: dict[str, frozenset[str]] = {
    "meat": frozenset({"meat", "fleisch"}),
    "asia": frozenset({"asia", "thai"}),
    "hund": frozenset({"hund", "dog"}),
    "katze": frozenset({"katze", "cat"}),
}

# Never match (wrong category / species)
ALWAYS_REJECT = (
    "ergaenzung", "erganzung", "veterinary", "veterinaer",
)

# Seasonal / special editions — tracked separately, not as the primary listing
ALTERNATIVE_MARKERS = (
    "wintermenu", "saison", "limited edition", "limited",
)

# Savings bundles — prefer these when picking among matches
DEAL_BONUS_TERMS: dict[str, float] = {
    "sparpaket": 15.0,
    "spar paket": 15.0,
}

# Trial / sample packs — deprioritize vs regular listings
SOFT_PENALTY_TERMS: dict[str, float] = {
    "probiermix": 25.0,
    "probierpaket": 25.0,
}


@dataclass(frozen=True)
class PackSize:
    count: int
    amount: float
    unit: str


PACK_PATTERN = re.compile(
    r"(\d+)\s*[x×]\s*(\d+(?:[.,]\d+)?)\s*(g|kg|ml|l)(?![a-z])",
    re.IGNORECASE,
)


def parse_pack_size(text: str) -> Optional[PackSize]:
    if not text:
        return None
    compact = re.sub(r"[-_]", "", text.replace(" ", ""))
    match = PACK_PATTERN.search(compact) or PACK_PATTERN.search(text)
    if not match:
        return None
    count = int(match.group(1))
    amount = float(match.group(2).replace(",", "."))
    unit = match.group(3).lower()
    if unit == "kg":
        amount *= 1000
        unit = "g"
    return PackSize(count=count, amount=amount, unit=unit)


def pack_sizes_match(required: str, *texts: str) -> bool:
    if not required:
        return True
    required_pack = parse_pack_size(required)
    if required_pack is None:
        req = required.replace(" ", "").lower()
        return any(req in (t or "").replace(" ", "").lower() for t in texts)
    for text in texts:
        if not text:
            continue
        candidate_pack = parse_pack_size(text)
        if candidate_pack and (
            required_pack.count == candidate_pack.count
            and abs(required_pack.amount - candidate_pack.amount) < 0.01
            and required_pack.unit == candidate_pack.unit
        ):
            return True
    return False


def same_item_size(reference_pack: str, candidate_pack: str) -> bool:
    """True when each item is the same size (e.g. 85 g) but count may differ."""
    ref = parse_pack_size(reference_pack)
    cand = parse_pack_size(candidate_pack)
    if ref is None or cand is None:
        return False
    return (
        ref.unit == cand.unit
        and abs(ref.amount - cand.amount) < 0.01
        and ref.count != cand.count
    )


def same_item_size_in_listing(reference_pack: str, *texts: str) -> Optional[PackSize]:
    ref = parse_pack_size(reference_pack)
    if ref is None:
        return None
    for text in texts:
        if not text:
            continue
        cand = parse_pack_size(text)
        if (
            cand
            and cand.unit == ref.unit
            and abs(cand.amount - ref.amount) < 0.01
            and cand.count != ref.count
        ):
            return cand
    return None


def normalize_text(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.lower().replace("ß", "ss")
    text = re.sub(r"[^a-z0-9+]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"\b\+7\b", "7plus", text)
    text = re.sub(r"\b7\+\b", "7plus", text)
    text = re.sub(r"\+7", "7plus", text)
    text = re.sub(r"7\+", "7plus", text)
    text = re.sub(r"\binstinctive\s+7\b", "instinctive 7plus", text)
    text = re.sub(r"\b(sosse|sauce)\b", "sosse", text)
    text = re.sub(r"\b(jelly|gelee)\b", "gelee", text)
    text = re.sub(r"\b(menu|menue)\b", "menu", text)
    return text


def is_junk_candidate(title: str, url: str = "") -> bool:
    norm = normalize_text(title)
    return norm.startswith("suchergebnisse") or norm.startswith("produktsuche")


def _tokens(text: str) -> set[str]:
    return {t for t in normalize_text(text).split() if t not in STOP_WORDS and len(t) >= 2}


def _distinctive(query_tokens: set[str]) -> set[str]:
    return {t for t in query_tokens if t not in BRAND_TOKENS and len(t) >= 3}


def _token_satisfied(token: str, title_tokens: set[str]) -> bool:
    options = TOKEN_ALIASES.get(token, frozenset({token}))
    return bool(options & title_tokens)


def _distinctive_in_title(need: set[str], title_tokens: set[str]) -> bool:
    return all(_token_satisfied(token, title_tokens) for token in need)


def _combined(title: str, url: str, extra: str = "") -> str:
    return f"{title} {url} {extra}"


def _match_adjustment(norm_blob: str, norm_query: str) -> float:
    """Positive = prefer; negative = deprioritize."""
    adjustment = 0.0
    for term, value in DEAL_BONUS_TERMS.items():
        if term in norm_blob:
            adjustment += value
    for term, value in SOFT_PENALTY_TERMS.items():
        if term in norm_blob and term not in norm_query:
            adjustment -= value
    return adjustment


def is_alternative_listing(title: str, url: str = "", *, query: str = "") -> bool:
    norm_blob = normalize_text(_combined(title, url))
    norm_query = normalize_text(query) if query else ""
    return any(m in norm_blob and m not in norm_query for m in ALTERNATIVE_MARKERS)


def _brand_present(query_tokens: set[str], title_tokens: set[str]) -> bool:
    brands = {t for t in query_tokens if t in BRAND_TOKENS}
    if not brands:
        return True
    return bool(brands & title_tokens)


def product_matches(
    query: str,
    pack_size: str,
    title: str,
    *,
    url: str = "",
    extra: str = "",
) -> bool:
    if is_junk_candidate(title):
        return False

    blob = _combined(title, url, extra)
    norm_blob = normalize_text(blob)
    norm_query = normalize_text(query)

    for term in ALWAYS_REJECT:
        if term in norm_blob and term not in norm_query:
            return False

    if is_alternative_listing(title, url, query=query):
        return False

    q_tokens = _tokens(norm_query)
    b_tokens = _tokens(norm_blob)
    if not q_tokens:
        return False

    title_tokens = _tokens(normalize_text(title))
    url_tokens = _tokens(normalize_text(url))
    if not _brand_present(q_tokens, title_tokens | url_tokens):
        return False

    need = _distinctive(q_tokens)
    # Wet-food words are often omitted from short API titles — check separately
    core_need = need - WET_FOOD_TOKENS - {"7plus"}
    listing_tokens = title_tokens | url_tokens
    if core_need and not _distinctive_in_title(core_need, listing_tokens):
        return False

    wet_in_query = need & WET_FOOD_TOKENS
    if wet_in_query and not (wet_in_query & title_tokens):
        url_tokens = _tokens(normalize_text(url))
        if not (wet_in_query & url_tokens):
            conflicting = {"gelee", "mousse"} if "sosse" in wet_in_query else set()
            if conflicting & b_tokens:
                return False

    if pack_size and not pack_sizes_match(pack_size, title, url, extra):
        return False

    q_wet = bool(q_tokens & WET_FOOD_TOKENS)
    b_wet = bool(b_tokens & WET_FOOD_TOKENS)
    b_dry = bool(b_tokens & DRY_FOOD_TOKENS)
    if q_wet and b_dry and not b_wet:
        return False

    if "7plus" in q_tokens and "7plus" not in b_tokens:
        return False
    if "7plus" not in q_tokens and "7plus" in b_tokens:
        return False

    if "sosse" in need and "gelee" in b_tokens and "sosse" not in b_tokens:
        if "nassfutter" not in b_tokens and "nass" not in b_tokens:
            return False
    if "gelee" in need and "sosse" in b_tokens and "gelee" not in b_tokens:
        return False

    overlap = len(q_tokens & b_tokens) / len(q_tokens)
    if pack_size and pack_sizes_match(pack_size, title, url, extra):
        return overlap >= 0.3
    return overlap >= 0.45


def score_search_result(
    query: str,
    pack_size: str,
    title: str,
    *,
    url: str = "",
    extra_text: str = "",
    **_,
) -> float:
    if not product_matches(query, pack_size, title, url=url, extra=extra_text):
        return -1.0
    q_tokens = _tokens(normalize_text(query))
    b_tokens = _tokens(_combined(title, url, extra_text))
    overlap = len(q_tokens & b_tokens) / max(len(q_tokens), 1)
    score = overlap * 100
    if pack_size and pack_sizes_match(pack_size, title, url, extra_text):
        score += 50
    norm_blob = normalize_text(_combined(title, url, extra_text))
    norm_query = normalize_text(query)
    score += _match_adjustment(norm_blob, norm_query)
    return score


def pick_best_match(
    query: str,
    pack_size: str,
    candidates: Iterable[tuple[str, str, float, Optional[float], bool]],
    **_,
) -> Optional[tuple[str, str, float, str, bool]]:
    best: Optional[tuple[str, str, float, str, bool, float]] = None
    for title, url, price, original, in_stock in candidates:
        if not title:
            continue
        score = score_search_result(query, pack_size, title, url=url)
        if score < 0:
            continue
        if best is None or score > best[5]:
            orig = f"{original:.2f}" if original is not None else ""
            best = (title, url, price, orig, in_stock, score)
    if best is None:
        return None
    return best[0], best[1], best[2], best[3], best[4]


def alternative_variant_matches(
    query: str,
    pack_size: str,
    title: str,
    *,
    url: str = "",
    extra: str = "",
) -> bool:
    """Seasonal / limited variants: same brand + pack, looser name match."""
    if is_junk_candidate(title):
        return False
    if product_matches(query, pack_size, title, url=url, extra=extra):
        return False
    if not is_alternative_listing(title, url, query=query):
        return False

    blob = _combined(title, url, extra)
    norm_blob = normalize_text(blob)
    norm_query = normalize_text(query)

    for term in ALWAYS_REJECT:
        if term in norm_blob and term not in norm_query:
            return False

    if pack_size and not pack_sizes_match(pack_size, title, url, extra):
        return False

    q_tokens = _tokens(norm_query)
    b_tokens = _tokens(norm_blob)
    title_tokens = _tokens(normalize_text(title))
    if not q_tokens or not _brand_present(q_tokens, title_tokens):
        return False

    if "7plus" in q_tokens and "7plus" not in b_tokens:
        return False
    if "7plus" not in q_tokens and "7plus" in b_tokens:
        return False

    q_wet = bool(q_tokens & WET_FOOD_TOKENS)
    b_wet = bool(b_tokens & WET_FOOD_TOKENS)
    b_dry = bool(b_tokens & DRY_FOOD_TOKENS)
    if q_wet and b_dry and not b_wet:
        return False

    core_need = _distinctive(q_tokens) - WET_FOOD_TOKENS - {"7plus"}
    if core_need:
        hits = sum(1 for token in core_need if _token_satisfied(token, title_tokens))
        if hits < max(1, len(core_need) // 2):
            return False

    overlap = len(q_tokens & b_tokens) / len(q_tokens)
    return overlap >= 0.2


def pick_alternative_matches(
    query: str,
    pack_size: str,
    candidates: Iterable[tuple[str, str, float, Optional[float], bool]],
    *,
    exclude_url: str = "",
) -> list[tuple[str, str, float, Optional[float], bool]]:
    matches: list[tuple[str, str, float, Optional[float], bool]] = []
    seen: set[str] = set()
    for title, url, price, original, in_stock in candidates:
        if not title or not url or url in seen:
            continue
        if exclude_url and url.rstrip("/") == exclude_url.rstrip("/"):
            continue
        if not alternative_variant_matches(query, pack_size, title, url=url):
            continue
        seen.add(url)
        matches.append((title, url, price, original, in_stock))
    matches.sort(key=lambda row: row[2])
    return matches


def multipack_deal_matches(
    query: str,
    reference_pack: str,
    title: str,
    *,
    url: str = "",
    extra: str = "",
) -> bool:
    """Same product line and item size (e.g. 85 g) but different multipack count."""
    if is_junk_candidate(title):
        return False
    if product_matches(query, reference_pack, title, url=url, extra=extra):
        return False
    if is_alternative_listing(title, url, query=query):
        return False

    if same_item_size_in_listing(reference_pack, title, url, extra) is None:
        return False

    blob = _combined(title, url, extra)
    norm_blob = normalize_text(blob)
    norm_query = normalize_text(query)

    for term in ALWAYS_REJECT:
        if term in norm_blob and term not in norm_query:
            return False

    q_tokens = _tokens(norm_query)
    b_tokens = _tokens(norm_blob)
    title_tokens = _tokens(normalize_text(title))
    if not q_tokens or not _brand_present(q_tokens, title_tokens):
        return False

    need = _distinctive(q_tokens)
    core_need = need - WET_FOOD_TOKENS - {"7plus"}
    if core_need and not _distinctive_in_title(core_need, title_tokens):
        return False

    wet_in_query = need & WET_FOOD_TOKENS
    if wet_in_query and not (wet_in_query & title_tokens):
        url_tokens = _tokens(normalize_text(url))
        if not (wet_in_query & url_tokens):
            conflicting = {"gelee", "mousse"} if "sosse" in wet_in_query else set()
            if conflicting & b_tokens:
                return False

    q_wet = bool(q_tokens & WET_FOOD_TOKENS)
    b_wet = bool(b_tokens & WET_FOOD_TOKENS)
    b_dry = bool(b_tokens & DRY_FOOD_TOKENS)
    if q_wet and b_dry and not b_wet:
        return False

    if "7plus" in q_tokens and "7plus" not in b_tokens:
        return False
    if "7plus" not in q_tokens and "7plus" in b_tokens:
        return False

    if "sosse" in need and "gelee" in b_tokens and "sosse" not in b_tokens:
        if "nassfutter" not in b_tokens and "nass" not in b_tokens:
            return False
    if "gelee" in need and "sosse" in b_tokens and "gelee" not in b_tokens:
        return False

    overlap = len(q_tokens & b_tokens) / len(q_tokens)
    return overlap >= 0.3


def pick_multipack_matches(
    query: str,
    reference_pack: str,
    candidates: Iterable[tuple[str, str, float, Optional[float], bool]],
    *,
    exclude_urls: Iterable[str] = (),
) -> list[tuple[str, str, float, Optional[float], bool]]:
    from .pricing import unit_pricing_from_texts

    excluded = {u.rstrip("/") for u in exclude_urls if u}
    matches: list[tuple[str, str, float, Optional[float], bool, float]] = []
    seen: set[str] = set()

    for title, url, price, original, in_stock in candidates:
        if not title or not url or url in seen:
            continue
        if url.rstrip("/") in excluded:
            continue
        if not multipack_deal_matches(query, reference_pack, title, url=url):
            continue
        unit = unit_pricing_from_texts(price, title, url)
        if unit is None:
            continue
        seen.add(url)
        matches.append((title, url, price, original, in_stock, unit.price_per_piece))

    matches.sort(key=lambda row: row[5])
    return [row[:5] for row in matches]
