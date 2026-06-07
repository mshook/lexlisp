# How Common Lisp Implements Lexical Scope

Essentially the same way `lexlisp.py` does — the FUNARG mechanism *is* what Common Lisp does, just with decades of optimization on top.

**The core idea** is identical: when `LAMBDA` is evaluated, the runtime pairs the function code with a snapshot of the current lexical environment. That pair is the closure. On call, the body runs in the captured env extended with the new bindings — never in the caller's env.

**How CL represents environments** in practice:

- The compiler analyzes which variables a lambda closes over at compile time. Only those bindings need to be heap-allocated into a closure object; locals that aren't captured stay on the stack.
- A closure is typically a two-word heap object: a pointer to compiled machine code + a pointer to a vector of captured values.
- Nested closures that share a mutable binding (e.g. a counter) share the same heap cell, so mutation is visible across all of them — this is the "upward funarg" case that FUNARG was originally designed to solve.

**Special variables are the exception**: `defvar`/`defparameter` declare a variable *dynamically* scoped. CL has both worlds — lexical by default, dynamic via `declare special` or `defvar`. The dynamic variables use a separate thread-local binding stack, not the lexical environment chain.

**Compared to `lexlisp.py`**: the structure in `lexlisp.py:57-61` — extract the captured env from the closure, extend it with the new params, ignore the call-time `a` — is exactly what a CL implementation does. The difference is that `lexlisp.py` uses a linked a-list for the env (slow lookup, easy to understand), while production CL compilers use flat closure vectors with slot indices resolved at compile time (O(1) lookup).
