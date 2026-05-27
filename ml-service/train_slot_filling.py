from __future__ import annotations

import json
from pathlib import Path
from datasets import Dataset

from transformers import (
    AutoModelForTokenClassification,
    AutoTokenizer,
    DataCollatorForTokenClassification,
    Trainer,
    TrainingArguments,
)

MODEL_NAME = "cointegrated/rubert-tiny2"
DATA_PATH = Path(__file__).parent / "data" / "slot_filling_train.jsonl"
OUTPUT_DIR = Path(__file__).parent / "models" / "rubert-slot-filling"

LABELS = ["O", "B-RECIPIENT", "I-RECIPIENT", "B-MESSAGE", "I-MESSAGE"]
LABEL_TO_ID = {label: index for index,label in enumerate(LABELS)}
ID_TO_LABEL = {index: label for index, label in enumerate(LABELS)}

def load_jsonl(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as file:
        return [json.loads(line) for line in file if line.strip()]
    
def split_examples(examples: list[dict]) -> tuple[list[dict], list[dict]]:
    split_index = max(1, int(len(examples) * 0.8))
    return examples[:split_index], examples[split_index:]

def label_for_token(
        token_start: int,
        token_end: int,
        entities: list[dict],
) -> str:
    for entity in entities:
        start = int(entity["start"])
        end = int(entity["end"])
        label = str(entity["label"])

        if token_start >= start and token_end <= end:
            prefix = "B" if token_start == start else "I"
            return f"{prefix}-{label}"
        
    return "O"

def tokenize_and_align_labels(examples: dict, tokenizer):
    tokenized = tokenizer(
        examples["text"],
        truncation=True,
        padding=False,
        return_offsets_mapping=True,
    )

    all_labels: list[list[int]] = []

    for index,offsets in enumerate(tokenized["offset_mapping"]):
        entities = examples["entities"][index]
        labels: list[int] = []

        for token_start, token_end in offsets:
            if token_start == token_end:
                labels.append(-100)
                continue

            label = label_for_token(token_start, token_end,entities)
            labels.append(LABEL_TO_ID[label])
        
        all_labels.append(labels)

    tokenized["labels"] = all_labels
    tokenized.pop("offset_mapping")
    return tokenized

def main() -> None:
    examples = load_jsonl(DATA_PATH)
    train_examples, eval_examples = split_examples(examples)
    
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)

    train_dataset = Dataset.from_list(train_examples).map(
        lambda batch: tokenize_and_align_labels(batch,tokenizer),
        batched= True,
        remove_columns=["text", "entities"],
    )

    eval_dataset = Dataset.from_list(eval_examples).map(
        lambda batch: tokenize_and_align_labels(batch, tokenizer),
        batched=True,
        remove_columns=["text", "entities"],
    )

    model = AutoModelForTokenClassification.from_pretrained(
        MODEL_NAME,
        num_labels=len(LABELS),
        id2label=ID_TO_LABEL,
        label2id=LABEL_TO_ID,
    )

    args = TrainingArguments(
        output_dir=str(OUTPUT_DIR),
        learning_rate=3e-5,
        per_device_eval_batch_size=8,
        per_device_train_batch_size=8,
        num_train_epochs=10,
        weight_decay=0.01,
        eval_strategy="epoch",
        save_strategy="epoch",
        logging_steps=10,
        load_best_model_at_end=True,
    )

    trainer = Trainer(
        model=model,
        args=args,
        train_dataset=train_dataset,
        eval_dataset=eval_dataset,
        data_collator=DataCollatorForTokenClassification(tokenizer),
    )

    trainer.train()
    trainer.save_model(str(OUTPUT_DIR))
    tokenizer.save_pretrained(str(OUTPUT_DIR))

if __name__ == "__main__":
    main()