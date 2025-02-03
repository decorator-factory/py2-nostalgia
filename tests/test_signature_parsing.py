from types import MappingProxyType
import pytest

from nostalgia import parse_signature


def test_empty_signature():
    transform, converter = parse_signature("")
    assert transform == (0, [])
    assert [*converter()] == []

    with pytest.raises(TypeError):
        converter(1)


@pytest.mark.parametrize(
    ["sig"],
    [
        ["x"], ["x, y"], ["x, y, z"], ["x, y, z, w"],
    ]
)
def test_one_arg(sig):
    transform, converter = parse_signature(sig)
    assert transform == (sig.count(",") + 1, sig.split(", "))
    assert [*converter(*sig.split(", "))] == sig.split(", ")

    with pytest.raises(TypeError):
        converter()

    with pytest.raises(TypeError):
        converter(*sig.split(", ")[1:])

    with pytest.raises(TypeError):
        converter(*sig.split(", "), "extra")


def test_unpacking_trivial():
    transform, converter = parse_signature("()")
    assert transform == (1, [])
    # no "name bindings" are in the signature, so we don't output any args

    assert [*converter([])] == []
    assert [*converter("")] == []
    assert [*converter(map(str, []))] == []

    with pytest.raises(TypeError):
        converter()

    with pytest.raises(TypeError):
        converter("too big")

    with pytest.raises(TypeError):
        converter(42)

    with pytest.raises(TypeError):
        converter(map(str, [1, 2, 3]))


def test_sequence_unpacking_single():
    transform, converter = parse_signature("(x, y)")
    assert transform == (1, ["x", "y"])
    assert [*converter((420, 69))] == [420, 69]
    assert [*converter([420, 69])] == [420, 69]
    assert [*converter(map(lambda x: x + 1, [419, 68]))] == [420, 69]
    assert [*converter("hm")] == ["h", "m"]

    with pytest.raises(TypeError):
        converter()

    with pytest.raises(TypeError):
        converter((1, 2), 3)

    with pytest.raises(TypeError):
        converter(69_420)

    with pytest.raises(TypeError):
        converter("hmmmm")


_SIG2 = "first, (foo, bar), baz, (x, (y, z))"

@pytest.mark.parametrize(
    ["inputs", "expected"],
    [
        [
            ("a", ("b", "c"), "d", ("e", ("f", "g"))),
            ["a", "b", "c", "d", "e", "f", "g"]
        ],
        [
            ("a", map(str.lower, "BC"), "d", ("e", "fg")),
            ["a", "b", "c", "d", "e", "f", "g"]
        ],
    ],
)
def test_sequence_unpacking_nested_pass(inputs, expected):
    transform, converter = parse_signature(_SIG2)
    assert transform == (4, ["first", "foo", "bar", "baz", "x", "y", "z"])

    assert [*converter(*inputs)] == expected


@pytest.mark.parametrize(
    ["inputs"],
    [
        [()],
        [("a",)],
        [("a", ("b", "c"))],
        [("a", ("b", "c"), "d", ("e", ("f", "g")), "h")],
        [("a", ("b", "c", "x"), "d", ("e", ("f", "g")))],
        [("a", [], "d", ("e", ("f", "g")))],
        [("a", ("b", "c"), "d", ("e", ("f", "g", "h")))],
        [("a", ("b", "c"), "d", ("e", ("f", "g"), "h"))],
        [("a", ("b", "c"), "d", "help me")],

    ]
)
def test_sequence_unpacking_nested_fail(inputs):
    _, converter = parse_signature(_SIG2)

    with pytest.raises(TypeError):
        converter(*inputs)


def test_map_unpacking_trivial():
    transform, converter = parse_signature("{}")
    assert transform == (1, [])

    assert [*converter({})] == []
    assert [*converter({"ignore": "extras"})] == []
    assert [*converter("no need to verify that it's a dict")] == []

    with pytest.raises(TypeError):
        # however, we do require that the argument is provideds
        converter()

def test_map_unpacking_simple():
    transform, converter = parse_signature("{x, y, z}")
    assert transform == (1,  ["x", "y", "z"])
    assert [*converter({"x": 10, "y": 20, "z": 30})] == [10, 20, 30]
    assert [*converter({"z": 30, "x": 10, "y": 20})] == [10, 20, 30]
    assert [*converter({"z": 30, "x": 10, "hmm": 40, "y": 20})] == [10, 20, 30]

    non_dict_map = MappingProxyType({"x": 10, "z": 30, "y": 20})
    assert [*converter(non_dict_map)] == [10, 20, 30]

    with pytest.raises(TypeError):
        converter()

    with pytest.raises(TypeError):
        converter({"x": 10, "y": 20})

    with pytest.raises(TypeError):
        converter([])

    with pytest.raises(TypeError):
        converter([10, 20])

    with pytest.raises(TypeError):
        converter({10, 20, 30})


def test_combined_unpacking():
    transform, converter = parse_signature("a, b, (c, {d, e}, f), {g}")

    assert transform == (4, ["a", "b", "c", "d", "e", "f", "g"])
    assert (
        [*converter("A", "B", ("C", {"d": "D", "e": "E", "x": "y"}, "F"), {"g": "G", "h": "H"})]
        == ["A", "B", "C", "D", "E", "F", "G"]
    )


def test_map_unpacking_alias():
    transform, converter = parse_signature("{x: a, y: b, z, w: c}")
    assert transform == (1, ["x", "y", "z", "w"])
    assert [*converter({"a": 10, "b": 20, "z": 30, "c": 40})] == [10, 20, 30, 40]
    assert [*converter({"b": 20, "c": 40, "z": 30, "a": 10})] == [10, 20, 30, 40]

    with pytest.raises(TypeError):
        converter()

    with pytest.raises(TypeError):
        converter({"x": 10, "y": 20, "z": 30, "w": "40"})


def test_nested_map_unpacking():
    transform, converter = parse_signature("{label, {x, ypos:y}:point}")
    assert transform == (1, ["label", "x", "ypos"])
    assert [*converter({"label": "hello", "point": {"x": 5, "y": 10}})] == ["hello", 5, 10]

    with pytest.raises(TypeError):
        converter()

    for invalid in [
        {"label": "hello"},
        {"label": "hello", "point": {}},
        {"label": "hello", "point": {"x": 5}},
        {"label": "hello", "point": {"x": 5, "ypos": 10}},
    ]:
        with pytest.raises(TypeError):
            converter(invalid)


def test_list_in_map_unpacking():
    transform, converter = parse_signature("{ label, (x, y):point }")
    assert transform == (1, ["label", "x", "y"])
    assert [*converter({"label": "hello", "point": (420, 69)})] == ["hello", 420, 69]

    with pytest.raises(TypeError):
        converter()

    for invalid in [
        {"label": "hello"},
        {"label": "hello", "point": 42},
        {"label": "hello", "point": [420]},
        {"label": "hello", "point": [420, 60, 9]},
    ]:
        with pytest.raises(TypeError):
            converter(invalid)



def test_complex_mixed_signature():
    transform, converter = parse_signature(
        "{ label, "
        "(x, y):point, }, "
        "plain_arg, "
        "({{{{impostor}:third, other}:second}:first}, "
        "((huh)))"
    )
    assert transform == (
        3,
        ["label", "x", "y", "plain_arg", "impostor", "other", "huh"],
    )
    assert [*converter(
        {"label": "HELLO", "point": (420, 69)},
        "PLAIN",
        (
            {"first": {"second": {"third": {"impostor": "SUS"}, "other": "OTHER"}}},
            [["HUH"]],
        )
    )] == ["HELLO", 420, 69, "PLAIN", "SUS", "OTHER", "HUH"]



@pytest.mark.parametrize(
    ["sig", "input_args", "expected_output_args"],
    [
        (
            "",
            [],
            [],
        ),
        (
            "()",
            [()],
            [],
        ),
        (
            "x",
            ["X"],
            ["x"],
        ),
        (
            "x, y",
            ["X", "Y"],
            ["x", "y"],
        ),
        (
            "x, (y, z)",
            ["X", ["Y", "Z"]],
            ["x", "y", "z"],
        ),
        (
            "x, (y, {a, b}), {c, d}, e",
            ["X", ["Y", {"a": 1, "b": 2}], {"c": 3, "d": 4}, "E"],
            ["x", "y", "a", "b", "c", "d", "e"],
        )
    ]
)
def test_transform_reflects_transform(sig, input_args, expected_output_args):
    (in_count, out_args), converter = parse_signature(sig)
    assert in_count == len(input_args)
    assert out_args == expected_output_args
    assert len(converter(*input_args)) == len(out_args)
