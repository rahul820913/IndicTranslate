import re
import threading
from functools import lru_cache

from ..core.config import settings

ENG = "eng_Latn"

# FLORES-style codes used by IndicTrans2
LANGUAGES: dict[str, str] = {
    "eng_Latn": "English",
    "hin_Deva": "Hindi",
    "ben_Beng": "Bengali",
    "tam_Taml": "Tamil",
    "tel_Telu": "Telugu",
    "mar_Deva": "Marathi",
    "guj_Gujr": "Gujarati",
    "kan_Knda": "Kannada",
    "mal_Mlym": "Malayalam",
    "pan_Guru": "Punjabi",
    "ory_Orya": "Odia",
    "asm_Beng": "Assamese",
    "urd_Arab": "Urdu",
}


def validate_pair(src: str, tgt: str) -> None:
    if src not in LANGUAGES or tgt not in LANGUAGES:
        raise ValueError("Unsupported language code.")
    if src == tgt:
        raise ValueError("Source and target languages must differ.")
    if ENG not in (src, tgt):
        raise ValueError("Translate to or from English (Indic-to-Indic is not enabled).")


_SPLIT = re.compile(r"(?<=[.!?।])\s+|\n+")


def split_sentences(text: str) -> list[str]:
    return [s.strip() for s in _SPLIT.split(text) if s and s.strip()]


class MockTranslator:
    """Lets you build and test the whole stack without downloading a model."""

    def load(self) -> None:
        pass

    def translate(self, text: str, src: str, tgt: str) -> str:
        return f"[{tgt}] {text}"


class IndicTrans2Translator:
    """Loads each direction once at startup; generation is serialised with a lock."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._models: dict[str, tuple] = {}
        self._processor = None
        self._device = "cpu"

    def load(self) -> None:
        import torch
        from IndicTransToolkit.processor import IndicProcessor
        from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

        if settings.device == "auto":
            self._device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self._device = settings.device
        dtype = torch.float16 if self._device == "cuda" else torch.float32
        self._processor = IndicProcessor(inference=True)
        for name, ckpt in (
            ("en-indic", settings.model_en_indic),
            ("indic-en", settings.model_indic_en),
        ):
            tok = AutoTokenizer.from_pretrained(ckpt, trust_remote_code=True)
            model = AutoModelForSeq2SeqLM.from_pretrained(
                ckpt, trust_remote_code=True, torch_dtype=dtype
            )
            self._models[name] = (tok, model.to(self._device).eval())

    def translate(self, text: str, src: str, tgt: str) -> str:
        import torch

        tok, model = self._models["en-indic" if src == ENG else "indic-en"]
        sentences = split_sentences(text)
        batch = self._processor.preprocess_batch(sentences, src_lang=src, tgt_lang=tgt)
        inputs = tok(
            batch, truncation=True, padding="longest", return_tensors="pt", return_attention_mask=True
        ).to(self._device)
        with self._lock, torch.no_grad():
            out = model.generate(
                **inputs, use_cache=False, min_length=0, max_length=256, num_beams=5, num_return_sequences=1
            )
        decoded = tok.batch_decode(
            out.detach().cpu().tolist(), skip_special_tokens=True, clean_up_tokenization_spaces=True
        )
        return " ".join(self._processor.postprocess_batch(decoded, lang=tgt))


@lru_cache(maxsize=1)
def get_translator():
    return IndicTrans2Translator() if settings.translator_backend == "indictrans2" else MockTranslator()
