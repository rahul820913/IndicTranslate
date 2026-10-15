"""Fine-tune an IndicTrans2 checkpoint on one language pair.

NOTE: untested scaffold. IndicTransToolkit / transformers APIs shift between versions; check this
against the IndicTrans2 repo's fine-tuning notes for the versions you pin.

  python finetune.py --ckpt ai4bharat/indictrans2-en-indic-dist-200M --data ../data/en-hi \
      --src eng_Latn --tgt hin_Deva --out ../checkpoints/en-hi-ft
"""
import argparse
import json

import torch
from datasets import Dataset
from IndicTransToolkit.processor import IndicProcessor
from transformers import (
    AutoModelForSeq2SeqLM,
    AutoTokenizer,
    DataCollatorForSeq2Seq,
    EarlyStoppingCallback,
    Seq2SeqTrainer,
    Seq2SeqTrainingArguments,
    set_seed,
)


def read(path):
    return Dataset.from_list([json.loads(l) for l in open(path, encoding="utf-8")])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ckpt", required=True)
    ap.add_argument("--data", required=True)
    ap.add_argument("--src", required=True)
    ap.add_argument("--tgt", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--lr", type=float, default=3e-5)
    ap.add_argument("--epochs", type=int, default=3)
    ap.add_argument("--batch-size", type=int, default=16)
    ap.add_argument("--max-len", type=int, default=128)
    ap.add_argument("--max-train", type=int, default=50000)
    ap.add_argument("--seed", type=int, default=42)
    a = ap.parse_args()
    set_seed(a.seed)

    tok = AutoTokenizer.from_pretrained(a.ckpt, trust_remote_code=True)
    model = AutoModelForSeq2SeqLM.from_pretrained(a.ckpt, trust_remote_code=True)
    ip = IndicProcessor(inference=True)  # adds the language tags the model expects on the source side

    def encode(batch):
        srcs = ip.preprocess_batch(batch["src"], src_lang=a.src, tgt_lang=a.tgt)
        enc = tok(srcs, truncation=True, max_length=a.max_len)
        enc["labels"] = tok(text_target=batch["tgt"], truncation=True, max_length=a.max_len)["input_ids"]
        return enc

    train = read(f"{a.data}/train.jsonl")
    train = train.select(range(min(a.max_train, len(train))))
    valid = read(f"{a.data}/valid.jsonl")
    train = train.map(encode, batched=True, remove_columns=["src", "tgt"])
    valid = valid.map(encode, batched=True, remove_columns=["src", "tgt"])

    args = Seq2SeqTrainingArguments(
        output_dir=a.out,
        learning_rate=a.lr,
        per_device_train_batch_size=a.batch_size,
        per_device_eval_batch_size=a.batch_size,
        num_train_epochs=a.epochs,
        eval_strategy="epoch",
        save_strategy="epoch",
        save_total_limit=2,
        load_best_model_at_end=True,
        metric_for_best_model="eval_loss",
        greater_is_better=False,
        fp16=torch.cuda.is_available(),
        seed=a.seed,
        logging_steps=50,
        report_to="none",
    )
    trainer = Seq2SeqTrainer(
        model=model,
        args=args,
        train_dataset=train,
        eval_dataset=valid,
        data_collator=DataCollatorForSeq2Seq(tok, model=model),
        callbacks=[EarlyStoppingCallback(early_stopping_patience=2)],
    )
    trainer.train()
    trainer.save_model(a.out)
    tok.save_pretrained(a.out)
    json.dump(vars(a), open(f"{a.out}/train_config.json", "w"), indent=2)  # reproducibility record


if __name__ == "__main__":
    main()
