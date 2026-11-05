# NVIDIA Nemotron 3.5 Lightning as the ReAct model (2026-11-05)

Model `nvidia/nemotron-3.5-lightning` (OpenRouter, paid tier, 262k
context), provider `openrouter-nemotron-lightning` in `configs/llm*.yaml`.
Same setup as `runs/nsv2-distill.md`: config `configs/llm.master-v0.yaml`
(BM25, 6 examples, `verify_rounds: 0`, 8 steps), English, ReAct,
temperature 0, OpenRouter only. "before" = NeuroLang `f695d502` (bank of
46; worktree `/Users/bot/NeuroLang-distill-before`, reached through
`PYTHONPATH` over `.venv-distill`), "after" = `.venv-distill`
(`7c41d73f`, #1057 bank of 85). `scripts/run_nsv2_nemotron.sh` runs all six;
`scripts/run_cost.py` prices a run from the input/output tokens of its
traces. Runs: `runs/nsv2-{dev,test}-nemotron-{before,after}`,
`runs/distill-heldout-{before,after}-nemotron-or`.

**Tool calling: native** (3-question smoke run: tool calls well formed,
every call parsed, no fallback to text needed). **Thinking toggle:** not
tried. The assistant has no extra-request-parameter passthrough
(`ProviderConfig` has `headers`, `tool_calling`, `max_tokens`,
`requests_per_minute` only), so `chat_template_kwargs.enable_thinking`
and the recommended temperature 1.0 / top_p 0.95 (temperature is one
assistant-wide key, top_p does not exist) cannot be set without NeuroLang
code. Not added, as asked. The model emits visible reasoning in `thought`
by default.

## Results (single runs, English, before bank → after bank)

| split | model | mean J | exact | steps | tokens/q | s/q | cost/q |
|---|---|---|---|---:|---:|---:|---:|
| dev (20) | Nemotron Lightning | 0.450 → 0.450 | 9 → 9 | 7.0 → 6.6 | 57k → 54k | 39 → 52 | $0.0046 → $0.0046 |
| dev | Gemma 4 31B | 0.950 → 0.900 | 19 → 18 | 1.9 → 1.6 | 13k → 11k | 29 → 25 | $0.0027 → $0.0022 |
| dev | DeepSeek 0731 | 0.950 → 0.950 | 19 → 19 | 4.2 → 3.5 | 29k → 24k | 35 → 30 | $0.0019 → $0.0015 |
| dev | Sonnet 5.5 (master, verify 1) | 1.000 | 20 | 3.1 | 35k | 27 | $0.080 |
| test (21) | Nemotron Lightning | 0.285 → 0.284 | 5 → 5 | 7.0 → 6.5 | 57k → 50k | 31 → 38 | $0.0045 → $0.0041 |
| test | Gemma 4 31B | 0.952 → 0.903 | 20 → 18 | 2.0 → 1.7 | 14k → 11k | 23 → 23 | $0.0029 → $0.0023 |
| test | DeepSeek 0731 | 0.952 → 0.952 | 20 → 20 | 4.1 → 3.7 | 30k → 26k | 30 → 26 | $0.0021 → $0.0016 |
| test | Sonnet 5.5 (master, verify 1) | 1.000 | 21 | 2.8 | 34k | 25 | $0.076 |
| held-out (25) | Nemotron Lightning | 0.205 → 0.240 | 5 → 6 | 7.2 → 6.2 | 56k → 46k | 43 → 46 | $0.0044 → $0.0037 |
| held-out | Gemma 4 31B | 0.776 → 0.840 | 18 → 21 | 3.2 → 2.9 | 22k → 20k | 31 → 27 | n/a (no trace) |
| held-out | DeepSeek 0731 | 0.736 → 0.720 | 17 → 18 | 5.8 → 5.0 | 42k → 37k | 54 → 54 | n/a → $0.0031 |

Sonnet is the 2026-10-3x `nsv2-{dev,test}-master-sonnet` run (older
master, verifier on, hence its 2 calls per answer and cost); on the held-out
slice it is the gold (1.00 by construction). Cost = input x price in +
output x price out per million tokens, from the traces (no prompt-cache
discount): Nemotron $0.07/$0.20, Gemma $0.20/$0.40, DeepSeek 0731
$0.0434/$0.30, Sonnet $2/$10 (OpenRouter /models, 2026-11-05). Nemotron
sends 45-52k input tokens a question (6.1k per request over 7 requests)
against 10-12k for Gemma: it is the cheapest per token and the most
expensive per question of the three open models.

## Failures

Out of steps dominates: 10 + 12 of 41 questions before, 9 + 11 after,
and 14 of the 16 out-of-steps answers of the "after" runs never ran a
query: the 8 steps went to `search_values` (e.g. nsv2-10 and nsv2-17
looping over "intraparietal" / "Cont" in `schaefer`, `destrieux`, `tian`,
repeating the same call). The rest: no probability over
`selected_study` (nsv2-13, dh-029, -062, -087, -093), wrong predicate
(nsv2-31, -34, dh-015, -141), wrong structure (nsv2-15 0.97, -24, -33,
dh-122), wrong value (nsv2-26, dh-151). Early steps often reply with a
hallucinated answer in plain text ("The count is 10.") that the agent
rejects, costing 1-2 requests. The distilled bank changes nothing
measurable (dev/test identical, held-out 5 → 6 exact), with about 5%
fewer steps; the outcome flips in both directions (dev nsv2-04, -05,
-14, -18 gained, nsv2-07, -23, -25, -28 lost).

Per-question Jaccard overlap, after bank, rows with a miss (Nemotron
cause: out of steps unless stated):

| split | question | Nemotron |
|---|---|---|
| dev | nsv2-07 | 0.00 (1/32) out of steps |
| dev | nsv2-12 | 0.00 (1/1) out of steps |
| dev | nsv2-16 | 0.00 (0/4) out of steps |
| dev | nsv2-21 | 0.00 (0/78) out of steps |
| dev | nsv2-23 | 0.00 (0/1) out of steps |
| dev | nsv2-25 | 0.00 (0/719) out of steps |
| dev | nsv2-26 | 0.00 (1/1) wrong value |
| dev | nsv2-28 | 0.00 (719/3024) out of steps |
| dev | nsv2-32 | 0.00 (0/1) out of steps |
| dev | nsv2-35 | 0.00 (0/32) out of steps |
| dev | nsv2-36 | 0.00 (0/1) out of steps |
| test | nsv2-08 | 0.00 (0/565) out of steps |
| test | nsv2-10 | 0.00 (0/1) out of steps |
| test | nsv2-11 | 0.00 (0/148) out of steps |
| test | nsv2-13 | 0.00 (1/1) no choice |
| test | nsv2-15 | 0.97 (32/31) wrong structure |
| test | nsv2-19 | 0.00 (1/1) out of steps |
| test | nsv2-22 | 0.00 (0/100) out of steps |
| test | nsv2-24 | 0.00 (1/1) wrong structure |
| test | nsv2-27 | 0.00 (0/100) out of steps |
| test | nsv2-29 | 0.00 (0/1) out of steps |
| test | nsv2-31 | 0.00 (1/1) wrong predicate |
| test | nsv2-33 | 0.00 (22/21) wrong structure |
| test | nsv2-34 | 0.00 (1/1) wrong predicate |
| test | nsv2-37 | 0.00 (32/32) out of steps |
| test | nsv2-38 | 0.00 (0/1) out of steps |
| test | nsv2-40 | 0.00 (0/1) out of steps |
| held-out | dh-005 | 0.00 (0/32) out of steps |
| held-out | dh-141 | 0.00 (1/1) wrong predicate |
| held-out | dh-010 | 0.00 (0/1159907) out of steps |
| held-out | dh-052 | 0.00 (0/1) out of steps |
| held-out | dh-015 | 0.00 (148/148) wrong predicate |
| held-out | dh-067 | 0.00 (100/1) out of steps |
| held-out | dh-117 | 0.00 (0/1) out of steps |
| held-out | dh-020 | 0.00 (0/100) out of steps |
| held-out | dh-122 | 0.00 (1/1) wrong structure |
| held-out | dh-029 | 0.00 (223795/223795) no choice |
| held-out | dh-057 | 0.00 (0/313) out of steps |
| held-out | dh-093 | 0.00 (32/32) no choice |
| held-out | dh-127 | 0.00 (0/31) out of steps |
| held-out | dh-062 | 0.00 (4519/4519) no choice |
| held-out | dh-132 | 0.00 (0/1) out of steps |
| held-out | dh-166 | 0.00 (0/148) out of steps |
| held-out | dh-039 | 0.00 (1/1) out of steps |
| held-out | dh-087 | 0.00 (91/91) no choice |
| held-out | dh-151 | 0.00 (1/1) wrong value |

(The rows are Jaccard overlap, predicted rows / gold rows; the cause is the
failure taxonomy of `scripts/failure_taxonomy.py`.)

## Verdict

Not usable as the assistant model: mean J 0.24-0.45 against 0.72-0.95
for DeepSeek and Gemma, at 2-4x their tokens and cost per question.
The model follows the tool protocol but explores instead of writing a
query. Thinking mode and temperature 1.0 were not tried (no passthrough
in the assistant config); a trial needs a provider `extra_body` key in
NeuroLang, which would be one field in `ProviderConfig` and the OpenAI
payload.
