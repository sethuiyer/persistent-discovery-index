# O4B_INJECTOR.md

**Status: FROZEN BEFORE GENERATION.** Operator set v1 (`op/v1`). This file fixes
*how* tasks are manufactured **before** any agent runs, and before any eligibility
result is known. Mutation operators may not be added, removed or retuned once
generation has begun.

The injector manufactures **executable behavioural defects** in production modules.
It never edits tests, and it never consults agent behaviour.

## 1. Module pool

One task per module; the **module is the cluster**. Twenty fast, deterministic
production modules with a mapped suite:

`pdi`, `quotient_tower`, `adapters`, `ingest`, `multiresolution`, `cofinal_mesh`,
`transport`, `stable_quotient`, `collision_mechanism`, `both_structures`,
`one_question`, `invariance_first`, `proof_awareness`, `prime_holonomy`,
`survival_commutation`, `core_monodromy`, `o2_theorem`, `zeta_separation`, `sudoku`,
`agent_profiler`.

`invertibility.py` and `test_invertibility.py` are **excluded** from v1 purely on
runtime (its suite takes ~62 s), as is any suite whose clean run exceeds
`TIMEOUT = 90 s`. `collision_mechanism.py` is kept but is slow (~43 s) and so
receives at most one operator (§3).

**Excluded:** tests, `evaluators.py`, `o4b_stat.py`, `o4b.py`, `o4b_inject.py`,
split/eligibility/bootstrap machinery, and anything implementing the frozen ruler.
Benchmarking an evaluator needs an independent verifier; it is out of v1.

## 2. Operators (`op/v1`)

AST transformations, applied to a **production** module only. Text is produced by
`ast.unparse`.

| id | target nodes | transformation | candidate order |
|---|---|---|---|
| `arith_literal` | `Constant` (int/float, not bool) | int `n → n+1`; float `n → n*2` | `(lineno, col_offset)` |
| `cmp_invert` | `Compare`, single op | `==↔!=`, `<↔>=`, `<=↔>` | `(lineno, col_offset)` |
| `branch_swap` | `If` with non-empty `body` and `orelse` | swap the two blocks | `(lineno, col_offset)` |
| `return_sentinel` | `Return` with a value | replace value with `None` | `(lineno, col_offset)` |
| `off_by_one` | `Call(range, 1 arg)` | `range(x) → range(x + 1)` | `(lineno, col_offset)` |
| `default_arg` | `arguments.defaults` int/bool `Constant` | int `+1`; bool negate | `(lineno, col_offset)` |
| `drop_validate` | `Expr` calling `*validate*` / `validate_pairs`, or `Assert` | delete the statement | `(lineno, col_offset)` |

`drop_validate` targets **production invariant checks only** — never a test, never
an assertion inside a verifier.

## 3. Candidate ordering and seeded selection

1. For a `(module, operator)`, candidates are the matching nodes sorted by
   `(lineno, col_offset)`; ties broken by node type name then `ast.dump`.
2. For each `(module, operator)`, attempts start at the **seeded candidate**
   `sha256(f"{seed}:{module}:{operator}") mod |candidates|`, then proceed **in
   order**, wrapping, for up to `CANDIDATE_LIMIT = 5` candidates.
3. If none is eligible, the **next operator** in the fixed order is tried.
4. A task is taken from the **first eligible** `(module, operator, candidate)`.
   **Every** attempt is recorded in the corpus with its result and reason. This is
   a bounded, documented search — never a silent replacement.
5. Suites slower than `FAST_LIMIT = 20 s` on the clean tree are given **all
   operators but only one candidate each** (`climit = 1`), to bound runtime.

## 4. Eligibility

A candidate is **eligible** iff, in a fresh copy of the clean snapshot:

```text
clean snapshot, verifier        -> PASS (exit 0)
mutated snapshot, ast.parse      -> parses
mutated snapshot, verifier       -> FAIL (nonzero) and NOT an infrastructure error
```

Rejection reasons, recorded verbatim: `no_candidates`, `syntax_error`,
`infra_error` (SyntaxError/ImportError/ModuleNotFoundError in output),
`timeout`, `clean_fail`, `slow_suite`, `did_not_flip`, `exhausted`.

Broken files are **not** tasks. A timeout is a rejection, not a defect.

## 5. Provenance — one record per task

`task_id`, `module_cluster`, `seed`, `source_commit`, `candidate_location`,
`operator` + `version`, `patch_hash`, `clean_hash`, `mutated_hash`, `task_text`,
`verifier_command`, `clean_result`, `mutated_result`, `eligibility`,
`exclusion_reason`, `attempts[]` (each with its own reason).

`task_text` reveals **no** mutation metadata, location, operator, failing
assertion, or reference patch:

> "The repository's test suite `python3 <suite>.py` is failing. A regression was
> introduced into the production code. Find and fix the defect. Do not modify the
> tests."

## 6. Split — sealed

Tasks are grouped by **module cluster**, then `M = 20` clusters are shuffled with
`random.Random(seed=20260916)` and split **12 discovery / 8 held-out**. Because
there is one task per module, **no module appears on both sides** — the holdout
measures transfer to unseen modules, not within seen ones.

`discovery`'s mutation metadata may be inspected to build the corpus. `held-out`
identities are generated deterministically and then **sealed**: no held-out
profile, outcome or failure is inspected or used to tune anything.

## 7. Fingerprint

`sha256` over canonical JSON of `{operator_version, seed, M, split,
tasks:[{task_id, module_cluster, operator, candidate_location, clean_hash,
mutated_hash, eligibility}]}`. This fingerprint, the operator set, the eligibility
decisions and the split are committed together. Generation writes
`o4b_corpus/corpus.json`.
