from rich.traceback import install
install(show_locals=True)

from rich.console import Console
console = Console()

python_print = print
print = console.print

print('hi\n')

with open('neo.ci') as f:
	code = f.read()

print(code)

import re
import json

class Token:
    def __init__(self, type_, value=None):
        self.type = type_
        self.value = value

    def __repr__(self):
        return f"Token({self.type}, {repr(self.value)})"

def tokenize(code):
    token_specification = [
        ("LPAREN", r"[(]"),
        ("RPAREN", r"[)]"),
        ("DOT", r"[.]"),
        ("COMMA", r"[,]"),
        ("WORD", r'[^(),\s]+'),
        ("STRING1", r'"[^"]*"'),
        ("STRING2", r"'[^']*'"),
        ("COMMENT", r'#.*'),
        ("NEWLINE", r'\n'),
        ("WHITESPACE", r'[ \t]+'),
        ("ERROR", r'.*\S+'),
    ]
    token_regex = '|'.join(f'(?P<{name}>{pattern})' for name, pattern in token_specification)

    # Track the previous indentation level
    prev_indent_level = 0
    indent_stack = [0]  # Stack to keep track of indentation levels

    for match in re.finditer(token_regex, code):
        kind = match.lastgroup
        value = match.group()
        
        if kind == "NEWLINE":
            # Lookahead to find the next non-whitespace token's indentation
            next_non_ws = re.match(r'[ \t]*', code[match.end():])
            indent_level = len(next_non_ws.group(0))

            if indent_level > indent_stack[-1]:
                indent_stack.append(indent_level)
                yield Token("INDENT")
            while indent_level < indent_stack[-1]:
                indent_stack.pop()
                yield Token("DEDENT")
                
            yield Token(kind, value)  # Emit NEWLINE token
        elif kind == "SKIP":
            continue  # Ignore spaces and tabs outside of newline handling
        else:
            yield Token(kind, value)

    # Emit DEDENT tokens if needed at EOF
    while len(indent_stack) > 1:
        indent_stack.pop()
        yield Token("DEDENT")

tokens = list(tokenize(code))


indent = 0
for token in tokens:
    indent_string = '    ' * indent
    print(f'{indent_string} {token}')
    if token.type == 'INDENT':
        indent += 1
    elif token.type == 'DEDENT':
        indent -= 1
    elif token.type == 'NEWLINE':
        print()


class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.current_token_index = 0

    def parse(self):
        ast = []

        self.consume_comments_and_newlines()
        while not self.end_of_tokens():
            ast.append(self.parse_statement())
            self.consume_comments_and_newlines()
            #print(json.dumps(ast['body'], indent=4))
        return ast

    def parse_statement(self):

        if self.end_of_tokens():
            assert False
            return None

        cmd = self.consume('WORD').value

        args  = []
        block = []

        while self.current_token().type not in ['NEWLINE', 'INDENT', 'DEDENT']:
            sub_expr = self.parse_expression()
            args.append(sub_expr)

        #print(args)
        if self.current_token().type == 'INDENT':
            block = self.consume_block()

        expr = [cmd, args, block]

        return expr

    def parse_expression(self):
        cmd = self.consume('WORD').value

        if self.current_token().type != 'LPAREN':
            return cmd

        _ = self.consume('LPAREN')

        if self.current_token().type == 'INDENT':
            args = self.consume_paren_block()
            block = []
            expr = [cmd, args, block]
            return expr

        arg = ['infix']
        args = [arg]

        while self.current_token().type != 'RPAREN':
            t = self.consume(None)
            if t.type == 'COMMA':
                assert len(arg)
                args.append(arg)
                arg = ['infix']
            else:
                arg.append(t.value)

        if arg:
            args.append(arg)


        _ = self.consume('RPAREN')

        block = []
        expr = [cmd, args, block]
        return expr

    def current_token(self):
        return self.tokens[self.current_token_index]

    def consume_block(self):
        block = []
        _ = self.consume('INDENT')
        while self.current_token().type != 'DEDENT':
            self.consume_comments_and_newlines()
            expr = self.parse_expression()
            block.append(expr)
            #print(block)
            
        _ = self.consume('DEDENT')

        return block

    def consume_paren_block(self):
        block = []
        _ = self.consume('INDENT')
        while True:
            self.consume_comments_and_newlines()
            self.consume_whitespace()
            if self.current_token().type in ['DEDENT', 'RPAREN']:
                break
            t = self.current_token()
            statement = self.parse_statement()
            print(statement)
            block.append(statement)
            #print(block)
            
        t = self.current_token()
        _ = self.consume('RPAREN')
        _ = self.consume('DEDENT')

        return block

    def consume_comments_and_newlines(self):
        while not self.end_of_tokens():
            if self.current_token().type in ["COMMENT", 'NEWLINE']:
                _ = self.consume(None)
                #print(f'skip {_}')
            else:
                break

    def consume(self, expected_type, expected_value=None, skip_whitespace=True):
        if skip_whitespace:
            self.consume_whitespace()

        token = self.current_token()
        #print(f'{token=}')
        if token.type == expected_type and (expected_value is None or token.value == expected_value):
            self.current_token_index += 1
            return token
        elif expected_type is None:
            self.current_token_index += 1
            return token
        else:
            raise Exception(f"Expected token {expected_type} but got {token.type}")

    def consume_whitespace(self):
        while not self.end_of_tokens() and self.current_token().type == 'WHITESPACE':
            self.current_token_index += 1

    def end_of_tokens(self):
        return self.current_token_index >= len(self.tokens)

parser = Parser(tokens)
ast = parser.parse()

print(json.dumps(ast, indent=4))

