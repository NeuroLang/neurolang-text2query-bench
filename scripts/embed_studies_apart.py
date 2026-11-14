"""
Embed an engine's study abstracts in a process of their own.

Building the NeuroStore engine takes most of a 64 GB machine, and SPECTER2
then crawls in swapped memory.  ``dump`` builds the engine and saves the
ids and texts of its ``study_abstracts`` index; ``embed`` embeds them
without the engine and writes the index's cache, which the engine reads
afterwards (same ids, same encoder, same cache key).  On an Intel Mac's
CPU it embeds about 900 abstracts a minute (64,920 for NeuroStore); a
Turing GPU on Margaret does them in 11 minutes, with
``python -m neurolang_apps.utils.text_embeddings -e neurostore``.

    python scripts/embed_studies_apart.py dump --engine neurostore
    python scripts/embed_studies_apart.py embed
"""
import argparse
import logging
import pickle
import time
from pathlib import Path


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("stage", choices=["dump", "embed"])
    p.add_argument("--engine", default="neurostore")
    p.add_argument("--data-dir", default="neurolang_data")
    p.add_argument("--dump", default="/tmp/study_texts.pkl")
    args = p.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    from neurolang_apps.utils import text_embeddings

    if args.stage == "dump":
        from neurolang_apps.utils import engine_registry

        nl = engine_registry.build_engine(args.engine, Path(args.data_dir))
        index = nl.text_embedding_indexes["study_abstracts"]
        enc = index.encoder
        texts = index._load_texts([str(d) for d in index.ids])
        with open(args.dump, "wb") as f:
            pickle.dump({"ids": index.ids, "texts": texts,
                         "cache_path": index.cache_path,
                         "encoder": enc}, f)
        print(f"{len(index.ids)} studies, key {index.cache_key}")
        return
    with open(args.dump, "rb") as f:
        d = pickle.load(f)
    index = text_embeddings.EmbeddingIndex(
        d["ids"], lambda keys: d["texts"], d["encoder"], d["cache_path"])
    print(f"{len(index.ids)} studies, key {index.cache_key}")
    start = time.perf_counter()
    m = index.build()
    print(f"embedded {m.shape} in {time.perf_counter() - start:.0f}s "
          f"-> {index.cache_path}")


if __name__ == "__main__":
    main()
