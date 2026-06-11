# lexical-tests.lisp

Smoke tests for the lexically-scoped `lisp.js`. The reader has no comment syntax,
so the expressions live in `lexical-tests.lisp` and their expected results are
documented here. SectorLISP idiom: dotted `DEFINE`, `(QUOTE T)` for true.

Run against the compiled REPL:

```bash
cc -w -xc lisp.js bestline.c -o lisp     # needs bestline.c/.h from justine.lol
./lisp < lexical-tests.lisp
```

Or, without the C toolchain / bestline, drive the same (real) core under Node:

```bash
node harness.cjs                  # defaults to lexical-tests.lisp
node harness.cjs some-other.lisp  # run any program file
```

`harness.cjs` loads the actual `lisp.js` and runs a DOM-free REPL loop mirroring
`Lisp()`; it exists only for verification.

Expected output (one line per result; `DEFINE` is silent):

| # | Expression | Result | What it shows |
|---|------------|--------|----------------|
| 1 | bare self-application (`FF FF`) | `A` | recursion threaded through a parameter survives lexical scope |
| 2 | Z combinator | `A` | ergonomic recursion; self-application quarantined inside `Z` |
| 3 | `(DEFINE FF . (LAMBDA …))` then `(FF …)` | `A` | recursion **by name**, lexically, via the global frame |
| 4 | free `GG` (old dynamic-scope trick) | `?GG` (error) | the dynamic-scope crutch is gone — `GG` is genuinely unbound |

(So the four printed lines are `A`, `A`, `A`, `?GG`.)

Note the deliberate behavior change: `DEFINE` now **evaluates** its value (Scheme
`define` semantics), so a literal atom must be quoted — `(DEFINE FOO . (QUOTE BAR))`,
not `(DEFINE FOO . BAR)`.
