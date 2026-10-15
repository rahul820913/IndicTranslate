"""Score a checkpoint on the held-out test set: BLEU, chrF++, latency, and an error-analysis dump.

Run the SAME command for the baseline and the fine-tuned checkpoint, then compare results.json files:
  python evaluate.py --ckpt ai4bharat/indictrans2-en-indic-dist-200M --test ../data/en-hi/test.jsonl \
      --src eng_Latn --tgt hin_Deva --out ../results/baseline
  python evaluate.py --ckpt ../checkpoints/en-hi-ft --test ../data/en-hi/test.jsonl \
      --src eng_Latn --tgt hin_Deva --out ../results/finetuned
"""
import argparse
import json
import pathlib
import sys
import time

import sacrebleu
from sacrebleu.metrics import CHRF

sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))
from inference.indictrans import load, translate_batch  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ckpt", required=True)
    ap.add_argument("--test", required=True)
    ap.add_argument("--src", required=True)
    ap.add_argument("--tgt", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--batch-size", type=int, default=16)
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()

    rows = [json.loads(l) for l in open(a.test, encoding="utf-8")]
    if a.limit:
        rows = rows[: a.limit]
    sources, refs = [r["src"] for r in rows], [r["tgt"] for r in rows]

    tok, model, ip = load(a.ckpt)
    hyps, latencies = [], []
    for i in range(0, len(sources), a.batch_size):
        chunk = sources[i : i + a.batch_size]
        t0 = time.perf_counter()
        hyps.extend(translate_batch(tok, model, ip, chunk, a.src, a.tgt))
        latencies.append((time.perf_counter() - t0) / len(chunk))

    bleu = sacrebleu.corpus_bleu(hyps, [refs])
    chrf = CHRF(word_order=2).corpus_score(hyps, [refs])  # word_order=2 -> chrF++
    results = {
        "checkpoint": a.ckpt,
        "n_examples": len(rows),
        "bleu": round(bleu.score, 2),
        "chrf++": round(chrf.score, 2),
        "avg_latency_ms_per_sentence": round(1000 * sum(latencies) / len(latencies), 1),
    }
    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "results.json").write_text(json.dumps(results, indent=2))

    # Worst examples by sentence-level chrF++ to drive error analysis
    chrf_s = CHRF(word_order=2)
    scored = sorted(
        ({"src": s, "ref": r, "hyp": h, "chrf": chrf_s.sentence_score(h, [r]).score}
         for s, r, h in zip(sources, refs, hyps)),
        key=lambda x: x["chrf"],
    )
    (out / "worst_examples.json").write_text(json.dumps(scored[:50], ensure_ascii=False, indent=2))
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
