"""Fuzzy product matching, used by the search bar and by in-store shopping lists.

Shoppers type or speak things like "2 doodh, brown bread, 1kg atta and maggi" or, from voice input
with no punctuation at all, "milk bread eggs". This module turns that into product matches:

1. Split the text into chunks on commas / new lines / "and" / "aur".
2. Within a chunk, read quantities ("2", "two", "do", "x2") and pack sizes ("1kg", "500 ml").
3. Score products by how well their name, brand, tags (synonyms, Hindi names) and subcategory
   cover the words, tolerating typos ("tomatos") and partial words ("mag" -> maggi).
4. If a chunk doesn't match one product well, split it into the best sequence of products
   ("milk bread eggs" -> milk + bread + eggs, while "milk bread" alone stays one product).
"""

import math
import re
from dataclasses import dataclass, field
from functools import cached_property

from rapidfuzz import fuzz, process

from app.models import Product

MATCH_THRESHOLD = 62  # minimum score to treat a product as what the shopper asked for
STRONG_MATCH = 100  # a whole chunk scoring this high is never split into several products
SUGGESTION_THRESHOLD = 38
MAX_SPAN = 4  # longest product phrase considered when splitting an unpunctuated chunk
SPAN_PENALTY = 5  # per extra product when splitting, so ties prefer fewer products

STOPWORDS = {
    "a", "an", "the", "of", "some", "please", "pls", "i", "need", "want", "to", "buy", "get",
    "me", "also", "and", "with", "for", "my", "few", "any", "or", "aur", "bhi", "chahiye", "lena",
    "hai", "ka", "ki", "ke",
}  # fmt: skip
NUMBER_WORDS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8,
    "nine": 9, "ten": 10, "twelve": 12, "ek": 1, "do": 2, "teen": 3, "char": 4, "paanch": 5,
}  # fmt: skip
# unit -> (base unit, multiplier)
SIZE_UNITS = {
    "kg": ("g", 1000), "kgs": ("g", 1000), "kilo": ("g", 1000), "kilos": ("g", 1000),
    "g": ("g", 1), "gm": ("g", 1), "gms": ("g", 1), "gram": ("g", 1), "grams": ("g", 1),
    "l": ("ml", 1000), "ltr": ("ml", 1000), "litre": ("ml", 1000), "liter": ("ml", 1000),
    "litres": ("ml", 1000), "liters": ("ml", 1000), "ml": ("ml", 1),
}  # fmt: skip
COUNT_UNITS = {
    "x", "pc", "pcs", "piece", "pieces", "pack", "packs", "packet", "packets", "pkt", "pkts",
    "nos", "bottle", "bottles", "box", "boxes", "unit", "units",
}  # fmt: skip

PIECE_UNITS = {"pc", "pcs", "piece", "pieces"}

_SPLIT_RE = re.compile(r"[,\n;/+&]+|\band\b|\baur\b|\bplus\b|\bthen\b", re.IGNORECASE)
_NUMBER_RE = re.compile(r"^\d+(?:\.\d+)?$")
_ATTACHED_RE = re.compile(r"^(\d+(?:\.\d+)?)([a-z]+)$")  # 500g, 2kg, 2pcs, 2x
_X_COUNT_RE = re.compile(r"^x(\d+)$")  # x2
_SIZE_IN_TEXT_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(" + "|".join([*SIZE_UNITS, *PIECE_UNITS]) + r")\b")


def normalize(text: str) -> str:
    text = text.lower().replace("&", " and ").replace("'", "").replace("’", "")
    text = re.sub(r"[^a-z0-9.]+", " ", text)
    text = re.sub(r"(?<!\d)\.|\.(?!\d)", " ", text)  # keep dots only inside numbers
    return " ".join(text.split())


def singular(token: str) -> str:
    if len(token) <= 3 or not token.isalpha():
        return token
    if token.endswith("oes"):
        return token[:-2]  # tomatoes -> tomato
    if token.endswith(("ches", "shes", "xes")):
        return token[:-2]  # peaches -> peach
    if token.endswith("s") and not token.endswith(("ss", "us", "is")):
        return token[:-1]  # eggs -> egg, biscuits -> biscuit
    return token


def words_of(text: str) -> list[str]:
    return [singular(t) for t in normalize(text).split() if t not in STOPWORDS]


def phrase_of(text: str) -> str:
    return " ".join(words_of(text))


def parse_size(text: str) -> tuple[str, float] | None:
    """'500 ml' -> ('ml', 500); '1 kg' -> ('g', 1000); '6 pcs' -> ('pc', 6)."""
    m = _SIZE_IN_TEXT_RE.search(normalize(text))
    if not m:
        return None
    if m.group(2) in PIECE_UNITS:
        return "pc", float(m.group(1))
    base, factor = SIZE_UNITS[m.group(2)]
    return base, float(m.group(1)) * factor


def packs_for_pieces(pieces: int, unit_label: str) -> int | None:
    """'6 eggs' of a '6 pcs' pack is one pack; '12 eggs' is two. None if not sold by the piece."""
    size = parse_size(unit_label)
    if size is None or size[0] != "pc" or size[1] < 1:
        return None
    return max(1, math.ceil(pieces / size[1]))


@dataclass
class _Doc:
    product: Product
    name_tokens: set[str]
    all_tokens: set[str]
    phrases: set[str]  # name + tags, normalized
    name_phrase: str
    subcategory_tokens: set[str]
    size: tuple[str, float] | None


@dataclass
class Match:
    product: Product
    score: float


@dataclass
class ParsedRequest:
    words: list[str]  # normalized for matching ("egg")
    display: list[str] = field(default_factory=list)  # as the shopper said it ("eggs")
    quantity: int = 1
    explicit_quantity: bool = False
    size: tuple[str, float] | None = None
    trailing_quantity: bool = False


@dataclass
class ListLine:
    """One thing the shopper asked for, after splitting and matching."""

    query: str
    quantity: int
    matches: list[Match] = field(default_factory=list)
    pieces: int | None = None  # "6 eggs": a count that may mean pieces rather than packs

    @property
    def best(self) -> Match | None:
        if self.matches and self.matches[0].score >= MATCH_THRESHOLD:
            return self.matches[0]
        return None


class ProductMatcher:
    def __init__(self, products: list[Product], subcategory_names: dict[int, str]):
        self.docs: list[_Doc] = []
        self.vocab: dict[str, set[int]] = {}
        for product in products:
            name_words = words_of(product.name)
            subcategory = words_of(subcategory_names.get(product.category_id, ""))
            tags = [phrase_of(t) for t in product.tags or []]
            brand = words_of(product.brand or "")
            all_tokens = set(name_words) | set(subcategory) | set(brand)
            for tag in tags:
                all_tokens.update(tag.split())
            name_phrase = " ".join(name_words)
            doc = _Doc(
                product=product,
                name_tokens=set(name_words),
                all_tokens=all_tokens,
                phrases={name_phrase, *filter(None, tags)},
                name_phrase=name_phrase,
                subcategory_tokens=set(subcategory),
                size=parse_size(product.unit_label),
            )
            index = len(self.docs)
            self.docs.append(doc)
            for token in all_tokens:
                self.vocab.setdefault(token, set()).add(index)
        self.vocab_list = list(self.vocab)
        self._cache: dict[tuple, list[Match]] = {}

    @cached_property
    def _by_first_letter(self) -> dict[str, list[str]]:
        groups: dict[str, list[str]] = {}
        for token in self.vocab_list:
            groups.setdefault(token[0], []).append(token)
        return groups

    def _token_similarities(self, token: str) -> dict[str, float]:
        """How well a query word matches each vocabulary word: exact, prefix, or typo."""
        sims: dict[str, float] = {}
        if token in self.vocab:
            sims[token] = 100.0
        same_letter = self._by_first_letter.get(token[0], [])
        if len(token) >= 2:
            prefix_score = 88.0 if len(token) >= 3 else 72.0
            for word in same_letter:
                if word != token and word.startswith(token):
                    sims[word] = max(sims.get(word, 0.0), prefix_score)
        if len(token) >= 3 and same_letter:
            cutoff = 85 if len(token) <= 4 else 78
            for word, score, _ in process.extract(
                token, same_letter, scorer=fuzz.ratio, score_cutoff=cutoff, limit=6
            ):
                sims[word] = max(sims.get(word, 0.0), float(score))
        return sims

    def search(
        self,
        words: list[str],
        size: tuple[str, float] | None = None,
        in_stock: dict[int, bool] | None = None,
    ) -> list[Match]:
        """Products ranked by how well they match `words` (already normalized via words_of)."""
        if not words:
            return []
        key = (tuple(words), size)
        if key in self._cache:
            matches = self._cache[key]
        else:
            matches = self._score(words, size)
            self._cache[key] = matches
        if in_stock is None:
            return matches
        # Among good matches, prefer something the shopper can actually buy when scores are close.
        return sorted(
            matches,
            key=lambda m: (
                m.score < MATCH_THRESHOLD,
                -(m.score + (6 if in_stock.get(m.product.id) else 0)),
                -m.product.popularity,
            ),
        )

    def _score(self, words: list[str], size: tuple[str, float] | None) -> list[Match]:
        query_phrase = " ".join(words)
        sims_per_word = [self._token_similarities(w) for w in words]
        candidates: set[int] = set()
        for sims in sims_per_word:
            for word in sims:
                candidates.update(self.vocab[word])

        results: list[Match] = []
        for index in candidates:
            doc = self.docs[index]
            total = 0.0
            name_hits = 0
            for sims in sims_per_word:
                best_any = max((s for w, s in sims.items() if w in doc.all_tokens), default=0.0)
                best_name = max((s for w, s in sims.items() if w in doc.name_tokens), default=0.0)
                total += best_any
                if best_name and best_name >= best_any:
                    name_hits += 1
            coverage = total / len(words)
            if coverage < 35:
                continue
            phrase = max(
                fuzz.token_set_ratio(query_phrase, doc.name_phrase),
                max(fuzz.ratio(query_phrase, p) for p in doc.phrases),
            )
            score = 0.7 * coverage + 0.3 * phrase
            if query_phrase in doc.phrases:
                score += 15  # exact name or synonym ("doodh" -> milk)
            if name_hits == len(words):
                score += 8
            if set(words) <= doc.subcategory_tokens:
                score += 6  # "bread" -> the Bread subcategory, not "Garlic Bread Spread"
            if size and doc.size == size:
                score += 10
            results.append(Match(doc.product, round(score, 1)))

        results.sort(key=lambda m: (-m.score, -m.product.popularity, m.product.id))
        return results

    def best_score(self, words: list[str]) -> float:
        matches = self.search(words)
        return matches[0].score if matches else 0.0

    # ---- shopping lists -------------------------------------------------------------------

    def split_unpunctuated(self, words: list[str]) -> list[tuple[int, int]]:
        """Best split of a phrase into consecutive product phrases (dynamic programming).
        Returns (start, end) index pairs into `words`."""
        n = len(words)
        if n <= 1 or self.best_score(words) >= STRONG_MATCH:
            return [(0, n)]

        best: list[tuple[float, list[tuple[int, int]]]] = [(0.0, [])] * (n + 1)
        for i in range(n - 1, -1, -1):
            options = []
            for j in range(i + 1, min(n, i + MAX_SPAN) + 1):
                score = self.best_score(words[i:j])
                value = score * (j - i) if score >= MATCH_THRESHOLD else 0.0
                rest_value, rest = best[j]
                options.append((value + rest_value - SPAN_PENALTY, [(i, j), *rest]))
            best[i] = max(options, key=lambda option: option[0])

        # Glue neighbouring unmatched words back together ("organic foo bar" stays one query).
        merged: list[tuple[int, int]] = []
        for start, end in best[0][1]:
            unmatched = self.best_score(words[start:end]) < MATCH_THRESHOLD
            if unmatched and merged and self.best_score(words[slice(*merged[-1])]) < MATCH_THRESHOLD:
                merged[-1] = (merged[-1][0], end)
            else:
                merged.append((start, end))
        return merged

    def parse_list(self, text: str, in_stock: dict[int, bool] | None = None) -> list[ListLine]:
        lines: list[ListLine] = []
        for chunk in _SPLIT_RE.split(text):
            for request in parse_chunk(chunk):
                spans = self.split_unpunctuated(request.words)
                for i, (start, end) in enumerate(spans):
                    owns_quantity = (i == len(spans) - 1) if request.trailing_quantity else i == 0
                    size = request.size if owns_quantity else None
                    pieces = request.quantity if owns_quantity and request.explicit_quantity else None
                    if size is None and pieces:
                        size = ("pc", float(pieces))  # "30 eggs" prefers the 30-piece tray
                    words = request.words[start:end]
                    lines.append(
                        ListLine(
                            query=" ".join(request.display[start:end]),
                            quantity=request.quantity if owns_quantity else 1,
                            matches=self.search(words, size, in_stock),
                            pieces=pieces,
                        )
                    )
        return lines


def _classify(tokens: list[str]) -> list[tuple[str, object]]:
    """Labels raw tokens as ("count", n), ("size", (unit, amount)) or ("word", (word, original))."""
    out: list[tuple[str, object]] = []
    i = 0
    while i < len(tokens):
        token = tokens[i]
        nxt = tokens[i + 1] if i + 1 < len(tokens) else None
        if _NUMBER_RE.match(token):
            amount = float(token)
            if nxt in SIZE_UNITS:
                base, factor = SIZE_UNITS[nxt]
                out.append(("size", (base, amount * factor)))
                i += 2
                continue
            out.append(("count", max(1, int(amount))))
            i += 2 if nxt in COUNT_UNITS else 1
            continue
        attached = _ATTACHED_RE.match(token)
        if attached and attached.group(2) in SIZE_UNITS:
            base, factor = SIZE_UNITS[attached.group(2)]
            out.append(("size", (base, float(attached.group(1)) * factor)))
        elif attached and attached.group(2) in COUNT_UNITS:
            out.append(("count", max(1, int(float(attached.group(1))))))
        elif _X_COUNT_RE.match(token):
            out.append(("count", max(1, int(token[1:]))))
        elif token in NUMBER_WORDS and nxt is not None and nxt not in SIZE_UNITS:
            out.append(("count", NUMBER_WORDS[token]))
        elif token in NUMBER_WORDS and nxt in SIZE_UNITS:
            base, factor = SIZE_UNITS[nxt]
            out.append(("size", (base, NUMBER_WORDS[token] * factor)))
            i += 1
        elif token not in STOPWORDS and token not in COUNT_UNITS:
            out.append(("word", (singular(token), token)))
        i += 1
    return out


def parse_chunk(chunk: str) -> list[ParsedRequest]:
    """Splits one chunk into requests, attaching each quantity/size to the right words.

    A number before words starts a new item ("2 milk 3 bread"); a number with no words after it
    belongs to the item before it ("milk 2", "sugar 1kg")."""
    tokens = _classify(normalize(chunk).split())
    requests: list[ParsedRequest] = []
    current = ParsedRequest(words=[])
    closed = False  # a trailing quantity/size was attached; the next word starts a new item

    for index, (kind, value) in enumerate(tokens):
        if kind == "word":
            if closed:
                requests.append(current)
                current, closed = ParsedRequest(words=[]), False
            word, original = value
            current.words.append(word)
            current.display.append(original)
            continue
        words_follow = any(k == "word" for k, _ in tokens[index + 1 :])
        if current.words and words_follow:
            requests.append(current)
            current, closed = ParsedRequest(words=[]), False
        if kind == "count" and not current.explicit_quantity:
            current.quantity = min(int(value), 50)
            current.explicit_quantity = True
            current.trailing_quantity = bool(current.words)
        elif kind == "size" and current.size is None:
            current.size = value
        if current.words:
            closed = True
    if current.words:
        requests.append(current)
    return requests


def walking_route(locations: list[tuple[int, int]]) -> list[int]:
    """Order in which to visit (aisle, row) spots, as indexes into `locations`.

    Snakes through only the aisles that are needed: from the entrance (row 1) up the first aisle,
    back down the next one, and so on, so the shopper never doubles back."""
    aisles = sorted({aisle for aisle, _ in locations})
    upward = {aisle: k % 2 == 0 for k, aisle in enumerate(aisles)}

    def key(index: int) -> tuple[int, int]:
        aisle, row = locations[index]
        return aisle, row if upward[aisle] else -row

    return sorted(range(len(locations)), key=key)
