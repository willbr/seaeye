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

with open('comments.ci') as f:
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
        ("COMMENT", r'#.*'),
        ("STRING1", r'"[^"]*"'),
        ("STRING2", r"'[^']*'"),
        ("LPAREN", r"[(]"),
        ("RPAREN", r"[)]"),
        ("DOT", r"[.]"),
        ("COMMA", r"[,]"),
        ("WORD", r'[^#(),.\s]+'),
        ("NEWLINE", r'\n'),
        ("WHITESPACE", r'[ \t]+'),
        ("ERROR", r'.*\S+'),
    ]
    token_regex = '|'.join(f'(?P<{name}>{pattern})' for name, pattern in token_specification)

    for match in re.finditer(token_regex, code):
        kind = match.lastgroup
        value = match.group()
        yield Token(kind, value)


def print_tokens(tokens, header=None):
    print()
    print('*'*40)
    if header:
        print(f'    {header}')
        print('*'*40)
    print()
    indent = 0
    i = 0
    for token in tokens:
        indent_string = '    ' * indent
        print(f'{i} {indent_string} {token}')
        if token.type == 'INDENT':
            indent += 1
        elif token.type == 'DEDENT':
            indent -= 1
        elif token.type == 'NEWLINE':
            print()
        i += 1
    print('*'*40)
    print()

tokens1 = list(tokenize(code))
print_tokens(tokens1)


# TODO move this into the tokeniser with a regex?
def strip_whitespace_from_the_end_of_lines(input_tokens):
    i = 0
    while i < len(input_tokens):
        token = input_tokens[i]
        i += 1

        if token.type == 'WHITESPACE':
            next_token = input_tokens[i]
            if next_token.type in ['COMMENT', 'NEWLINE']:
                continue
        yield token

tokens2 = list(strip_whitespace_from_the_end_of_lines(tokens1))
#print_tokens(tokens2, 'striped eol whitespace')

def strip_empty_lines(input_tokens):
    i = 0
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

tokens3 = list(strip_empty_lines(tokens2))
#print_tokens(tokens3, header='strip empty lines')

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

        next_token = input_tokens[i]

        if next_token.type == 'WHITESPACE':
            i += 1
            indent_level = len(next_token.value)
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

tokens4 = list(parse_indentation(tokens3))
#tokens2 = tokens1
#print_tokens(tokens4, header='indent')
#exit()

tokens = tokens4

#assert False

infix_words = [
        '=',
        '+', '+=',
        '-', '-=',
        '*', '*=',
        '/', '/=',
        ]

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

        cmd = self.parse_expression()

        args  = []
        block = []

        while self.current_token().type not in ['NEWLINE', 'INDENT', 'DEDENT', 'EOF']:
            sub_expr = self.parse_expression()
            args.append(sub_expr)

        #print(args)
        if self.current_token().type == 'INDENT':
            block = self.consume_block()

        if len(args):
            first_arg = args[0]
            if first_arg in infix_words:
                assert block == []
                expr = ['infix', [cmd, *args], block]
                return expr

        expr = [cmd, args, block]

        return expr

    def parse_infix_expression(self):
        args = []
        while self.current_token().type not in ['RPAREN', 'COMMA']:
            sub_expr = self.parse_expression()
            args.append(sub_expr)

        if len(args) == 1:
            return args[0]

        expr = ['infix', args, []]
        return expr

    def parse_expression(self):
        self.consume_whitespace()

        t = self.current_token()

        if t.type == 'LPAREN':
            _ = self.consume('LPAREN')
            expr = self.parse_infix_expression()
            _ = self.consume('RPAREN')
            return expr


        if t.type == 'COMMENT':
            expr = ['comment', t.value, []]
            return expr

        if t.type not in ['WORD', 'STRING1', 'STRING2']:
            assert False

        cmd = self.consume(None).value

        attributes = []
        while self.current_token().type == 'DOT':
            _ = self.consume('DOT')
            attribute = self.consume('WORD').value
            attributes.append(attribute)

        if attributes:
            cmd = ['attr', [cmd, *attributes], []]


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

            arg_expr = self.parse_infix_expression()
            args.append(arg_expr)

            t = self.current_token()
            if t.type == 'COMMA':
                _ = self.consume('COMMA')

        block = []
        expr = [cmd, args, block]
        return expr

    def current_token(self):
        try:
            t = self.tokens[self.current_token_index]
        except IndexError:
            t = Token('EOF')
        return t


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

#print(json.dumps(ast, indent=4))

def dumps(ast):
    lines = dump_block(ast, 'module', 0)
    print('\n'.join(lines))

def dump_block(block, context, indent):
    lines = []
    for statement in block:
        s = dump_statement(statement, context, indent)
        s2 = '\n'.join(s)
        lines.append(s2)
    return lines

def dump_statement(ast, context, indent):
    cmd, args, block = ast

    if cmd == 'attr':
        assert False
    elif cmd == 'infix':
        cmd_string = ''
        args_string = dump_args(args, ' ', 'infix', indent)
        assert block == []
    else:
        cmd_string = dump_expr(cmd, 'statement', indent)
        args_string = dump_args(args, ' ', 'statement', indent)

    indent_string = '    ' * indent
    if cmd_string:
        expr_string = f'{cmd_string} {args_string}'
    else:
        expr_string = args_string

    lines = [f'{indent_string}{expr_string}']
    for sub_statement in block:
        sub_statement_string = dump_statement(sub_statement, context, indent+1)
        lines.append('\n'.join(sub_statement_string))
    return lines

def dump_attr(expr, indent):
    cmd, args, block = expr
    assert cmd == 'attr'
    assert block == []
    s = dump_args(args, '.', 'attr', indent)
    return s

def dump_expr(expr, context, indent):
    if not isinstance(expr, list):
        return str(expr)

    cmd, args, block = expr
    assert block == []

    if cmd == 'attr':
        return dump_attr(expr, indent)
    elif cmd == 'infix':
        args_string = dump_args(args, ' ', 'infix', indent)
        assert block == []
        if context == 'infix':
            return f'({args_string})'
        else:
            return args_string
    else:
        cmd_string = dump_expr(cmd, context, indent)
        args_string = dump_args(args, ', ', 'neoteric', indent)
        return f'{cmd_string}({args_string})'

def dump_args(args, sep, context, indent):
    has_named_args = False
    for arg in args:
        if not isinstance(arg, list):
            continue
        cmd = arg[0]
        if cmd != 'infix':
            continue
        op = arg[1][1]
        if op == '=':
            has_named_args = True
            break
        #print(arg[1][1])

    if has_named_args:
        indent_string = '    ' * (indent + 1)
        lines =  dump_block(args, context, indent+1)
        return '\n' + '\n'.join(lines) + f'\n{indent_string}'

    return sep.join(dump_expr(a, context, indent) for a in args)

print('*'*40)
print()
dumps(ast)
print()

