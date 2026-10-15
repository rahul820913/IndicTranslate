"""Clean an aligned parallel corpus and split it into train/valid/test JSONL.

Usage:
  python prepare_data.py --src en.txt --tgt hi.txt --out ../data/en-hi
Each line of --src must align with the same line of --tgt.
"""
import argparse
import hashlib
import json
import pathlib


def norm(s: str) -> str:
    return " ".join(s.split())


def bucket(src: str) -> int:
    # Deterministic split keyed on the SOURCE sentence, so duplicates can never straddle train/test.
    return int(hashlib.md5(src.encode()).hexdigest(), 16) % 100


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--tgt", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--max-words", type=int, default=100)
    ap.add_argument("--valid-pct", type=int, default=5)
    ap.add_argument("--test-pct", type=int, default=5)
    a = ap.parse_args()

    src_lines = pathlib.Path(a.src).read_text(encoding="utf-8").splitlines()
    tgt_lines = pathlib.Path(a.tgt).read_text(encoding="utf-8").splitlines()
    assert len(src_lines) == len(tgt_lines), "Source and target files must have equal line counts"

    seen, rows = set(), []
    for s, t in zip(src_lines, tgt_lines):
        s, t = norm(s), norm(t)
        if not s or not t or len(s.split()) > a.max_words or len(t.split()) > a.max_words:
            continue
        if s in seen:
            continue
        seen.add(s)
        rows.append({"src": s, "tgt": t})

    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    splits = {"train": [], "valid": [], "test": []}
    for r in rows:
        b = bucket(r["src"])
        name = "test" if b < a.test_pct else "valid" if b < a.test_pct + a.valid_pct else "train"
        splits[name].append(r)
    for name, items in splits.items():
        with open(out / f"{name}.jsonl", "w", encoding="utf-8") as f:
            for r in items:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        print(name, len(items))


if __name__ == "__main__":
    main()
