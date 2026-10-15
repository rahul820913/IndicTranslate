# IndicTranslate

English <-> Indian-language translation platform: React + TypeScript, FastAPI, IndicTrans2, PostgreSQL, Redis, Docker.

## Run it (no model download: mock translator)
```bash
docker compose up --build
# app: http://localhost:8080   API docs: http://localhost:8000/docs
```

## Run locally without Docker
```bash
cd backend && python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload   # uses SQLite + in-memory cache by default; http://localhost:8000/docs
pytest -q                       # run tests

cd ../frontend && npm install && npm run dev   # http://localhost:5173
```
To use PostgreSQL/Redis locally, copy `backend/.env.example` to `backend/.env`.

## Use the real IndicTrans2 model
```bash
pip install -r backend/requirements-ml.txt
export TRANSLATOR_BACKEND=indictrans2           # first start downloads the checkpoints
```
For Docker: set `INSTALL_ML: "true"` in docker-compose.yml and `TRANSLATOR_BACKEND=indictrans2`.
Check the model card for hardware needs before choosing a checkpoint.

## ML experiment (one language pair, e.g. English -> Hindi)
```bash
cd ml && pip install -r requirements.txt
python preprocessing/prepare_data.py --src data/en.txt --tgt data/hi.txt --out data/en-hi
python evaluation/evaluate.py --ckpt ai4bharat/indictrans2-en-indic-dist-200M --test data/en-hi/test.jsonl --src eng_Latn --tgt hin_Deva --out results/baseline
python training/finetune.py --ckpt ai4bharat/indictrans2-en-indic-dist-200M --data data/en-hi --src eng_Latn --tgt hin_Deva --out checkpoints/en-hi-ft
python evaluation/evaluate.py --ckpt checkpoints/en-hi-ft --test data/en-hi/test.jsonl --src eng_Latn --tgt hin_Deva --out results/finetuned
```
Fill in the table below with the numbers you actually measure.

| Metric | Baseline | Fine-tuned |
|---|---|---|
| BLEU | | |
| chrF++ | | |
| Avg latency (ms/sentence) | | |
