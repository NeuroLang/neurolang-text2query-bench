"""
Check that the questions of a dataset are far from the example bank.

Each question of the dataset, in each of its languages, is embedded
with bge-m3 on Albert (``/embeddings``, at most 64 texts a request), as
are the questions of the assistant's example banks of the engine. The
script prints, per question, its highest cosine similarity to a bank
question and that question, and fails when one is above ``--max``.

    source scripts/env.sh
    python scripts/leakage.py datasets/neurosynth-v2.yaml
"""

import argparse
import os
import sys

import httpx
import numpy as np

from text2query_bench.dataset import load_dataset

ALBERT = "https://albert.api.etalab.gouv.fr/v1"


def embed(texts, model="bge-m3", batch=64):
    """Return the L2-normalised bge-m3 embeddings of *texts*."""
    headers = {"Authorization": f"Bearer {os.environ['ALBERT_API_KEY']}"}
    vectors = []
    with httpx.Client(timeout=120) as client:
        for start in range(0, len(texts), batch):
            response = client.post(
                f"{ALBERT}/embeddings", headers=headers,
                json={"model": model, "input": texts[start:start + batch]},
            )
            response.raise_for_status()
            data = sorted(response.json()["data"], key=lambda d: d["index"])
            vectors += [d["embedding"] for d in data]
    matrix = np.array(vectors, dtype=float)
    return matrix / np.linalg.norm(matrix, axis=1, keepdims=True)


def bank_questions(engine):
    """Return the questions of the example banks of *engine*."""
    from neurolang_apps.utils.llm.examples import load_examples

    return [e.question for e in load_examples(engine) if e.question]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("dataset")
    parser.add_argument("--max", type=float, default=0.85)
    args = parser.parse_args()
    dataset = load_dataset(args.dataset)
    bank = bank_questions(dataset.engine)
    texts = [
        (q.id, lang, text) for q in dataset.questions
        for lang, text in q.text.items()
    ]
    similarity = embed([t for _, _, t in texts]) @ embed(bank).T
    worst = 0.0
    for (qid, lang, text), row in zip(texts, similarity):
        best = int(row.argmax())
        worst = max(worst, row[best])
        flag = "  TOO CLOSE" if row[best] > args.max else ""
        print(f"{row[best]:.3f} {qid} [{lang}] {text}\n"
              f"      ~ {bank[best]}{flag}")
    print(f"\nmax cosine to the bank ({len(bank)} questions): {worst:.3f}")
    return 1 if worst > args.max else 0


if __name__ == "__main__":
    sys.exit(main())
