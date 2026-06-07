#!/usr/bin/env python3
"""
lexlisp.py -- a faithful host-language transcription of the lexically-scoped
McCarthy metacircular evaluator (the FUNARG-closure version).

Data model:
    atoms  -> Python str          ('CAR', 'A', 'FF', ...)
    NIL    -> Python None          (the empty list / false)
    conses -> Python 2-tuples      (car, cdr)
    closures are (FUNARG params body . env)  built by EVAL, never read

The five primitives (CAR CDR CONS ATOM EQ) plus QUOTE / COND / LAMBDA are
handled exactly as in the Lisp source; everything else (recursion, the Z
combinator) is plain user code. There is no DEFINE here -- expressions are
evaluated in the empty environment NIL, like the examples we traced.
"""

import sys
sys.setrecursionlimit(1_000_000)

NIL = None
def cons(a, d): return (a, d)
def car(x): return x[0]
def cdr(x): return x[1]
def atomp(x): return not isinstance(x, tuple)   # strings and None are atoms
def eq(x, y): return x == y                     # only ever called on atoms
def truthy(v): return v is not NIL              # anything but NIL is true

# --- auxiliaries: ASSOC / EVCON / PAIRLIS / EVLIS (unchanged from dynamic ver.)
def assoc(x, y):
    if y is NIL: return '*UNDEFINED'
    if eq(x, car(car(y))): return cdr(car(y))
    return assoc(x, cdr(y))

def evcon(c, a):
    if truthy(EVAL(car(car(c)), a)):
        return EVAL(car(cdr(car(c))), a)
    return evcon(cdr(c), a)

def pairlis(x, y, a):
    if x is NIL: return a
    return cons(cons(car(x), car(y)), pairlis(cdr(x), cdr(y), a))

def evlis(m, a):
    if m is NIL: return NIL
    return cons(EVAL(car(m), a), evlis(cdr(m), a))

# --- the heart: APPLY binds onto the *captured* env, never the call-time A
def APPLY(fn, x, a):
    if atomp(fn):
        if fn == 'CAR':  return car(car(x))
        if fn == 'CDR':  return cdr(car(x))
        if fn == 'ATOM': return 'T' if atomp(car(x)) else NIL
        if fn == 'CONS': return cons(car(x), car(cdr(x)))
        if fn == 'EQ':   return 'T' if eq(car(x), car(cdr(x))) else NIL
        return APPLY(EVAL(fn, a), x, a)            # symbol -> look up, re-apply
    if eq(car(fn), 'FUNARG'):
        params = car(cdr(fn))
        body   = car(cdr(cdr(fn)))
        env    = cdr(cdr(cdr(fn)))                 # <-- captured env, not A
        return EVAL(body, pairlis(params, x, env))
    raise ValueError("cannot apply: " + write(fn))

def EVAL(e, a):
    if atomp(e):
        if e is NIL: return NIL
        if e == 'T': return 'T'
        return assoc(e, a)
    if atomp(car(e)):
        h = car(e)
        if h == 'QUOTE':  return car(cdr(e))
        if h == 'COND':   return evcon(cdr(e), a)
        if h == 'LAMBDA':                           # build a closure over A
            return cons('FUNARG',
                        cons(car(cdr(e)),
                             cons(car(cdr(cdr(e))), a)))
        return APPLY(car(e), evlis(cdr(e), a), a)   # symbol operator
    return APPLY(EVAL(car(e), a), evlis(cdr(e), a), a)  # compound operator: eval it

# --- reader / writer (proper lists only; closures are never parsed) ---
def _tok(s): return s.replace('(', ' ( ').replace(')', ' ) ').split()

def _rd(t, i):
    if t[i] == '(':
        i += 1
        el = []
        while t[i] != ')':
            e, i = _rd(t, i)
            el.append(e)
        lst = NIL
        for e in reversed(el):
            lst = cons(e, lst)
        return lst, i + 1
    x = t[i]
    return (NIL if x == 'NIL' else x), i + 1

def read(s):
    e, _ = _rd(_tok(s), 0)
    return e

def write(x):
    if x is NIL: return 'NIL'
    if atomp(x): return str(x)
    parts = []
    while isinstance(x, tuple):
        parts.append(write(car(x)))
        x = cdr(x)
    return '(' + ' '.join(parts) + (')' if x is NIL else ' . ' + write(x) + ')')

def run(src, env=NIL):
    """Read one S-expression from src and evaluate it in env (default NIL)."""
    return write(EVAL(read(src), env))

# --- smoke tests --------------------------------------------------------------
if __name__ == '__main__':
    BARE = """
    ((LAMBDA (FF X) (FF FF X))
     (LAMBDA (FF X) (COND ((ATOM X) X)
                          (T (FF FF (CAR X)))))
     (QUOTE ((A) B C)))
    """

    ZCOMB = """
    (((LAMBDA (F)
        ((LAMBDA (G) (F (LAMBDA (V) ((G G) V))))
         (LAMBDA (G) (F (LAMBDA (V) ((G G) V))))))
      (LAMBDA (RECUR)
        (LAMBDA (W)
          (COND ((ATOM W) W)
                (T (RECUR (CAR W)))))))
     (QUOTE ((A) B C)))
    """

    # the original dynamic-scope trick: free FF, must fail under lexical scope
    FREE_FF = """
    ((LAMBDA (FF X) (FF X))
     (LAMBDA (X) (COND ((ATOM X) X)
                       (T (FF (CAR X)))))
     (QUOTE ((A) B C)))
    """

    print("bare self-application :", run(BARE))
    print("Z combinator          :", run(ZCOMB))
    try:
        print("free FF (dynamic only):", run(FREE_FF))
    except RecursionError:
        print("free FF (dynamic only): UNBOUND -- diverges (as expected)")
