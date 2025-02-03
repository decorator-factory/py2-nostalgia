import pytest

from nostalgia import mild_reminiscence, nostalgia


@nostalgia
def render_point1(label: "(", x, y: ")"):
    return f"label:{label}, x:{x}, y:{y}"


@nostalgia
def render_point2(_: "{", label: ", {", x, y, z: ":height }: point }"):
    return f"label:{label}, x:{x}, y:{y}, z:{z}"


@nostalgia
def sing_song(
    _: "{(", topic1, topic2: "):first_line, (", topic3, topic4: "):second_line, {",
    vol: ":loudness", device: "}: config", max_tokens: "}", api_token):
    return (
        f"TOKEN={api_token} chatgpt "
        f"--song {topic1},{topic2},{topic3},{topic4} "
        f"--limit {max_tokens} {vol}@{device}"
    )


@mild_reminiscence("label, (x, y)")
def render_point1_mild(label, x, y):
    return f"label:{label}, x:{x}, y:{y}"


@mild_reminiscence("{label, {x, y, z:height}:point}")
def render_point2_mild(label, x, y, z):
    return f"label:{label}, x:{x}, y:{y}, z:{z}"


@mild_reminiscence("""
  {
    (topic1, topic2):first_line,
    (topic3, topic4):second_line,
    {vol:loudness, device}:config,
    max_tokens
  },
  api_token
""")
def sing_song_mild(topic1, topic2, topic3, topic4, vol, device, max_tokens, api_token):
    return (
        f"TOKEN={api_token} chatgpt "
        f"--song {topic1},{topic2},{topic3},{topic4} "
        f"--limit {max_tokens} {vol}@{device}"
    )


@pytest.mark.parametrize("fn", [render_point1, render_point1_mild])
def test_readme1(fn):
    assert fn("origin", (420, 69)) == "label:origin, x:420, y:69"


@pytest.mark.parametrize("fn", [render_point2, render_point2_mild])
def test_readme2(fn):
    assert fn({
        "label": "origin",
        "point": {"x": 420, "y": 6, "height": 9},
    }) == "label:origin, x:420, y:6, z:9"


@pytest.mark.parametrize("fn", [sing_song, sing_song_mild])
def test_readme3(fn):
    command = fn(
        {
            "first_line": ["love", "regret"],
            "second_line": ["distance", "loss"],
            "config": {
                "loudness": 11,
                "device": "obnoxious-bluetooth-speaker",
            },
            "max_tokens": 5000,
        },
        "ABCDEF",
    )
    assert command == (
        "TOKEN=ABCDEF chatgpt --song love,regret,distance,loss "
        "--limit 5000 11@obnoxious-bluetooth-speaker"
    )


def test_mild_reminiscence_detects_disorder():
    with pytest.raises(TypeError):
        @mild_reminiscence("first, { foo, bar: baz}, kamaz")
        def my_fn(first, bar, foo, kamaz):
            pass

    with pytest.raises(TypeError):
        @mild_reminiscence("first, { foo, bar: baz}, kamaz")
        def my_fn(first, kamaz, foo, bar):
            pass

    with pytest.raises(TypeError):
        @mild_reminiscence("first, { foo, bar: baz}, kamaz")
        def my_fn(first, foo, bar, baz):
            pass

    with pytest.raises(TypeError):
        @mild_reminiscence("first, { foo, bar: baz}, kamaz")
        def my_fn(first, foo, bar, almaz):
            pass
