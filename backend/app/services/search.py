"""Product search and shopping-list parsing.

Used by the catalog search bar and by in-store mode, where a customer types or
speaks a list such as "2 milk, brown bread and a dozen eggs" and we work out
which products they mean.

This is a lightweight in-memory ranker that is fine for a few thousand
products per store. Swap it for Postgres full-text search or a search engine
when the catalog grows.
"""

import re
from collections.abc import Iterable
from dataclasses import dataclass
from difflib import SequenceMatcher

from ..models import Product

NUMBER_WORDS = {
    "a": 1, "an": 1, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
    "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "couple": 2,
}  # fmt: skip

# "2 packets of chips" -> quantity 2 of "chips"
COUNT_WORDS = {
    "pack", "packs", "packet", "packets", "pc", "pcs", "piece", "pieces", "bottle", "bottles",
    "box", "boxes", "unit", "units", "bag", "bags", "can", "cans", "jar", "jars", "x",
}  # fmt: skip

# "1 kg onion" -> quantity 1 of "1 kg onion" (the size helps pick the right pack)
UNIT_ALIASES = {
    "kg": "kg", "kgs": "kg", "kilo": "kg", "kilos": "kg", "kilogram": "kg", "kilograms": "kg",
    "g": "g", "gm": "g", "gms": "g", "gram": "g", "grams": "g",
    "l": "l", "ltr": "l", "litre": "l", "litres": "l", "liter": "l", "liters": "l",
    "ml": "ml",
}  # fmt: skip

FILLER_WORDS = {
    "i", "want", "wanna", "need", "to", "buy", "get", "me", "please", "some", "also", "of",
    "the", "with", "would", "like", "add", "pick", "grab", "few", "more", "my", "for", "give",
    "and", "then", "um", "uh", "okay", "ok", "can", "you", "find", "where", "is", "are",
}  # fmt: skip

SPLIT_RE = re.compile(r"[,\n;]+|\band\b|&|\+|\bthen\b|\balso\b|\bplus\b", re.IGNORECASE)

MATCH_THRESHOLD = 1.2


def _normalize(text: str) -> str:
    text = text.lower()
    text = re.sub(r"(\d)([a-z])", r"\1 \2", text)  # "1kg" -> "1 kg"
    text = re.sub(r"([a-z])(\d)", r"\1 \2", text)  # "x2" -> "x 2"
    return text


def _stem(token: str) -> str:
    if len(token) > 4 and token.endswith("ies"):
        return token[:-3] + "y"
    if len(token) > 4 and token.endswith("oes"):
        return token[:-2]
    if len(token) > 3 and token.endswith("s") and not token.endswith("ss"):
        return token[:-1]
    return token


def tokenize(text: str) -> list[str]:
    tokens = re.findall(r"[a-z0-9]+", _normalize(text))
    return [UNIT_ALIASES.get(t, _stem(t)) for t in tokens]


def _to_number(token: str) -> int | None:
    if token.isdigit():
        return int(token)
    return NUMBER_WORDS.get(token)


@dataclass
class ParsedItem:
    query: str
    quantity: int


def parse_shopping_list(text: str) -> list[ParsedItem]:
    items: list[ParsedItem] = []
    for part in SPLIT_RE.split(text):
        raw = re.findall(r"[a-z0-9]+", _normalize(part))
        tokens = [t for t in raw if t not in FILLER_WORDS or t in NUMBER_WORDS]
        quantity = 1

        if tokens and _to_number(tokens[0]) is not None:
            is_size = len(tokens) > 1 and tokens[1] in UNIT_ALIASES
            if not is_size:
                quantity = _to_number(tokens[0]) or 1
                tokens = tokens[1:]
        if len(tokens) >= 2 and tokens[-1].isdigit() and tokens[-2] not in UNIT_ALIASES:
            quantity = int(tokens[-1])  # "milk x 2" / "milk 2"
            tokens = tokens[:-1]

        tokens = [t for t in tokens if t not in COUNT_WORDS and t not in ("a", "an")]
        if tokens:
            items.append(ParsedItem(" ".join(tokens), max(1, min(quantity, 50))))
    return items


@dataclass
class _Indexed:
    product: Product
    fields: list[tuple[float, list[str]]]
    name_norm: str
    keyword_phrases: set[str]
    head: str  # last word of the name, usually the noun ("Toned Milk" -> "milk")


def _index(product: Product) -> _Indexed:
    keywords = " ".join(product.keywords.split(","))
    name_tokens = tokenize(product.name)
    return _Indexed(
        product=product,
        fields=[
            (3.0, name_tokens),
            (3.0, tokenize(keywords)),
            (2.0, tokenize(product.brand or "")),
            (1.5, tokenize(product.category.name if product.category else "")),
            (1.0, tokenize(product.unit)),
        ],
        name_norm=" ".join(name_tokens),
        keyword_phrases={" ".join(tokenize(k)) for k in product.keywords.split(",") if k.strip()},
        head=name_tokens[-1] if name_tokens else "",
    )


def _token_score(query_token: str, field_tokens: list[str], weight: float) -> float:
    best = 0.0
    for ft in field_tokens:
        if query_token == ft:
            return weight
        if len(query_token) >= 2 and ft.startswith(query_token):
            best = max(best, weight * 0.8)
        elif len(query_token) >= 4 and len(ft) >= 4:
            ratio = SequenceMatcher(None, query_token, ft).ratio()
            if ratio >= 0.8:
                best = max(best, weight * ratio * 0.8)
    return best


def score(query_tokens: list[str], item: _Indexed) -> float:
    if not query_tokens:
        return 0.0
    total = 0.0
    matched = 0
    has_text_match = False
    for qt in query_tokens:
        per_field = [_token_score(qt, tokens, weight) for weight, tokens in item.fields]
        best = max(per_field)
        if best > 0:
            matched += 1
            # Matching in several fields (name + keywords) means a stronger match.
            total += best + 0.5 * (sum(1 for s in per_field if s > 0) - 1)
            if any(s > 0 for s in per_field[:4]):
                has_text_match = True
        if qt == item.head:
            total += 0.5
    coverage = matched / len(query_tokens)
    if not has_text_match or coverage < 0.5:
        return 0.0
    result = total / len(query_tokens) * coverage
    phrase = " ".join(query_tokens)
    if phrase in item.keyword_phrases:
        result += 2.0  # an exact synonym ("aloo" -> Potato) says what the customer means
    elif phrase in item.name_norm:
        result += 1.0
    return result


def rank_products(
    products: Iterable[Product], query: str, in_stock: set[int] | None = None, limit: int = 20
) -> list[tuple[Product, float]]:
    """Products matching `query`, best first. In-stock products win ties."""
    query_tokens = tokenize(query)
    scored = []
    for product in products:
        s = score(query_tokens, _index(product))
        if s >= MATCH_THRESHOLD:
            scored.append((product, s))
    stocked = in_stock or set()
    scored.sort(key=lambda ps: (ps[0].id not in stocked, -round(ps[1], 2), len(ps[0].name)))
    return scored[:limit]
