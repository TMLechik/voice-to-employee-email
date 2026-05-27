from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Protocol

import pymorphy3
from rapidfuzz import fuzz


class RecipientLike(Protocol):
    id: int
    username: str | None
    full_name: str


@dataclass(frozen=True)
class RecipientCandidate:
    recipient: RecipientLike
    score: float
    matched_value: str
    matched_kind: str


@dataclass(frozen=True)
class RecipientMatchResult:
    status: str
    recipient: RecipientLike | None
    candidates: list[RecipientCandidate]

    @property
    def is_exact(self) -> bool:
        return self.status == "exact"

    @property
    def is_confident(self) -> bool:
        return self.status == "confident"

    @property
    def is_ambiguous(self) -> bool:
        return self.status == "ambiguous"

    @property
    def is_not_found(self) -> bool:
        return self.status == "not_found"


class RecipientMatcher:
    def __init__(
        self,
        confident_score: float = 92.0,
        ambiguous_score: float = 80.0,
        min_gap: float = 8.0,
    ) -> None:
        self.confident_score = confident_score
        self.ambiguous_score = ambiguous_score
        self.min_gap = min_gap
        self.morph = pymorphy3.MorphAnalyzer()

    def match(
        self,
        query: str,
        recipients: list[RecipientLike],
        aliases_by_recipient_id: dict[int, list[str]] | None = None,
    ) -> RecipientMatchResult:
        aliases_by_recipient_id = aliases_by_recipient_id or {}

        query_keys = self._make_search_keys(query)
        search_items = self._build_search_items(recipients, aliases_by_recipient_id)

        exact_candidate = self._find_exact_match(query_keys, search_items)
        if exact_candidate is not None:
            return RecipientMatchResult(
                status="exact",
                recipient=exact_candidate.recipient,
                candidates=[exact_candidate],
            )

        candidates = self._find_fuzzy_matches(query_keys, search_items)
        if not candidates:
            return RecipientMatchResult(
                status="not_found",
                recipient=None,
                candidates=[],
            )

        best = candidates[0]
        second = candidates[1] if len(candidates) > 1 else None

        if best.score < self.ambiguous_score:
            return RecipientMatchResult(
                status="not_found",
                recipient=None,
                candidates=candidates[:3],
            )

        has_safe_gap = second is None or best.score - second.score >= self.min_gap

        if best.score >= self.confident_score and has_safe_gap:
            return RecipientMatchResult(
                status="confident",
                recipient=best.recipient,
                candidates=candidates[:3],
            )

        return RecipientMatchResult(
            status="ambiguous",
            recipient=None,
            candidates=candidates[:3],
        )

    def _build_search_items(
        self,
        recipients: list[RecipientLike],
        aliases_by_recipient_id: dict[int, list[str]],
    ) -> list[tuple[RecipientLike, str, str, set[str]]]:
        items: list[tuple[RecipientLike, str, str, set[str]]] = []

        for recipient in recipients:
            values = [recipient.full_name]

            if recipient.username:
                values.append(recipient.username)
                values.append(f"@{recipient.username}")

            values.extend(aliases_by_recipient_id.get(recipient.id, []))

            for value in values:
                keys = self._make_search_keys(value)
                if keys:
                    kind = "alias" if value != recipient.full_name else "full_name"
                    items.append((recipient, value, kind, keys))

        return items

    def _find_exact_match(
        self,
        query_keys: set[str],
        search_items: list[tuple[RecipientLike, str, str, set[str]]],
    ) -> RecipientCandidate | None:
        for recipient, value, kind, item_keys in search_items:
            if query_keys & item_keys:
                return RecipientCandidate(
                    recipient=recipient,
                    score=100.0,
                    matched_value=value,
                    matched_kind=kind,
                )

        return None

    def _find_fuzzy_matches(
        self,
        query_keys: set[str],
        search_items: list[tuple[RecipientLike, str, str, set[str]]],
    ) -> list[RecipientCandidate]:
        best_by_recipient_id: dict[int, RecipientCandidate] = {}

        for recipient, value, kind, item_keys in search_items:
            score = self._max_token_sort_score(query_keys, item_keys)

            current = best_by_recipient_id.get(recipient.id)
            if current is None or score > current.score:
                best_by_recipient_id[recipient.id] = RecipientCandidate(
                    recipient=recipient,
                    score=score,
                    matched_value=value,
                    matched_kind=kind,
                )

        return sorted(
            best_by_recipient_id.values(),
            key=lambda candidate: candidate.score,
            reverse=True,
        )

    def _max_token_sort_score(self, left_keys: set[str], right_keys: set[str]) -> float:
        best_score = 0.0

        for left in left_keys:
            for right in right_keys:
                score = fuzz.token_sort_ratio(left, right)
                best_score = max(best_score, float(score))

        return best_score

    def _make_search_keys(self, value: str) -> set[str]:
        cleaned = self._clean(value)

        if not cleaned:
            return set()

        keys = {cleaned}

        lemmatized = self._lemmatize(cleaned)
        if lemmatized:
            keys.add(lemmatized)

        without_username_symbol = cleaned.lstrip("@")
        if without_username_symbol:
            keys.add(without_username_symbol)

        return keys

    def _clean(self, value: str) -> str:
        value = value.lower().replace("ё", "е")
        value = re.sub(r"[^а-яa-z0-9@._\-\s]", " ", value)
        return " ".join(value.split())

    def _lemmatize(self, value: str) -> str:
        words = value.split()
        normalized_words: list[str] = []

        for word in words:
            if word.startswith("@"):
                normalized_words.append(word)
                continue

            parsed = self.morph.parse(word)
            if parsed:
                normalized_words.append(parsed[0].normal_form)
            else:
                normalized_words.append(word)

        return " ".join(normalized_words)


RecipientMathcer = RecipientMatcher
