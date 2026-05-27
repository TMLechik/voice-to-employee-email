from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import torch
from transformers import AutoModelForTokenClassification, AutoTokenizer

@dataclass(frozen=True)
class SlotFillingResult:
    recipient: str | None
    message: str | None

class RuBertSlotFillingService:
    def __init__(self, model_path: Path) -> None:
        self.tokenizer = AutoTokenizer.from_pretrained(str(model_path))
        self.model = AutoModelForTokenClassification.from_pretrained(str(model_path))
        self.model.eval()

    def _join_spans(self, text: str, spans: list[tuple[int,int]]) -> str | None:
        if not spans:
            return None
        
        start = min(span[0] for span in spans)
        end = max(span[1] for span in spans)
        value = text[start:end].strip(" ,.:;!?")
        return value or None

    def extract(self, text: str) -> SlotFillingResult:
        encoded = self.tokenizer(
            text,
            return_tensors="pt",
            return_offsets_mapping=True,
            truncation=True,
        )

        offsets = encoded.pop("offset_mapping")[0].tolist()

        with torch.no_grad():
            output = self.model(**encoded)

        label_ids = output.logits.argmax(dim=-1)[0].tolist()

        spans: dict[str, list[tuple[int,int]]] = {
            "RECIPIENT": [],
            "MESSAGE": [],
        }

        for label_id, (start, end) in zip(label_ids, offsets, strict=False):
            if start == end:
                continue

            label = self.model.config.id2label[int(label_id)]
            if label == "O":
                continue

            _, slot_name = label.split("-", maxsplit=1)
            if slot_name in spans:
                spans[slot_name].append((start,end))

        return SlotFillingResult(
            recipient=self._join_spans(text, spans["RECIPIENT"]),
            message=self._join_spans(text, spans["MESSAGE"]),
        )
