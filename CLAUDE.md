# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A Python transcription of McCarthy's metacircular EVAL/APPLY evaluator, modified for **lexical** (not dynamic) scope using the FUNARG closure mechanism. The companion document `lexical-evaluator-conversation.md` explains the design decisions in depth — read it before changing the evaluator semantics.

## Running

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

## Architecture

**Data model** (`lexlisp.py:21-26`): atoms are Python `str`, NIL is Python `None`, cons cells are 2-tuples. Closures are runtime-only cons cells tagged `FUNARG`: `(FUNARG params body . captured-env)` — they are never parsed from source.

**Evaluator core** (`lexlisp.py:49-78`): `EVAL` and `APPLY` are mutually recursive, matching the original McCarthy structure exactly. The single lexical-vs-dynamic pivot is in `APPLY`'s FUNARG clause (`lexlisp.py:57-61`): it binds params onto `env` (the *captured* env stored in the closure), not onto `a` (the call-time env). The dynamic version used `a` there.

**EVAL lambda case** (`lexlisp.py:73-76`): when `EVAL` sees `LAMBDA`, it immediately builds a `FUNARG` closure capturing the current `a`. The dynamic version returned the bare lambda form.

**Auxiliaries** (`lexlisp.py:30-46`): `assoc`, `evcon`, `pairlis`, `evlis` are unchanged from the dynamic version — the lexical change is entirely in EVAL/APPLY.

**No DEFINE**: the evaluator has no top-level definition form. All expressions evaluate in the empty environment `NIL`. Recursion requires either explicit self-passing (`FF FF`) or the Z combinator; see `lexical-evaluator-conversation.md` §3.

**Reader/writer** (`lexlisp.py:81-112`): minimal S-expression parser — tokenizes, then builds cons cells. Handles proper lists and NIL; dot notation is write-only (closures in output). `read` → `EVAL` → `write` is the round-trip.
