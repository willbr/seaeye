import re
from collections import deque

# tokens are white space seprated
# newline is a token
# each line is an expression

code = """

set a 55
set b 11

set c [sum [+ a 2] [+ b 3]]

while > b 0 {
	puts b
	-= b 1
}

"""

print(code)
token_regex = re.compile(r"([\[\](),]|[^\[\](),;\s]+|;.*)")


def parse_string(code):
    lines = code.split("\n")
    while len(lines):
        line = lines.pop(0)
        tokens = token_regex.findall(line)
        if not tokens:
            continue
        cmd = tokens.pop(0)
        match cmd:
            case 'while':
                yield 'begin'
                yield '['

        if not tokens:
            yield cmd
            continue

        *middle, tail = tokens

        yield from middle
        if tail == "{":
            if cmd in ['while']:
                yield ']'
            yield cmd
            yield tail
        else:
            yield tail
            yield cmd
            assert cmd not in ['while']


def parse_inline(tokens):
    stack = []
    cmd_stack = []
    tokens = deque(tokens)
    while tokens:
        token = tokens.popleft()
        match token:
            case '[':
                cmd = tokens.popleft()
                cmd_stack.append(cmd)
            case ']':
                cmd = cmd_stack.pop()
                yield cmd
            case _:
                yield token

    assert stack == [], f'{stack=}'
    assert cmd_stack == [], f'{cmd_stack=}'


def parse(code):
    tokens = list(parse_string(code))
    #print(f'{tokens=}')
    yield from parse_inline(tokens)


rpn = list(parse(code))

expected_result = [
    "a", "55", "set",
    "b", "11", "set",
    "c", "a", "2", "+", "b", "3", "+", "sum", "set",
    "begin", "b", "0", ">", "while", "{",
        "b", "puts",
        "b", "1", "-=",
    "}",
]

#print(f'{expected_result=}')
assert rpn == expected_result, f'\n         result={rpn}'



