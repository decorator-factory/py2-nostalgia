from enum import Enum
from functools import wraps
import inspect

__all__ = (
    "BadSignature",
    "TokenKind",
    "nostalgia",
    "mild_reminiscence",
    "parse_signature",
)


class BadSignature(ValueError):
    def __init__(self, token_kind, pos, explanation=""):
        self.token = token_kind
        self.pos = pos
        message = f"Invalid signature syntax: {pos=}, {token_kind=}"
        if explanation:
            message += f": {explanation}"
        super().__init__(message)


class TokenKind(Enum):
    ident = "ident"
    left_paren = "("
    right_paren = ")"
    left_brace = "{"
    right_brace = "}"
    colon = ":"
    comma = ","


def nostalgia(fn):
    fn_sig = inspect.signature(fn)
    _validate_function(fn_sig)

    text_sig = ""
    dummy_first_param = next(iter(fn_sig.parameters.values())).name == "_"
    for name, param in fn_sig.parameters.items():
        if not (name == "_" and dummy_first_param):
            text_sig += name

        if isinstance(param.annotation, str):
            text_sig += param.annotation
        text_sig += ","

    print(f"{text_sig=}")

    (_in_count, expected_param_names), converter = parse_signature(text_sig)
    if dummy_first_param:
        expected_param_names = ["_", *expected_param_names]
    _prevent_signature_mismatch(expected_param_names, fn, fn_sig)

    if dummy_first_param:
        @wraps(fn)
        def wrapper(*args):
            return fn(None, *converter(*args))
    else:
        @wraps(fn)
        def wrapper(*args):
            return fn(*converter(*args))

    return wrapper


def mild_reminiscence(text_sig):
    (_in_count, expected_param_names), converter = parse_signature(text_sig)

    def decorator(fn):
        fn_sig = inspect.signature(fn)
        _validate_function(fn_sig)
        _prevent_signature_mismatch(expected_param_names, fn, fn_sig)

        @wraps(fn)
        def wrapper(*args):
            return fn(*converter(*args))
        return wrapper

    return decorator


def _prevent_signature_mismatch(expected_param_names, fn, fn_sig):
    actual_param_names = list(fn_sig.parameters)
    if expected_param_names != actual_param_names:
        raise TypeError(
            f"Mismatched param names: signature provides {expected_param_names}, "
            f"function {fn.__qualname__} accepts {actual_param_names}"
        )


def _validate_function(fn_sig):
    for name, param in fn_sig.parameters.items():
        if param.kind not in (
            inspect.Parameter.POSITIONAL_ONLY,
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
        ):
            raise TypeError(
                "Only known positional arguments are supported. "
                f"Don't know how to handle {name!r}"
            )
        if param.default is not inspect.Parameter.empty:
            raise TypeError(
                "Defaults are not supported. "
                f"Don't know how to handle {name!r}"
            )


def parse_signature(sig):
    """
    Parse an unpacking signature (as a string).
    Returns a tuple of (transform, converter).
    - transform is a (input_argument_count, expected_function_arg_names) tuple
    - converter is a function mapping (*input_args) to a list of output args
    """

    # This part of the code is a little complicated. But in short,
    # we're keeping a stack of various states. When a sub-state (e.g. a map
    # pattern inside a list pattern) ends, it is popped from the stack and
    # somehow incorporated into the now-topmost state.
    #
    # https://en.wikipedia.org/wiki/Pushdown_automaton

    # Pat:
    #   - ("ident", str)
    #   - ("list", list[Pat])
    #   - ("map", list[tuple[str, Pat]])

    # Stack states:
    #   - {kind: "list", patterns: list[Pat]}         --
    #   - {kind: "map", keys: list[tuple[str, Pat]]}
    #   - {kind: "map_subpat_ident", key: str}        -- waiting for a ':', ',' or '}' after 'key' in '{a, b, key'
    #   - {kind: "map_subpat_complex", pattern: Pat}  -- complex pattern waiting for a ':', like '{a, b, (c, d)'
    #   - {kind: "map_subpat_colon", pattern: Pat}    -- waiting for an ident in '{a, b, (c, d):' and '{a, b, key:'

    # Example runout for `(foo, bar), {key, a: lias, {n, e}:sted}`
    # region <-- you can fold this, at least in VSCode
    #   .
    #     [(list [])]
    #
    #   (.
    #     [(list []) (list [])]
    #
    #   (foo.
    #     [(list []) (list [(ident foo)])]
    #
    #   (foo, bar.
    #     [(list []) (list [(ident foo) (ident bar)])]
    #
    #   (foo, bar), .
    #     [(list [(list [(ident foo) (ident bar)])])]
    #
    #   (foo, bar), {.
    #     [(list [#0]), (map [])]
    #
    #   (foo, bar), {key .
    #     [(list [#0]), (map []), (map_subpat_ident "key")]
    #
    #   (foo, bar), {key, .
    #     [(list [#0]), (map [("key" (ident "key"))])]
    #
    #   (foo, bar), {key, a.
    #     [(list [#0]), (map [("key" (ident "key"))]), (map_subpat_ident "a")]
    #
    #   (foo, bar), {key, a: .
    #     [(list [#0]), (map [("key" (ident "key"))]), (map_subpat_colon (ident "a"))]
    #
    #   (foo, bar), {key, a: lias, .
    #     [(list [#0]), (map [("key" (ident "key")) ("a" (ident "lias"))])]
    #
    #   (foo, bar), {key, a: lias, {.
    #     [(list [#0]), (map [#1]), (map [])]
    #
    #   (foo, bar), {key, a: lias, {.
    #     [(list [#0]), (map [#1]), (map [])]
    #
    #   (foo, bar), {key, a: lias, {n, e.  # steps skipped for brevity
    #     [(list [#0]), (map [#1]), (map [("n" (ident "n")) ("e" (ident "e"))])]
    #
    #   (foo, bar), {key, a: lias, {n, e}.
    #     [(list [#0]), (map [#1]), (map_subpat_complex (map [("n" (ident "n")) ("e" (ident "e"))]))]
    #
    #   (foo, bar), {key, a: lias, {n, e}:.
    #     [(list [#0]), (map [#1]), (map_subpat_colon (map [("n" (ident "n")) ("e" (ident "e"))]))]
    #
    #   (foo, bar), {key, a: lias, {n, e}:sted.
    #     [(list [#0]), (map [#1, ("sted" (map [("n" (ident "n")) ("e" (ident "e")]))])]
    #
    #   (foo, bar), {key, a: lias, {n, e}:sted}.
    #     [(list [#0, (map [#1, ("sted" (map [("n" (ident "n")) ("e" (ident "e")]))])])]
    #
    # endregion

    ()

    state_stack = [
        {"kind": "list", "patterns": []},
    ]

    def _pop_dict():
        state = state_stack.pop()
        if state_stack[-1]["kind"] == "list":
            state_stack[-1]["patterns"].append(("map", state["keys"]))
        elif state_stack[-1]["kind"] == "map":
            state_stack.append({"kind": "map_subpat_complex", "pattern": ("map", state["keys"])})
        else:
            assert False, state_stack

    for kind, value, pos in _tokenize_sig(sig):
        if state_stack[-1]["kind"] == "list":
            if kind is TokenKind.left_brace:
                state_stack.append({"kind": "map", "keys": []})

            elif kind is TokenKind.left_paren:
                state_stack.append({"kind": "list", "patterns": []})

            elif kind is TokenKind.right_paren:
                state = state_stack.pop()
                if not state_stack:
                    raise BadSignature(kind, pos)

                if state_stack[-1]["kind"] == "list":
                    state_stack[-1]["patterns"].append(("list", state["patterns"]))
                elif state_stack[-1]["kind"] == "map":
                    state_stack.append({"kind": "map_subpat_complex", "pattern": ("list", state["patterns"])})
                else:
                    assert False, state_stack

            elif kind is TokenKind.left_paren:
                state_stack.append({"kind": "list", "patterns": []})

            elif kind is TokenKind.ident:
                state_stack[-1]["patterns"].append(("ident", value))

            elif kind is TokenKind.comma:
                pass  # ignore for now

            else:
                raise BadSignature(kind, pos)

        elif state_stack[-1]["kind"] == "map":
            if kind is TokenKind.ident:
                state_stack.append({"kind": "map_subpat_ident", "key": value})

            elif kind is TokenKind.left_brace:
                state_stack.append({"kind": "map", "keys": []})

            elif kind is TokenKind.left_paren:
                state_stack.append({"kind": "list", "patterns": []})

            elif kind is TokenKind.right_brace:
                _pop_dict()

            elif kind is TokenKind.comma:
                pass  # ignore for now

            else:
                raise BadSignature(kind, pos)

        elif state_stack[-1]["kind"] == "map_subpat_ident":
            assert state_stack[-2]["kind"] == "map"

            if kind is TokenKind.comma:
                # {a, b, c} should be the same as {a:a, b:b, c:c}
                state = state_stack.pop()
                state_stack[-1]["keys"].append((state["key"], ("ident", state["key"])))

            elif kind is TokenKind.right_brace:
                # a } triggers popping the "map_subpat_ident" state and the underlying "map" state
                state = state_stack.pop()
                state_stack[-1]["keys"].append((state["key"], ("ident", state["key"])))
                _pop_dict()

            elif kind is TokenKind.colon:
                state = state_stack.pop()
                state_stack.append({"kind": "map_subpat_colon", "pattern": ("ident", state["key"])})

            else:
                raise BadSignature(kind, pos)

        elif state_stack[-1]["kind"] == "map_subpat_complex":
            if kind is TokenKind.colon:
                state = state_stack.pop()
                state_stack.append({"kind": "map_subpat_colon", "pattern": state["pattern"]})

            else:
                raise BadSignature(kind, pos, "expected a colon after subpattern")

        elif state_stack[-1]["kind"] == "map_subpat_colon":
            assert state_stack[-2]["kind"] == "map"

            if kind is TokenKind.ident:
                state = state_stack.pop()
                state_stack[-1]["keys"].append((value, state["pattern"]))

            else:
                raise BadSignature(kind, pos, "expected an identifier after colon")
        else:
            assert False, f"{state_stack=}"

    if len(state_stack) > 1:
        raise ValueError("You forgot to close somehting in the signature")

    patterns = state_stack[-1]["patterns"]
    in_count = len(patterns)
    expected_arg_names = list(_gather_arg_names(("list", patterns)))

    def converter(*args):
        if len(args) != len(patterns):
            raise TypeError(f"Expected {len(patterns)} positional arguments, got {len(args)}")

        out_args = []
        for i, (arg, pattern) in enumerate(zip(args, patterns)):
            out_args.extend(_unpack_pattern(arg, pattern, str(i)))
        return out_args
    return (in_count, expected_arg_names), converter


def _tokenize_sig(sig: str):
    current_token = ""
    for pos, char in enumerate(sig):
        if char in {"(", ")", "{", "}", ",", ":"}:
            if current_token:
                yield TokenKind.ident, current_token, pos - 1
                current_token = ""

            yield TokenKind(char), char, pos

        elif not char.isspace():
            current_token += char

    if current_token:
        yield TokenKind.ident, current_token, pos - 1


def _gather_arg_names(pattern):
    pat_kind, pat_value = pattern  # alas, can't use @nostalgia here!

    if pat_kind == "ident":
        yield pat_value

    elif pat_kind == "list":
        for pat in pat_value:
            yield from _gather_arg_names(pat)

    elif pat_kind == "map":
        for _key, subpat in pat_value:
            yield from _gather_arg_names(subpat)

    else:
        assert False, f"{pat_kind=}"


def _unpack_pattern(arg, pattern, path):
    pat_kind, pat_value = pattern

    if pat_kind == "ident":
        yield arg

    elif pat_kind == "list":
        items = list(arg)
        if len(items) != len(pat_value):
            raise TypeError(f"Expected {len(pat_value)} items at {path}, got {len(arg)}")
        for i, (item, subpattern) in enumerate(zip(items, pat_value)):
            yield from _unpack_pattern(item, subpattern, f"path.{i}")

    elif pat_kind == "map":
        for key, subpattern in pat_value:
            try:
                arg_value = arg[key]
            except KeyError:
                raise TypeError(f"Missing key {key!r} at {path}")
            yield from _unpack_pattern(arg_value, subpattern, f"{path}.{key!r}")

    else:
        assert False, f"{pat_kind=}"
