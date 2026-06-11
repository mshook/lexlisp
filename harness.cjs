// Headless verification harness for the lexical lisp.js.
// Loads the real (edited) shared core + JS host fns from lisp.js, then runs a
// DOM-free REPL loop that mirrors Lisp() over lexical-tests.lisp.
const fs = require('fs');
const lisp = fs.readFileSync(__dirname + '/lisp.js', 'utf8');
globalThis.__PROG = fs.readFileSync(process.argv[2] || __dirname + '/lexical-tests.lisp', 'utf8');

const driver = `
;(function () {
  function runProgram(s) {
    Reset();
    funcall = Funcall;            // SetUp() normally does this; no DOM here
    output = "";
    Load(s);
    while (dx) {
      if (dx <= Ord(' ')) {
        ReadChar();
      } else {
        var A = cx, x;
        try {
          x = Read();
          if (x < 0 && Car(x) == kDefine) {
            g = Define(Cons(Car(Cdr(x)), Eval(Cdr(Cdr(x)), 0)), g);
            continue;
          }
          x = Eval(x, 0);
        } catch (z) {
          PrintChar(Ord('?'));
          x = z;
        }
        Print(x);
        PrintChar(Ord('\\n'));
        Gc(A, 0);
      }
    }
    return output;
  }
  globalThis.__OUT = runProgram(globalThis.__PROG);
})();
`;

eval(lisp + driver);
process.stdout.write(globalThis.__OUT);
