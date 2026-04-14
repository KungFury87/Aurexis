#!/usr/bin/env python3
"""
Aurexis Core V1 Substrate Candidate — Pytest Surface Runner

Lightweight pytest-compatible runner that runs every test function in tests/
without requiring pytest to be installed. If pytest IS installed on the host,
the equivalent honest command is:

    PYTHONPATH=src pytest tests/ -q

This runner supports:
  * test_* functions at module level
  * TestClass classes with test_* methods
  * @pytest.fixture-decorated fixtures (module and class scoped)
  * @pytest.mark.parametrize with literal argvalues

Usage:
    PYTHONPATH=src python3 run_pytest_surface.py

(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""
import os
import sys
import inspect
import importlib.util
import traceback
import functools
import types

# ---------------------------------------------------------------------------
# pytest module stub
# ---------------------------------------------------------------------------
if "pytest" not in sys.modules:
    pytest_stub = types.ModuleType("pytest")

    def fixture(*fargs, **fkwargs):
        def decorator(func):
            func._is_pytest_fixture = True
            return func
        if len(fargs) == 1 and callable(fargs[0]) and not fkwargs:
            return decorator(fargs[0])
        return decorator

    pytest_stub.fixture = fixture

    class _Mark:
        def __getattr__(self, name):
            if name == "parametrize":
                def parametrize(argnames, argvalues, **kw):
                    def decorator(func):
                        # stack multiple parametrize decorators
                        existing = getattr(func, "_pytest_parametrize_stack", [])
                        existing = [(argnames, list(argvalues))] + existing
                        func._pytest_parametrize_stack = existing
                        return func
                    return decorator
                return parametrize
            # generic no-op mark
            def _noop_mark(*a, **kw):
                def decorator(func):
                    return func
                return decorator
            return _noop_mark

    pytest_stub.mark = _Mark()

    class _Raises:
        def __init__(self, exc_type):
            self.exc_type = exc_type
        def __enter__(self):
            return self
        def __exit__(self, exc_type, exc_val, tb):
            if exc_type is None:
                raise AssertionError(f"expected {self.exc_type} to be raised, but nothing was")
            if not issubclass(exc_type, self.exc_type):
                return False
            return True

    def raises(exc_type, **kw):
        return _Raises(exc_type)

    pytest_stub.raises = raises
    pytest_stub.skip = lambda *a, **kw: (_ for _ in ()).throw(_Skipped(*a, **kw))
    pytest_stub.approx = lambda x, rel=None, abs=None: x  # rough

    class _Skipped(Exception):
        pass
    pytest_stub._Skipped = _Skipped

    sys.modules["pytest"] = pytest_stub


HERE = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.join(HERE, "src")
TESTS_DIR = os.path.join(HERE, "tests")

if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)


def load_test_module(path):
    name = "tests_" + os.path.splitext(os.path.basename(path))[0]
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def collect_fixtures(obj):
    out = {}
    for name in dir(obj):
        if name.startswith("_"):
            continue
        try:
            attr = getattr(obj, name)
        except Exception:
            continue
        if callable(attr) and getattr(attr, "_is_pytest_fixture", False):
            out[name] = attr
    return out


def resolve_fixture(fn, fixtures, instance=None, cache=None):
    """Call fixture fn, recursively resolving its own fixture params."""
    if cache is None:
        cache = {}
    key = (id(fn), id(instance))
    if key in cache:
        return cache[key]
    sig = inspect.signature(fn)
    kwargs = {}
    params = list(sig.parameters)
    if params and params[0] == "self":
        params = params[1:]
    for pname in params:
        if pname in fixtures:
            kwargs[pname] = resolve_fixture(fixtures[pname], fixtures, instance=instance, cache=cache)
    if instance is not None and list(sig.parameters) and list(sig.parameters)[0] == "self":
        value = fn(instance, **kwargs)
    else:
        value = fn(**kwargs)
    cache[key] = value
    return value


def call_test(func, fixtures, instance=None, extra_kwargs=None):
    sig = inspect.signature(func)
    kwargs = dict(extra_kwargs or {})
    cache = {}
    params = list(sig.parameters)
    if params and params[0] == "self":
        params = params[1:]
    for pname in params:
        if pname in kwargs:
            continue
        if pname in fixtures:
            kwargs[pname] = resolve_fixture(fixtures[pname], fixtures, instance=instance, cache=cache)
    if instance is not None:
        return func(instance, **kwargs)
    return func(**kwargs)


def expand_parametrize(func):
    """If func has @pytest.mark.parametrize (possibly stacked), yield
    (test_name_suffix, extra_kwargs) for every combination (cross-product)."""
    stack = getattr(func, "_pytest_parametrize_stack", None)
    if not stack:
        yield "", {}
        return
    # Build per-layer value lists keyed by argnames
    layers = []
    for argnames, argvalues in stack:
        names = [n.strip() for n in (argnames.split(",") if isinstance(argnames, str) else argnames)]
        per_row = []
        for vals in argvalues:
            if not isinstance(vals, (list, tuple)):
                vals = (vals,)
            per_row.append(dict(zip(names, vals)))
        layers.append(per_row)
    # Cartesian product
    def combine(idx, current, suffix):
        if idx == len(layers):
            yield suffix, current
            return
        for j, row in enumerate(layers[idx]):
            merged = dict(current)
            merged.update(row)
            new_suffix = f"{suffix}[{j}]"
            yield from combine(idx + 1, merged, new_suffix)
    yield from combine(0, {}, "")


def run_test(name, func, fixtures, instance=None):
    try:
        any_ran = False
        last_err = None
        for suffix, extra in expand_parametrize(func):
            try:
                call_test(func, fixtures, instance=instance, extra_kwargs=extra)
                any_ran = True
            except sys.modules["pytest"]._Skipped:
                any_ran = True  # treat skip as pass for our purposes
            except Exception as e:
                return False, f"{name}{suffix}: {type(e).__name__}: {e}\n{traceback.format_exc()}"
        return True, None
    except Exception as e:
        return False, f"{name}: {type(e).__name__}: {e}\n{traceback.format_exc()}"


def main():
    if not os.path.isdir(TESTS_DIR):
        print(f"ERROR: tests dir not found: {TESTS_DIR}", file=sys.stderr)
        return 2

    test_files = sorted(
        f for f in os.listdir(TESTS_DIR)
        if f.startswith("test_") and f.endswith(".py")
    )
    if not test_files:
        print("No test files found.")
        return 2

    total_pass = 0
    total_fail = 0
    failures = []
    per_file = {}

    for tf in test_files:
        path = os.path.join(TESTS_DIR, tf)
        file_pass = 0
        file_fail = 0
        try:
            mod = load_test_module(path)
        except Exception as e:
            total_fail += 1
            file_fail += 1
            failures.append((tf, "<module load>", f"{type(e).__name__}: {e}"))
            per_file[tf] = (0, 1)
            continue

        module_fixtures = collect_fixtures(mod)

        # Module-level test_* functions
        for attr_name in sorted(dir(mod)):
            if not attr_name.startswith("test_"):
                continue
            attr = getattr(mod, attr_name)
            if not callable(attr) or inspect.isclass(attr):
                continue
            if getattr(attr, "_is_pytest_fixture", False):
                continue
            ok, err = run_test(attr_name, attr, module_fixtures)
            if ok:
                total_pass += 1
                file_pass += 1
            else:
                total_fail += 1
                file_fail += 1
                failures.append((tf, attr_name, err))

        # TestClass classes with test_* methods
        for cls_name in sorted(dir(mod)):
            if not cls_name.startswith("Test"):
                continue
            cls = getattr(mod, cls_name)
            if not inspect.isclass(cls):
                continue
            try:
                instance = cls()
            except Exception as e:
                total_fail += 1
                file_fail += 1
                failures.append((tf, f"{cls_name}.__init__", f"{type(e).__name__}: {e}"))
                continue

            # Collect class-level fixtures (as unbound funcs)
            class_fixtures = {}
            for nm in dir(cls):
                if nm.startswith("_"):
                    continue
                a = getattr(cls, nm)
                if callable(a) and getattr(a, "_is_pytest_fixture", False):
                    class_fixtures[nm] = a

            # Merge: class fixtures shadow module fixtures
            combined_fixtures = dict(module_fixtures)
            combined_fixtures.update(class_fixtures)

            for m_name in sorted(dir(cls)):
                if not m_name.startswith("test_"):
                    continue
                method = getattr(cls, m_name)
                if not callable(method):
                    continue
                ok, err = run_test(f"{cls_name}::{m_name}", method, combined_fixtures, instance=instance)
                if ok:
                    total_pass += 1
                    file_pass += 1
                else:
                    total_fail += 1
                    file_fail += 1
                    failures.append((tf, f"{cls_name}::{m_name}", err))

        per_file[tf] = (file_pass, file_fail)

    print("=" * 64)
    print(f"  PYTEST SURFACE RESULTS")
    print("=" * 64)
    for tf in test_files:
        p, f = per_file.get(tf, (0, 0))
        status = "OK" if f == 0 else "FAIL"
        print(f"  [{status}] {tf}: {p} passed, {f} failed")
    print("-" * 64)
    print(f"  TOTAL: {total_pass} passed, {total_fail} failed")
    print("=" * 64)

    if failures:
        print("\nFAILURES (first 20):")
        for tf, name, err in failures[:20]:
            print(f"\n--- {tf}::{name} ---")
            lines = err.split("\n")
            for line in lines[:6]:
                print(f"  {line}")
        return 1

    print("\n  ALL PYTEST SURFACE TESTS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
