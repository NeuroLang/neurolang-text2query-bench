# neurosynth-v3d: step 1 of the distillation plan on Albert DeepSeek (2026-11-13)

Albert only: `albert-deepseek`, i.e. DeepSeek V4 Flash 0731. No OpenRouter calls.
- **Code:** upstream master **8532a28b** (0.1a22, after #1176), in the detached worktree
  `/Users/bot/NeuroLang-nsv3d`, run with `source scripts/nsv3d_env.sh` (`.venv-dsparity` + PYTHONPATH).
- **Config:** `configs/llm.nsv3d.yaml` is `llm.nsv3.yaml` with a 180 s request timeout. Albert replies took 15–140 s,
  and 60 s timed out.
- **Run settings:** English, ReAct, BM25, 6 examples, 8 steps, temperature 0, `verify_rounds: 0`.
- **Fixes:** the local branch `nsv3d-integration` (`/Users/bot/NeuroLang-nsv3d-int`, `NL_TREE=...`) holds
  #1201 + #1202 + #1203.

**Caveat: load.** Another session ran four Sonnet distillation shards and the nsv3c reruns on the same Mac
throughout (load 11–12, 20–36 GB swap, 60 GB in the memory compressor).
- The agent's 30 s query timeout and 4 GB memory guard fired on queries that are fast on an idle machine.
  For example, dh-117's `peak_mni ... euclidean <= 6` was stopped at 30 s.
- Single runs at temperature 0 move by ±2 questions on their own (p-019, p-150, p-175 below).
- Every number here is one run.

## Golds

#1176 (`kernel_radius_mm` 6 for `activated` and the atlases) changes 41 of 65 v3 golds. These changes are expected:
- probabilities over larger kernels;
- negations losing rows ("but not"/"do not activate" a region that more studies now reach: p-099 110→66, dh-062 4490→4220).

The golds that hard-coded the assistant's old 3 mm point radius, without the question saying "3 mm", now use 6 mm,
the engine's `kernel_radius_mm`:
- v3: dh-112, dh-117, dh-122 and the right-caudate question;
- fresh: the right-insula question;
- nsv2-12: two points.

The nsv2 questions that say "within 3 mm" keep 3. The gold caches were regenerated on 8532a28b.
This edit landed while the other session's nsv2/v3 reruns were in flight.

## Step 0: Albert DeepSeek on v3 dev (33), master

27 exact, mean J 0.818, 32k tokens/q, 141 s/q. This is after two `--resume` passes over Albert request timeouts.

| miss | category | evidence |
|---|---|---|
| p-116 | search loop | 8 `search_values` (premotor → precentral, one repeated), out of steps |
| dh-029 | memory/time guard | `p_a_given_t`, the inline PROB and a plain join over `activated`: all stopped ("too much memory", "> 30 s") |
| p-049 | memory/time guard (+ Cognitive Atlas) | every voxel query stopped; `search_values` on `cogat_subclass_of` crashed (`'DataFrame' object has no attribute 'str'`, #1204) |
| dh-151 | other (Tian parts) | left amygdala = `lAMY lh` only, not `mAMY lh` |
| p-068 | other (term) | `mentions(s, 'frontal')` for "frontal lobe"; on the way it hit an engine bug (#1205) |
| dh-067 | Albert | the request timed out (180 s) three times |

On dev there is no answer-shape miss, no probabilistic-negation miss and no MNI-versus-voxel miss: those are all
test-split questions (p-128, dh-127, dh-166, dh-117).

## Fixes (NeuroLang PRs, from master)

| PR | change | evidence |
|---|---|---|
| [#1201](https://github.com/NeuroLang/NeuroLang/pull/1201) | search loops: from the 2nd `search_values` call finding no value not seen before (a repeated call counts), that call's observation asks for the query with the values found | replay of past runs (`scripts/search_loop_replay.py`): fires on 15 DeepSeek answers (7 out-of-steps misses, at step 3–7) and on no Sonnet answer |
| [#1202](https://github.com/NeuroLang/NeuroLang/pull/1202) | guidance: regions "not activated" by a topic = PROB[not_active // topic] with `~destrieux_activated` over `selected_study`; MNI coordinates never the voxel indices of `activated`/`lift`/`brain_mask` | test questions dh-166, dh-117 |
| [#1203](https://github.com/NeuroLang/NeuroLang/pull/1203) | the agent's per-query memory guard counted the parent's pages the child reads | see below |
| [#1204](https://github.com/NeuroLang/NeuroLang/pull/1204) | `search_values` on a predicate with repeated column names (`cogat_subclass_of`: `iri, iri`) crashed | p-049 |
| [#1205](https://github.com/NeuroLang/NeuroLang/pull/1205) | `l` bound outside a body disjunction of builtins (`tian(l, r), (startswith('aHIP', l) \| startswith('pHIP', l))`) raised UnboundVariablesError (NeurolangDL and PDL) | p-068 step0, dh-127 retest |

#1201 and #1202 each add a `**Bug fixes:**` block at the same changelog anchor, so whichever merges second needs
a trivial rebase.

**Answer shape: no PR.** The verifier's judgement request already has the head columns and the first rows:
`answer_rows` is the preview, "N rows; columns ..." followed by the rows. A retest of the test questions with
`verify_rounds: 1` (`configs/llm.nsv3d-verify.yaml`) gave:
- **p-128:** DeepSeek answered pairs `(l1, l2, p)`, the gold's 4950 rows, but the verifier rejected it because
  parcels are "not networks" (a false rejection). The model then ran on until an Albert timeout.
- **dh-127:** P(co_active ∧ hip | injury) excluding the seed. The back-translation read it as
  P(l | injury ∧ hip) and the verifier accepted it (a false acceptance). F1 0.

The verifier is not the lever for these two.

### Measured effect

**v3 dev**, integration (#1201–#1203) against master, one run each:

| | exact | mean J | Albert timeouts | tokens/q |
|---|---:|---:|---:|---:|
| master (step 0) | 27 | 0.818 | 1 | 32k |
| integration | 25 | 0.783 | 2 | 33k |

Flips:
- **p-116 0 → 1:** the notice fired at step 5, and the out-of-steps fallback answer was exact.
- **dh-029:** an Albert timeout on the integration run.
- **p-019, p-150 0 → 0:** hemisphere variance ("left hippocampus" taken as both; "left amygdala" as `lAMY lh` only).
- **p-175 1 → 0.83:** "globus pallidus" taken as the left GP only.

None of these three regressions reads a changed line. The fixes were not active in those trajectories: the
notice never fired, and there is no negation or MNI question.

**Targeted test questions**, one run each:

| | master | integration |
|---|---|---|
| dh-166 (negation) | 0 | **1** |
| dh-117 (MNI) | 1 | 0 (peak query stopped at 30 s under load, then voxel indices) |
| p-008 (loop) | 1 | 0 (notice fired twice, the model kept searching, out of steps) |
| p-083 (loop) | Albert timeout | 1 |
| p-186 (loop) | 1 | 1 |
| dh-010 (memory) | Albert timeout | Albert timeout (after 2 guard stops) |

## The memory limit of `p_a_given_similar` (dh-010)

Not an engine inefficiency: `p_a_given_similar` allocates less than the inline form.
- **Allocation peak (tracemalloc, numpy included):** `p_a_given_similar('being socially excluded…', i, j, k, p)` peaks at
  1.85–2.0 GB; the inline `PROB[activation // close(q, s)]` at 3.5 GB. Both give the same 1,786,587 rows.
- **Plans:** magic sets restrict `activated` to the 719 similar studies (17.7 M of 346 M rows).

The kills come from the guard.
- **What it measured:** `validation._in_child` measured the forked child with `ps rss`, which counts the
  parent's pages the child shares.
  - **Linux** (Margaret, 6.12): a child's RSS is the parent's from the fork. A 2 GB parent gives a 2064 MB child
    with 1 MB private. With a 14 GB engine, every query is "too much memory".
  - **macOS:** RSS grows as the child reads. A child only summing a 3 GB parent array is stopped at 2 GB
    (`scripts/fork_rss_probe.py`).
- **Why voxel queries hit it now:** since #1176, `activated` has 346 M rows on the 1 mm grid, so every voxel query
  reading it is stopped: dh-010, dh-029, p-049 (`p_a_given_t`, inline PROB, plain joins).
- **#1203** measures private memory instead: `Private_*` of `smaps_rollup` on Linux, `ri_phys_footprint` on macOS.
  - Under the memory pressure of this machine, the compressed parent pages are decompressed into the child,
    and the footprint still grows. So on this Mac today the fix does not rescue the voxel queries; on Linux it does.
  - The inline gold also needs 3.5 GB and 23.6 s on an idle machine, close to the 4 GB and 30 s limits.
  - The limits and the grid (`-r 2`) are the user's call; nothing was changed.

## Judge cascade calibration (`scripts/judge_cascade.py`, free, Albert only)

**Steps:**
1. **Agreement:** ≥2 of 3 DeepSeek answers return the candidate's rows (symmetric, up to the column order;
   stop early when decided).
2. **Judges:** two Albert DeepSeek judge calls (the verifier's instructions, the engine's description, schema and
   guidance (6 mm), question, query, first rows), the second with the query before the question. Both yes: accept;
   both no: reject.
3. **Flag:** split verdicts are flagged for Sonnet. Sonnet was not called.

Every query was re-run on 8532a28b.

**Cases:**
- **Distill:** the 79 Sonnet answers with Opus's verdict (66 kept, 13 rejected). New Albert ReAct answers at
  temperature 0.7, the question left out of the bank. 74 were settled; 5 were left incomplete by Albert errors.
- **Gold:** the nsv2 + v3 golds (right) and up to 2 non-exact past answers per question, re-scored against the
  new golds (labels from execution). 146 cases with rows; the DeepSeek samples are 3 past DeepSeek runs, never
  the candidate's.

| set | cases (right) | agreement | judges yes | judges no | flagged | accept precision | accept recall | agrees with label, settled |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| distill vs Opus | 74 (62) | 41 (55%) | 14 | 14 | 5 (7%) | 0.909 | 0.806 | 56/69 = **81%** |
| distill, radius-free | 66 (54) | 36 | 12 | 13 | 5 | 0.896 | 0.796 | 49/61 = 80% |
| golds nsv2 + v3 | 146 (106) | 88 (60%) | 36 | 15 | 7 (5%) | 0.839 | 0.981 | 118/139 = **85%** |

**By stage:**
- **Agreement** is precise: 37/41 right on distill (the 4 are Opus rejections, e.g. pool-047, 182, 183) and
  86/88 on golds.
- **The DeepSeek judge pair is weak:**
  - golds: it accepted 18 of the 38 wrong answers it saw;
  - distill: it rejected 8 of the 25 Opus-kept answers it saw.
- **Direction of the agreement test:** the one-directional F1 = 1 of `agreement_gate.py` would add 9 + 2
  agreements on golds, and 1 on distill.

**Verdict: the target of ≥95% is not met.** Keep the agreement step: about 55–60% of the cases, ~90–98% precise.
Send every disagreement to the Sonnet judge (or Opus), not to the DeepSeek pair.

## Albert usage

- **Cascade:** 646 requests, 4.31 M in / 0.09 M out (`data/cascade/ledger.jsonl`).
- **Bench runs** (step 0, integration, retests): about 2.9 M tokens, about 350 calls (`answers.json` tokens,
  timed-out requests not counted).
- **Total:** about 7.3 M tokens of DeepSeek, no Gemma.
