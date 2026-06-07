# Substitution vs Environment Models and Lexical Scope

Pure substitution is *inherently* lexically scoped. Beta reduction is the definitional semantics of lexical scope.

When you apply `(λx. body) v` under substitution, you replace the free occurrences of `x` in `body` with `v` — "free" meaning not shadowed by an inner binding. That structure-respecting replacement is exactly what lexical scope means: the binding site in the source text determines what `x` refers to, full stop. There's no environment, no call stack, nothing to go wrong.

Dynamic scope is actually harder to express with substitution — you'd need extra machinery to thread a runtime context through. The environment model made dynamic scope fall out *accidentally* in McCarthy's eval because `PAIRLIS` extended the call-time `a` rather than the definition-time one.

So the historical irony is:

- **Lambda calculus (Church)**: substitution model → lexical scope, naturally
- **McCarthy's eval (1960)**: environment model → dynamic scope, accidentally
- **lexlisp.py**: environment model → lexical scope, by fixing the FUNARG bug

The environment model is an *optimization* of substitution — instead of rewriting the expression, you defer name resolution and look it up. For pure code they're equivalent. The price of that optimization is that you have to be careful about *which* environment you extend, which is exactly the mistake McCarthy's original made.
