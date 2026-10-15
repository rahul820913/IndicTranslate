"""Standalone IndicTrans2 inference, used by evaluation (no web app needed)."""
import torch
from IndicTransToolkit.processor import IndicProcessor
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"


def load(checkpoint: str):
    tok = AutoTokenizer.from_pretrained(checkpoint, trust_remote_code=True)
    dtype = torch.float16 if DEVICE == "cuda" else torch.float32
    model = AutoModelForSeq2SeqLM.from_pretrained(checkpoint, trust_remote_code=True, torch_dtype=dtype)
    return tok, model.to(DEVICE).eval(), IndicProcessor(inference=True)


def translate_batch(tok, model, ip, sentences, src_lang, tgt_lang, num_beams=5, max_length=256):
    batch = ip.preprocess_batch(sentences, src_lang=src_lang, tgt_lang=tgt_lang)
    inputs = tok(batch, truncation=True, padding="longest", return_tensors="pt", return_attention_mask=True).to(DEVICE)
    with torch.no_grad():
        out = model.generate(**inputs, use_cache=True, min_length=0, max_length=max_length,
                             num_beams=num_beams, num_return_sequences=1)
    decoded = tok.batch_decode(out.detach().cpu().tolist(), skip_special_tokens=True,
                               clean_up_tokenization_spaces=True)
    return ip.postprocess_batch(decoded, lang=tgt_lang)
