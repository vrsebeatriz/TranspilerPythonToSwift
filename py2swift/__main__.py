import sys
from pathlib import Path
from .transpiler import transpile_source


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    if not argv:
        print("Usage: python -m py2swift <input.py> [output.swift] [--emit-runtime]")
        return 1
    emit_runtime = False
    args = [a for a in argv if a != "--emit-runtime"]
    if "--emit-runtime" in argv:
        emit_runtime = True
    native_mode = False
    if "--native" in argv:
        native_mode = True
        args = [a for a in args if a != "--native"]
    inp = Path(args[0])
    if not inp.exists():
        print(f"Input file not found: {inp}")
        return 2
    out = Path(args[1]) if len(args) > 1 else inp.with_suffix('.swift')
    src = inp.read_text(encoding='utf-8')
    swift = transpile_source(src, native=native_mode)
    out.write_text(swift, encoding='utf-8')
    print(f"Wrote: {out}")
    if emit_runtime:
        # write a small runtime helper next to the output
        runtime = Path(__file__).parent / "templates" / "py_runtime.swift"
        if runtime.exists():
            r_out = out.with_name("PyRuntime.swift")
            r_out.write_text(runtime.read_text(encoding='utf-8'), encoding='utf-8')
            print(f"Wrote runtime helpers: {r_out}")
        else:
            print("Runtime template not found in package templates.")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
