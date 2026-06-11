# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Two lexically-scoped variants of McCarthy's metacircular EVAL/APPLY evaluator, both using the FUNARG closure mechanism for **lexical** (not dynamic) scope:

- **`lexlisp.py`** — a Python transcription with **no DEFINE**; every expression evaluates in the empty environment. Companion doc: `lexical-evaluator-conversation.md`.
- **`lisp.js`** — Justine Tunney's "friendly" SectorLISP v2 (a C/JavaScript polyglot), converted to lexical scope **with a Scheme-style global frame** so top-level `DEFINE` keeps recursion-by-name working. Companion doc: `lisp-js-lexical-conversation.md`.

Read the relevant companion document before changing evaluator semantics. The other markdown notes (`substitution-vs-environment.md`, `common-lisp-lexical-scope.md`) give background.

## Running

### `lexlisp.py`

```bash
python3 lexlisp.py
```

Runs the three built-in smoke tests and prints:

```
bare self-application : A
Z combinator          : A
free FF (dynamic only): UNBOUND -- diverges (as expected)
```

No dependencies beyond the Python standard library. No build step, no test runner.

To evaluate an expression interactively from Python:

```python
from lexlisp import run, NIL
run("(QUOTE (A B C))")           # evaluates in empty env
run("(CAR (QUOTE (A B C)))")     # => 'A'
```

### `lisp.js`

The polyglot self-builds via its shell trampoline, or compile it directly (needs `bestline.c`/`bestline.h` fetched from justine.lol):

```bash
cc -w -xc lisp.js bestline.c -o lisp
./lisp < lexical-tests.lisp
```

Without the C toolchain / network, `harness.cjs` drives the *real* `lisp.js` core under Node with a DOM-free REPL loop (verification only):

```bash
node harness.cjs                  # defaults to lexical-tests.lisp
node harness.cjs some-other.lisp
```

`lexical-tests.lisp` is the smoke-test suite (bare self-application, Z combinator, a `DEFINE` recursion, and a free-variable case that now errors); expected outputs are in `lexical-tests.README.md`. The reader has **no comment syntax** and bare `T` is unbound, so test programs use `(QUOTE T)` and contain expressions only.

## Architecture: `lexlisp.py`

**Data model** (`lexlisp.py:21-26`): atoms are Python `str`, NIL is Python `None`, cons cells are 2-tuples. Closures are runtime-only cons cells tagged `FUNARG`: `(FUNARG params body . captured-env)` — they are never parsed from source.

**Evaluator core** (`lexlisp.py:49-78`): `EVAL` and `APPLY` are mutually recursive, matching the original McCarthy structure exactly. The single lexical-vs-dynamic pivot is in `APPLY`'s FUNARG clause (`lexlisp.py:57-61`): it binds params onto `env` (the *captured* env stored in the closure), not onto `a` (the call-time env). The dynamic version used `a` there.

**EVAL lambda case** (`lexlisp.py:73-76`): when `EVAL` sees `LAMBDA`, it immediately builds a `FUNARG` closure capturing the current `a`. The dynamic version returned the bare lambda form.

**Auxiliaries** (`lexlisp.py:30-46`): `assoc`, `evcon`, `pairlis`, `evlis` are unchanged from the dynamic version — the lexical change is entirely in EVAL/APPLY.

**No DEFINE**: the evaluator has no top-level definition form. All expressions evaluate in the empty environment `NIL`. Recursion requires either explicit self-passing (`FF FF`) or the Z combinator; see `lexical-evaluator-conversation.md` §3.

**Reader/writer** (`lexlisp.py:81-112`): minimal S-expression parser — tokenizes, then builds cons cells. Handles proper lists and NIL; dot notation is write-only (closures in output). `read` → `EVAL` → `write` is the round-trip.

## Architecture: `lisp.js`

A C/JavaScript polyglot: the C-only and JS-only sections are hidden from each other via comment/template-literal tricks, and a **shared core** (the `Eval`/`Apply`/`Assoc`/reader/GC functions near the top) is valid in both. **All evaluator edits live in the shared core** so both targets inherit them, and every edit must stay within the C/JS-common subset (`#define var int`, `#define function`, K&R-style defs) or the polyglot breaks. Run `node --check lisp.js` after edits.

**Data model**: atoms are positive ints (interned), cons cells are negative ints, NIL is `0`. So in the core, `e > 0` ⇒ atom, `e < 0` ⇒ cons. A cons in operator position is assumed to be `(LAMBDA params body)` — `Apply` never checks the head atom — and a `(FUNARG params body . env)` closure aligns slot-for-slot, so body/param extraction is unchanged.

**Lexical pivot** (mirrors `lexlisp.py`): `Eval` builds a `FUNARG` closure capturing `a` for `LAMBDA` and evaluates compound operators (atom operators stay raw so the builtins resolve by name); `Apply`'s closure branch binds params onto the captured tail `Cdr(Cdr(Cdr(f)))`, not the call-time `a`.

**Global frame (the Scheme model)**: a shared global `g` holds top-level definitions. `Assoc` falls back to `g` (via `Lookup`) when the local env is exhausted; because `g` is consulted *live*, recursion-by-name plus forward/mutual references work without `LABEL`. Both driver loops (C `main`, JS `Lisp`) **evaluate** the `DEFINE` value into a closure and install it in `g`, and run top-level forms in the empty local env.

**Deliberate behavior change vs upstream SectorLISP**: `DEFINE` now *evaluates* its value (Scheme `define` semantics) instead of storing the raw form. A literal atom must therefore be quoted — `(DEFINE FOO . (QUOTE BAR))`, not `(DEFINE FOO . BAR)`. `LAMBDA`/`FUNARG` are interned (in both builtin strings and `LoadBuiltins`), and the JS-only global `a` was renamed to the shared `g`.
