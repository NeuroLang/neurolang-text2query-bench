"""Max bge-m3 cosine of the new bank questions to every question of the datasets."""
import sys
sys.path.insert(0, "/Users/bot/neurolang-text2query-bench/scripts")
from leakage import embed, OPENROUTER
from text2query_bench.dataset import load_dataset
new = sys.argv[1].split("|")
texts = []
for d in sys.argv[2:]:
    texts += [(q.id, t) for q in load_dataset(d).questions for t in q.text.values()]
where = dict(model="baai/bge-m3", base_url=OPENROUTER, key_env="OPENROUTER_API_KEY")
sim = embed(new, **where) @ embed([t for _, t in texts], **where).T
for q, row in zip(new, sim):
    i = row.argmax(); print(f"{row[i]:.3f} {q}\n      ~ {texts[i][0]} {texts[i][1]}")
