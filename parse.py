from rich.traceback import install
install(show_locals=True)

from rich.console import Console
console = Console()

python_print = print
print = console.print


import re
import json

debugging = True

print('hi\n')

with open('while.ci') as f:
	code = f.read()

print(code)

class Token:
    def __init__(self, type_, value=None):
        self.type = type_
        self.value = value

    def __repr__(self):
        return f"Token({self.type}, {repr(self.value)})"

def tokenize(code):
    token_specification = [
        ("STRING1", r'"[^"]*"'),
        ("STRING2", r"'[^']*'"),
        ("LPAREN", r"[(]"),
        ("RPAREN", r"[)]"),
        ("DOT", r"[.]"),
        ("COMMA", r"[,]"),
        ("WORD", r'[^(),\s]+'),
        ("COMMENT", r'#.*'),
        ("NEWLINE", r'\n'),
        ("WHITESPACE", r'[ \t]+'),
        ("ERROR", r'.*\S+'),
    ]
    token_regex = '|'.join(f'(?P<{name}>{pattern})' for name, pattern in token_specification)

    for match in re.finditer(token_regex, code):
        kind = match.lastgroup
        value = match.group()
        yield Token(kind, value)


def print_tokens(tokens):
    print()
    print('*'*40)
    print()
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
    print('*'*40)
    print()

tokens1 = list(tokenize(code))
#print_tokens(tokens1)


def strip_empty_lines(input_tokens):
    i = 0
    previous_token_type = None
    while i < len(input_tokens):
        t = input_tokens[i]
        i += 1
        yield t
        if t.type == 'NEWLINE':
            while i < len(input_tokens):
                t = input_tokens[i]
                if t.type != 'NEWLINE':
                    break
                i += 1

tokens2 = list(strip_empty_lines(tokens1))
print_tokens(tokens2)

def parse_indentation(input_tokens):
    indent_stack = [0]  # Stack to keep track of indentation levels

    i = 0
    while i < len(input_tokens):
        token = input_tokens[i]
        i += 1
        if token.type != 'NEWLINE':
            yield token
            continue

        if i == len(input_tokens):
            break

        token = input_tokens[i]
        i += 1

        if token.type == 'WHITESPACE':
            indent_level = len(token.value)
        else:
            indent_level = 0

        if indent_level > indent_stack[-1]:
            indent_stack.append(indent_level)
            yield Token("INDENT")
        while indent_level < indent_stack[-1]:
            indent_stack.pop()
            yield Token("DEDENT")

        yield token

    while len(indent_stack) > 1:
        indent_stack.pop()
        yield Token("DEDENT")

tokens3 = list(parse_indentation(tokens2))
#tokens2 = tokens1
print_tokens(tokens3)
exit()

def remove_empty_lines(input_tokens):
    i = 0
    stack = []
    tokens = []
    dedents  = 0
    newlines = 0
    indents  = 0

    while i < len(input_tokens):
        next_token = input_tokens[i]
        i += 1

        if next_token.type in 'DEDENT':
            dedents += 1
            stack.append(next_token)
        if next_token.type in 'NEWLINE':
            newlines += 1
            stack.append(next_token)
        elif next_token.type == 'INDENT':
            indents += 1
            stack.append(next_token)
        elif stack:
            diff = indents - dedents
            if diff == 0:
                pass
            else:
                tokens.extend(stack)
            tokens.append(next_token)
            stack = []
            dedents  = 0
            newlines = 0
            indents  = 0
        else:
            tokens.append(next_token)

        # merge indents and newlines?
        # remove duplicates
        # skip empty lines?

    return tokens

#tokens2 = remove_empty_lines(tokens1)

tokens = tokens2

#assert False

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
        self.consume_whitespace()
        if self.current_token().type not in ['WORD', 'STRING1', 'STRING2']:
            t = self.current_token()
            assert False

        cmd = self.consume(None).value

        if self.current_token().type != 'LPAREN':
            return cmd

        _ = self.consume('LPAREN')

        if self.current_token().type == 'INDENT':
            args = self.consume_paren_block()
            block = []
            expr = [cmd, args, block]
            return expr

        args = []

        while True:
            t = self.current_token()
            if t.type == 'RPAREN':
                _ = self.consume('RPAREN')
                break

            arg_expr = self.parse_expression()
            args.append(arg_expr)

            t = self.current_token()
            if t.type == 'COMMA':
                _ = self.consume('COMMA')

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
            expr = self.parse_statement()
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
            #print(statement)
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

