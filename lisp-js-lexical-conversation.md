# Making `lisp.js` Lexically Scoped (with a Global Frame)

A conversation about converting Justine Tunney's "friendly" SectorLISP v2
(`lisp.js`, a C/JavaScript polyglot) from dynamic to lexical scope — and, unlike
the earlier `lexlisp.py` exercise, deciding what to do about its top-level
`DEFINE`.

---

## 1. The opening question, and a reframing

**Prompt:** Modify `lisp.js` for lexical scope. There are two ways to do it —
(1) bare self-application and (2) the Z combinator. What are the tradeoffs, and
which do you recommend?

The premise needed untangling first. **Bare self-application and the Z combinator
are not two ways to *implement* lexical scope** — they are two ways to *recover
recursion* once you have made the evaluator lexical. Implementing lexical scope is
a single change, the FUNARG closure pivot that `lexlisp.py` already encodes:

- `Eval` builds a closure `(FUNARG params body . a)` capturing the current
  environment when it sees `LAMBDA`, and evaluates the operator before applying.
- `Apply` binds parameters onto the *captured* env (the dotted tail) instead of
  the call-time `a`.

That one substitution *is* lexical scope. What it **breaks** is McCarthy's
free-variable recursion trick (a function name picked up from the dynamic
environment). Bare self-application and Z are two ways to write recursive
*programs* once that crutch is gone — properties of the code you write, not of the
evaluator you build. The evaluator change is identical either way.

### The actual tradeoff

- **Bare self-application (`FF FF`)** — minimal, no extra machinery, fully
  transparent. Cost: the self-passing leaks into every recursive call
  (`(FF FF (CAR X))`), so the body is noisy and easy to get wrong.
- **Z combinator** — the function reads naturally (`(RECUR (CAR W))`);
  self-application is quarantined inside `Z`. Cost: you carry a fixpoint
  combinator, and under applicative order it needs the eta-delay
  `(LAMBDA (V) ((G G) V))` or it diverges before the function is ever called.

**Recommendation:** keep both as smoke tests (as `lexlisp.py` does) — they prove
different things. Bare is the clearer *minimal proof*; Z is the better *template
for real code*.

### The bigger point for `lisp.js`

Unlike `lexlisp.py`, `lisp.js` has `DEFINE` (SectorLISP v2 global definitions). So
neither trick is needed for everyday recursion if `DEFINE` is made lexical — and
that is the real design fork, the "deliberately no DEFINE … its own design choice"
caveat from the earlier conversation coming due.

---

## 2. Does Common Lisp make `DEFUN` lexical?

**Prompt:** LABEL is considered a kludge and has disappeared from Lisp. Does
Common Lisp make `DEFUN` (its `DEFINE`) lexical?

`DEFUN` is CL's define-for-functions, but **Common Lisp is a Lisp-2** — separate
namespaces for functions and values, so `DEFUN` targets the *function* namespace.
McCarthy's evaluator and `lisp.js` are **Lisp-1** (one namespace), so the closer
analog is actually **Scheme's `define`**.

"Is `DEFUN` lexical" splits into two questions:

1. **Variable references in the body → yes, lexical.** A `DEFUN` body is a lambda
   that captures the surrounding lexical *variable* environment via the FUNARG
   mechanism. `(let ((c 0)) (defun bump () (incf c)))` makes `bump` a global
   function that closes over the lexical `c`.

2. **The function's own name, for recursion → not lexical at all.** When
   `(defun fact (n) … (fact (1- n)))` calls `fact`, the name resolves through the
   symbol's **global function cell** (`fdefinition`) — a global, mutable slot, not
   a lexical capture. CL doesn't recover recursion the way `LABEL` /
   self-application / Z do; it **sidesteps** the problem with a separate global
   function namespace. The name is always findable because it lives on the symbol.

`LABEL` didn't vanish — it became **`LABELS`** (lexically scoped, mutually
recursive *local* function bindings), with `FLET` for the non-recursive case. In
Scheme the same role is `letrec`. The "kludge" framing applies to McCarthy's
original `LABEL` patching recursion into a single-namespace, dynamically-scoped
metacircular eval; `LABELS`/`letrec` are the principled descendants.

So the modern split is:

- **Global recursive functions** → `DEFUN` + the global function namespace (CL),
  or top-level `define` (Scheme).
- **Local recursive functions** → `LABELS` (CL) / `letrec` (Scheme).

This grounds the `lisp.js` decision: a global frame threaded as the base
environment, that closures see, *is* the CL/Scheme top-level model. Since `lisp.js`
is a Lisp-1, it lines up with Scheme's `define`/`letrec`. Recursion-by-name then
works **lexically, not as a kludge**, and bare/Z become demonstrations rather than
the everyday mechanism.

---

## 3. The decisions

- **Recursion model: global frame (Scheme model).** Local bindings are lexical
  (FUNARG closures); free names fall back to a single live global frame `g` that
  `DEFINE` extends. Because the fallback is consulted *live* (not snapshotted),
  recursion-by-name plus forward and mutual references work.
- **Demos: both** bare self-application and the Z combinator, plus a `DEFINE`
  recursion case and the old free-variable case (which must now fail).
- **Scope:** only `lisp.js` is changed (plus test files); `lexlisp.py` and the
  existing docs are left untouched.

---

## 4. The change

All evaluator edits live in the **shared C/JS core**, so both the C build and the
JS build inherit them, and every edit stays within the existing polyglot subset.

### The lexical pivot

`Apply` — bind onto the captured env (the only change is the third `Pairlis`
argument):

```c
function Apply(f, x, a) {
  if (f < 0)      return Eval(Car(Cdr(Cdr(f))),
                             Pairlis(Car(Cdr(f)), x, Cdr(Cdr(Cdr(f)))));  // captured env, not a
  ...
}
```

`Eval` — build a closure for `LAMBDA`, evaluate compound operators, keep atom
operators raw so the five builtins resolve by name:

```c
function Eval(e, a) {
  if (!e) return e;
  if (e > 0) return Assoc(e, a);
  if (Car(e) == kQuote) return Car(Cdr(e));
  if (Car(e) == kCond) return Evcon(Cdr(e), a);
  if (Car(e) == kLambda)
    return Cons(kFunarg, Cons(Car(Cdr(e)), Cons(Car(Cdr(Cdr(e))), a)));
  if (Car(e) > 0) return Apply(Car(e), Evlis(Cdr(e), a), a);
  return Apply(Eval(Car(e), a), Evlis(Cdr(e), a), a);
}
```

A `(FUNARG params body . env)` closure aligns slot-for-slot with the old
`(LAMBDA params body)` form SectorLISP assumed in operator position, so the
body/param extraction in `Apply` is unchanged — only the captured-env tail is new.

### The global frame

`Assoc` falls back to the live global frame `g` when the local env is exhausted:

```c
function Assoc(x, y) {
  if (!y) return Lookup(x, g);   // not local -> consult the global frame
  return x == Car(Car(y)) ? Cdr(Car(y)) : Assoc(x, Cdr(y));
}
function Lookup(x, y) {
  if (!y) Throw(x);              // truly unbound
  return x == Car(Car(y)) ? Cdr(Car(y)) : Lookup(x, Cdr(y));
}
```

Both driver loops (C `main` and JS `Lisp`) now **evaluate** the `DEFINE` value
into a closure and install it in `g`, and run top-level forms in the empty local
env, with globals reached via the fallback:

```c
g = Define(Cons(Car(Cdr(x)), Eval(Cdr(Cdr(x)), 0)), g);
...
x = Eval(x, 0);
```

`LAMBDA`/`FUNARG` are interned (added to both builtin strings and `LoadBuiltins`),
and the JS-only global `a` is renamed to the shared `g`.

Because `g` is consulted live, a closure defined before a name still sees it, so a
recursive `DEFINE` finds itself and mutually-recursive / forward references work.

### One deliberate behavior change

`DEFINE` now **evaluates** its value (Scheme `define` semantics), where SectorLISP
stored the raw form. A literal atom must therefore be quoted —
`(DEFINE FOO . (QUOTE BAR))`, not `(DEFINE FOO . BAR)`. This is the only
user-visible change and is the intended Scheme-like semantics.

---

## 5. Verification

The C build needs `bestline` (a network fetch) and a compiler. In a restricted
environment the same real, edited core was driven headlessly under Node
(`harness.cjs`, a DOM-free REPL loop mirroring `Lisp()`), running
`lexical-tests.lisp`:

```
A          ; bare self-application -- recursion survives lexical scope
A          ; Z combinator -- ergonomic recursion, self-application quarantined
A          ; (DEFINE FF . (LAMBDA ...)) then (FF ...) -- recursion by name, lexically
?GG        ; free GG -- the dynamic-scope crutch is gone; GG is genuinely unbound
```

Additional spot-checks confirmed the rest of the language is intact and the change
is genuine:

- Builtins / `QUOTE` / `COND`: `(A . B)`, `A`, `T`, `T`.
- **Lexical capture:** `(((LAMBDA (X) (LAMBDA (Y) X)) (QUOTE CAP)) (QUOTE IGNORED))`
  → `CAP` — the inner lambda kept `X` from its creation env.
- **Dynamic scope is gone:** `((LAMBDA (F) ((LAMBDA (X) (F)) (QUOTE INNER))) (LAMBDA NIL X))`
  → `?X` — a free variable in a passed-in lambda is unbound where dynamic scope
  would have resolved it to `INNER`.
- **Forward / mutual reference via the global frame:** a function that calls a
  helper defined *after* it → `A`.

The file still parses as valid JavaScript, and the C side uses constructs
identical to the existing code, so the polyglot remains buildable as C and
runnable as JS.
