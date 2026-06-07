# From Dynamic to Lexical Scope: McCarthy's Metacircular Evaluator

A conversation about converting McCarthy's `eval`/`apply` from dynamic to lexical
scoping, and recovering recursion through fixpoint combinators.

---

## 1. Explaining the original evaluator

**Prompt:** Explain this code.

```lisp
(DEFINE ASSOC .
  (LAMBDA (X Y)
    (COND ((EQ Y NIL) (QUOTE *UNDEFINED))
          ((EQ X (CAR (CAR Y))) (CDR (CAR Y)))
          ((QUOTE T) (ASSOC X (CDR Y))))))
(DEFINE EVCON .
  (LAMBDA (C A)
    (COND ((EVAL (CAR (CAR C)) A)
           (EVAL (CAR (CDR (CAR C))) A))
          ((QUOTE T) (EVCON (CDR C) A)))))
(DEFINE PAIRLIS .
  (LAMBDA (X Y A)
    (COND ((EQ X NIL) A)
          ((QUOTE T) (CONS (CONS (CAR X) (CAR Y))
                           (PAIRLIS (CDR X) (CDR Y) A))))))
(DEFINE EVLIS .
  (LAMBDA (M A)
    (COND ((EQ M NIL) M)
          ((QUOTE T) (CONS (EVAL (CAR M) A)
                           (EVLIS (CDR M) A))))))
(DEFINE APPLY .
  (LAMBDA (FN X A)
    (COND
      ((ATOM FN)
       (COND ((EQ FN (QUOTE CAR))  (CAR  (CAR X)))
             ((EQ FN (QUOTE CDR))  (CDR  (CAR X)))
             ((EQ FN (QUOTE ATOM)) (ATOM (CAR X)))
             ((EQ FN (QUOTE CONS)) (CONS (CAR X) (CAR (CDR X))))
             ((EQ FN (QUOTE EQ))   (EQ   (CAR X) (CAR (CDR X))))
             ((QUOTE T)            (APPLY (EVAL FN A) X A))))
      ((EQ (CAR FN) (QUOTE LAMBDA))
       (EVAL (CAR (CDR (CDR FN)))
             (PAIRLIS (CAR (CDR FN)) X A))))))
(DEFINE EVAL .
  (LAMBDA (E A)
    (COND
      ((ATOM E)
       (COND ((EQ E NIL) E)
             ((EQ E (QUOTE T)) (QUOTE T))
             ((QUOTE T) (ASSOC E A))))
      ((ATOM (CAR E))
       (COND ((EQ (CAR E) (QUOTE QUOTE)) (CAR (CDR E)))
             ((EQ (CAR E) (QUOTE COND)) (EVCON (CDR E) A))
             ((EQ (CAR E) (QUOTE LAMBDA)) E)
             ((QUOTE T) (APPLY (CAR E) (EVLIS (CDR E) A) A))))
      ((QUOTE T) (APPLY (CAR E) (EVLIS (CDR E) A) A)))))
(EVAL (QUOTE ((LAMBDA (FF X)
                (FF X))
              (LAMBDA (X)
                (COND ((ATOM X) X)
                      (T (FF (CAR X)))))
              (QUOTE ((A) B C))))
      NIL)
```

### Explanation

This is McCarthy's metacircular evaluator — `eval`/`apply` written in the very
language it interprets. It's the "Roots of Lisp" core (the seven primitives
`QUOTE ATOM EQ CAR CDR CONS COND` plus `LAMBDA`) in the dotted-`DEFINE`/SectorLISP
idiom, where `(DEFINE ASSOC . <lambda>)` literally conses the pair
`(ASSOC . <lambda>)` — exactly the shape `ASSOC` itself walks.

The auxiliaries are the plumbing:

- **`ASSOC`** — environment lookup. Walk the a-list `Y`, return the `CDR` of the
  first pair whose `CAR` matches `X`, else `*UNDEFINED`.
- **`EVCON`** — the `COND` engine. Evaluate each clause's predicate
  `(CAR (CAR C))`; on the first truthy one, evaluate its consequent
  `(CAR (CDR (CAR C)))`.
- **`PAIRLIS`** — bind parameters to arguments and *cons them onto the existing
  environment* `A`. This last detail is the whole game.
- **`EVLIS`** — evaluate an argument list, left to right.

`APPLY` and `EVAL` are the mutually-recursive heart:

`APPLY` dispatches on `FN`. If it's an atom, it's either one of the five builtins
applied to the already-evaluated args, or a name to be looked up and re-applied
(`(APPLY (EVAL FN A) X A)`). If it's `(LAMBDA params body)`, evaluate `body` in
`(PAIRLIS params X A)`.

`EVAL` dispatches on `E`: an atom is `NIL`/`T`/a variable looked up in `A`; a form
headed by `QUOTE`/`COND`/`LAMBDA` is special-cased; anything else is a call —
evaluate the args with `EVLIS` and hand off to `APPLY`.

The punchline is the final expression. It's McCarthy's `ff` ("find first atom")
example:

```lisp
((LAMBDA (FF X) (FF X))
 (LAMBDA (X) (COND ((ATOM X) X) (T (FF (CAR X)))))
 (QUOTE ((A) B C)))
```

`ff` descends through `CAR`s until it hits an atom, so on `((A) B C)` it goes
`((A) B C)` → `(A)` → `A`, and the result is **`A`**.

What makes this worth showing rather than just `eval` itself: the inner lambda
calls `FF` by name, but `FF` is a *free variable* — it's only the outer lambda's
parameter. There's no `LABEL`, no closure capture. It resolves solely because
`PAIRLIS` stacks new bindings on top of the inherited a-list, so when `ff`'s body
is finally evaluated, `FF` is still live in the dynamic environment:

```
A1 = ((FF . <ff-lambda>) (X . ((A) B C)))          ; outer lambda
A2 = ((X . ((A) B C)) (FF . <ff-lambda>) ...)        ; one level into ff — FF survives
```

Under lexical scoping this would be an unbound-variable error. So this snippet is
the classic demonstration that McCarthy's 1960 `eval` is dynamically scoped — and
the seed of what became the FUNARG problem. The recursion-via-self-passing trick
only works because of the bug, so to speak.

---

## 2. Making it lexically scoped

**Prompt:** How would you change this to be lexically scoped?

The essence of the change is one idea: a lambda must capture the environment it
was *created* in, and be applied in that captured environment rather than the one
live at the call site. Dynamic scope falls out of `APPLY` doing
`(PAIRLIS params X A)` with the *call-time* `A`; lexical scope means swapping that
`A` for an environment frozen when the lambda was evaluated. That's the FUNARG
mechanism, so we borrow its name for the closure tag.

Represent a closure as `(FUNARG params body . env)`. Two functions change;
`ASSOC`, `EVCON`, `PAIRLIS`, `EVLIS` are untouched.

`EVAL` stops returning the bare lambda and instead builds a closure over the
current `A`, and the compound-operator case now *evaluates* the operator (so it
becomes a closure) instead of handing `APPLY` a raw form:

```lisp
(DEFINE EVAL .
  (LAMBDA (E A)
    (COND
      ((ATOM E)
       (COND ((EQ E NIL) E)
             ((EQ E (QUOTE T)) (QUOTE T))
             ((QUOTE T) (ASSOC E A))))
      ((ATOM (CAR E))
       (COND ((EQ (CAR E) (QUOTE QUOTE)) (CAR (CDR E)))
             ((EQ (CAR E) (QUOTE COND)) (EVCON (CDR E) A))
             ((EQ (CAR E) (QUOTE LAMBDA))
              (CONS (QUOTE FUNARG)
                    (CONS (CAR (CDR E))
                          (CONS (CAR (CDR (CDR E))) A))))   ; capture A
             ((QUOTE T) (APPLY (CAR E) (EVLIS (CDR E) A) A))))
      ((QUOTE T) (APPLY (EVAL (CAR E) A) (EVLIS (CDR E) A) A)))))  ; eval operator
```

`APPLY` replaces the `LAMBDA` clause with a `FUNARG` clause that binds parameters
onto the *captured* env (the dotted tail), discarding `A`:

```lisp
(DEFINE APPLY .
  (LAMBDA (FN X A)
    (COND
      ((ATOM FN)
       (COND ((EQ FN (QUOTE CAR))  (CAR  (CAR X)))
             ((EQ FN (QUOTE CDR))  (CDR  (CAR X)))
             ((EQ FN (QUOTE ATOM)) (ATOM (CAR X)))
             ((EQ FN (QUOTE CONS)) (CONS (CAR X) (CAR (CDR X))))
             ((EQ FN (QUOTE EQ))   (EQ   (CAR X) (CAR (CDR X))))
             ((QUOTE T)            (APPLY (EVAL FN A) X A))))
      ((EQ (CAR FN) (QUOTE FUNARG))
       (EVAL (CAR (CDR (CDR FN)))                  ; body
             (PAIRLIS (CAR (CDR FN))               ; params
                      X
                      (CDR (CDR (CDR FN)))))))))    ; captured env, not A
```

That single substitution — `(CDR (CDR (CDR FN)))` where the dynamic version used
`A` — is the whole of lexical scoping. The threading is now self-consistent:
since every body runs in its captured env, the `A` flowing through `EVAL`/`APPLY`
*is* the lexical environment everywhere, so the symbol-operator lookup
`(APPLY (EVAL FN A) X A)` is already correct. The atom branch still passes the
operator symbol unevaluated so the five builtins are resolved by name rather than
looked up in the env.

The consequence: the old `ff` example now **breaks**. The inner
`(LAMBDA (X) ... (FF (CAR X)))` is evaluated as an argument at top level, so its
closure captures `NIL`; when `(FF (CAR X))` runs, `FF` isn't in that frozen env
and resolves to `*UNDEFINED`. The dynamic-scope accident that made self-passing
recursion work is exactly what's gone.

To recover recursion you need to name the function in scope. The canonical fix is
McCarthy's `LABEL`, two lines in `EVAL`:

```lisp
((EQ (CAR E) (QUOTE LABEL))
 (EVAL (CAR (CDR (CDR E)))
       (CONS (CONS (CAR (CDR E)) E) A)))   ; bind name to the LABEL form itself
```

Then:

```lisp
(EVAL (QUOTE
        ((LABEL FF (LAMBDA (X)
                     (COND ((ATOM X) X)
                           (T (FF (CAR X))))))
         (QUOTE ((A) B C))))
      NIL)            ; => A
```

Each lookup of `FF` re-evaluates the `LABEL` form into a fresh closure, so it's
bound in its own body. The combinator-flavored alternative, needing no new
special form, is to pass the function to itself explicitly.

---

## 3. The combinator-flavored alternative

**Prompt:** Show me the combinator-flavored alternative.

Both versions below run under the lexical evaluator and return `A` (and the old
free-`FF` version blows the stack, confirming it's genuinely broken under lexical
scope).

The bare, minimal version makes the self-reference an explicit parameter. `FF` is
passed to itself, so the recursive call is `(FF FF ...)`:

```lisp
((LAMBDA (FF X) (FF FF X))
 (LAMBDA (FF X) (COND ((ATOM X) X)
                      (T (FF FF (CAR X)))))
 (QUOTE ((A) B C)))            ; => A
```

This works because `FF` is now bound — no free variables leaning on the call-time
a-list. But the self-passing (`FF FF`) is boilerplate smeared through the body.
The combinator move factors it out so the recursive function reads naturally.

Write the function as a *generator* that takes its own recursive self as an
ordinary parameter `RECUR` and returns the real function:

```lisp
(LAMBDA (RECUR)
  (LAMBDA (W)
    (COND ((ATOM W) W)
          (T (RECUR (CAR W))))))
```

Then a fixpoint operator ties the knot. Under applicative order you need the Z
combinator (Y with the `(λv. (x x) v)` eta-delay, or it diverges before the
function is ever called):

```lisp
(LAMBDA (F)
  ((LAMBDA (G) (F (LAMBDA (V) ((G G) V))))
   (LAMBDA (G) (F (LAMBDA (V) ((G G) V))))))
```

Put together — `((Z gen) data)`:

```lisp
(((LAMBDA (F)
    ((LAMBDA (G) (F (LAMBDA (V) ((G G) V))))
     (LAMBDA (G) (F (LAMBDA (V) ((G G) V))))))
  (LAMBDA (RECUR)
    (LAMBDA (W)
      (COND ((ATOM W) W)
            (T (RECUR (CAR W)))))))
 (QUOTE ((A) B C)))            ; => A
```

The trade is the classic one: the bare version is shorter but the recursion
mechanism leaks into the function body (`FF FF`); the Z version pays for a
fixpoint combinator up front but the function it operates on is clean — `RECUR`
looks like an ordinary recursive call, and the self-application is quarantined
inside `Z`. Both rely on the same fact the lexical evaluator now enforces: a name
is only visible if it's lexically bound, so recursion has to be threaded through a
parameter rather than picked up from the dynamic environment. `LABEL` is just the
evaluator doing this knot-tying for you in `EVAL` instead of in source.

---

## 4. The verification harness

A faithful Python transcription of the lexically-scoped `EVAL`/`APPLY`, used to
check every variant above. Running it prints:

```
bare self-application : A
Z combinator          : A
free FF (dynamic only): UNBOUND -- diverges (as expected)
```

See the accompanying `lexlisp.py`. Notes for poking at variants:

- `run(src)` reads and evaluates one S-expression in `NIL`; swap the env argument
  to seed bindings by hand.
- The free-`FF` case is wrapped in a `RecursionError` guard so the script
  finishes instead of dumping a traceback — that divergence *is* the lexical-scope
  result (the lookup of an unbound `FF` falls through to `*UNDEFINED`, which then
  tries to apply itself).
- There's deliberately no `DEFINE`: the lexical-vs-dynamic question for top-level
  `DEFINE` is its own design choice. The clean move is a global frame threaded as
  the base env, which keeps top-level names lexical too.
