# `py2-nostalgia`

(not to be confused with the PyPI project `nostalgia` which appears to do something useful)

Do you ever miss the ability to unpack function arguments right in the signature? Like in the good old Python 2 days?

```py
def print_point(label, (x, y)):
    print "({0},{1}; label={2})".format(x, y, label)

print_point("origin", (420, 69))
```

Say no more, as this package lets you do exactly that. With the power of PEP 3107 annotations!

```py
from nostalgia import nostalgia

@nostalgia
def print_point(label: "(", x, y: ")"):
    print(f"({x},{y}; label={label}")

print_point("origin", (420, 69))
```

On top of that, you can destructure dictionaries:

```py
from nostalgia import nostalgia

@nostalgia
def print_point(_: "{", label: ", {", x, y, z: ":height }: point }"):
    print(f"label:{label}, x:{x}, y:{y}, z:{z}")

print_point({"label": "origin", "point": {"x": 420, "y": 6, "height": 9}})
```

If the first parameter is named `_`, it is ignored. This lets you add something to the start of the
unpacking signature, as you can see above.

Of course, nobody is working with points or labels nowadays. Let's take a look at a more realistic example.

# Leveraging the `@nostalgia` decorator for AI-powered workflows in the cloud

```py
from aiosky import the_cloud

@nostalgia
async def sing_song(
    _: "{(", topic1, topic2: "):first_line, (", topic3, topic4: "):second_line, {", vol: ":loudness", device: "}: config", max_tokens: "}", api_token):
    await the_cloud.leverage(
        "chatgpt "
        f"--song {topic1},{topic2},{topic3},{topic4} "
        f"--limit {max_tokens} {vol}@{device}",
        token=api_token
    )

# Call:

prompt = {
    "first_line": ["love", "regret"],
    "second_line": ["distance", "loss"],
    "config": {
        "loudness": 11,
        "device": "obnoxious-bluetooth-speaker",
    },
    "max_tokens": 5000,
}
await sing_song(prompt, "ABCDEF")

```

# Keeping track of work-life balance and mental health while using the `py2-nostalgia` library

If you are not ready to go completely insane, you can use the `mild_reminiscence`
decorator factory instead of the `nostalgia` decorator.

```py
from nostalgia import mild_reminiscence

@mild_reminiscence("label, (x, y)")
def print_point1(label, x, y):
    ...


@mild_reminiscence("{label, {x, y, z:height}:point}")
def print_point2(label, x, y, z):
    ...


@mild_reminiscence("""
  {
    (topic1, topic2):first_line,
    (topic3, topic4):second_line,
    {vol:loudness, device}:config,
    max_tokens
  },
  api_token
""")
async def sing_song(topic1, topic2, topic3, topic4, vol, device, max_tokens, api_token):
    ...

```

# Installation

```
pip install git+https://github.com/decorator-factory/py2-nostalgia
```

_(please don't actually use this)_

