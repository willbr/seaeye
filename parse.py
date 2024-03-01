from rich.traceback import install
install(show_locals=True)

from rich.console import Console
console = Console()

python_print = print
print = console.print
from pprint import pprint


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
#print_tokens(tokens1)


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
print_tokens(tokens4, header='indent')
#exit()

tokens = tokens4

#assert False

infix_words = [
        '=',
        '+', '+=',
        '-', '-=',
        '*', '*=',
        '/', '/=',
        'and', 'or',
        ]

class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.current_token_index = 0

    def parse(self):
        ast = []

        self.consume_newlines()
        while not self.end_of_tokens():
            ast.append(self.parse_statement())
            self.consume_newlines()
            #print(json.dumps(ast['body'], indent=4))
        return ast

    def parse_statement(self):
        if self.end_of_tokens():
            assert False
            return None

        cmd = self.parse_expression()

        args  = []
        block = []
        comment = None

        while self.current_token().type not in ['NEWLINE', 'INDENT', 'DEDENT', 'EOF']:
            self.consume_whitespace()
            comment = self.parse_comment()
            if comment:
                ct = self.current_token()
                if ct.type in ['NEWLINE', 'EOF']:
                    break
            arg = self.parse_expression()
            args.append(arg)

        #print(args)
        if self.current_token().type == 'INDENT':
            block = self.consume_block()

        if len(args):
            first_arg = args[0]
            if first_arg in infix_words:
                assert block == []
                expr = ['infix', [cmd, *args], block, comment]
                return expr

        expr = [cmd, args, block, comment]

        return expr

    def parse_infix_expression(self):
        args = []
        while self.current_token().type not in ['RPAREN', 'COMMA', 'COMMENT', 'INDENT']:
            sub_expr = self.parse_expression()
            args.append(sub_expr)

        if self.current_token().type == 'INDENT':
            assert False

        if len(args) == 1:
            return args[0]

        comment = self.parse_comment()

        expr = ['infix', args, [], comment]
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
            comment_text = self.consume('COMMENT').value
            expr = ['comment', [comment_text], [], None]
            return expr

        if t.type not in ['WORD', 'STRING1', 'STRING2']:
            assert False

        cmd = self.consume(None).value

        try:
            i = int(cmd)
            return i
        except ValueError:
            pass

        try:
            f = float(cmd)
            return f
        except ValueError:
            pass

        attributes = []
        while self.current_token().type == 'DOT':
            _ = self.consume('DOT')
            attribute = self.consume('WORD').value
            attributes.append(attribute)

        if attributes:
            cmd = ['attr', [cmd, *attributes], [], None]


        if self.current_token().type == 'LPAREN':
            return self.parse_neoteric(cmd)


        return cmd

    def parse_neoteric(self, cmd):
        _ = self.consume('LPAREN')

        pre_indent_comment = self.parse_comment()

        if self.current_token().type == 'INDENT':
            _ = self.consume('INDENT')
            args = self.consume_paren_block()

            neo_comment = self.parse_comment()

            _ = self.consume('DEDENT')
            block = []
            if pre_indent_comment:
                args.insert(0, pre_indent_comment)
            expr = [cmd, args, block, neo_comment]
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
        comment = None
        expr = [cmd, args, block, comment]
        return expr

    def parse_comment(self):
        t = self.optional_consume('COMMENT')
        if t is None:
            return
        comment_text = t.value.lstrip('# ')
        expr = ['comment', [comment_text], [], None]
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
            self.consume_newlines()
            expr = self.parse_statement()
            block.append(expr)
            #print(block)
            
        _ = self.consume('DEDENT')

        return block

    def consume_paren_block(self):
        block = []
        while True:
            self.consume_newlines()
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

        return block

    def consume_newlines(self):
        while not self.end_of_tokens():
            if self.current_token().type == 'NEWLINE':
                _ = self.consume(None)
                #print(f'skip {_}')
            else:
                break

    def optional_consume(self, expected_type):
        token = self.current_token()
        if token.type == expected_type:
            return self.consume(None)

        return None
        assert False

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

#print(json.dumps(ast, indent=2))
pprint(ast)

def dumps(ast):
    lines = dump_block(ast, 'module', 0)
    print(lines)
    print('\n'.join(lines))

def dump_block(block, context, indent):
    lines = []
    for statement in block:
        s = dump_statement(statement, context, indent)
        s2 = '\n'.join(s)
        lines.append(s2)
    return lines

def dump_statement(ast, context, indent):
    cmd, args, block, comment = ast

    comment_string = dump_comment(comment)

    if cmd == 'attr':
        assert False
    elif cmd == 'infix':
        cmd_string = ''
        args_string = dump_args(args, ' ', 'infix', indent)
        assert block == []
    elif cmd == 'comment':
        assert block == []
        assert comment is None
        assert len(args) == 1
        cmd_string = ''
        args_string = '# ' + args[0].lstrip('#')
    else:
        cmd_string = dump_expr(cmd, 'statement', indent)
        args_string = dump_args(args, ' ', 'statement', indent)

    indent_string = '    ' * indent
    if cmd_string:
        expr_string = f'{cmd_string}{args_string}'
    else:
        expr_string = args_string

    first_line = f'{indent_string}{expr_string}{comment_string}'
    lines = [first_line]
    for sub_statement in block:
        sub_statement_string = dump_statement(sub_statement, context, indent+1)
        lines.append('\n'.join(sub_statement_string))
    return lines

def dump_attr(expr, indent):
    cmd, args, block, comment = expr
    assert cmd == 'attr'
    assert block == []
    assert comment is None
    s = dump_args(args, '.', 'attr', indent)
    return s

def dump_comment(expr):
    if expr is None:
        return ''
    cmd, args, block, comment = expr
    assert cmd == 'comment'
    assert len(args) == 1
    assert block == []
    assert comment == None
    comment_text = args[0]
    s = f' # {comment_text}'
    return s

def dump_expr(expr, context, indent):
    if not isinstance(expr, list):
        return str(expr)

    cmd, args, block, comment = expr

    if isinstance(cmd , int):
        assert args == []
        assert block == []
        assert comment is None
        s = str(cmd)
        return s

    if isinstance(cmd , float):
        assert args == []
        assert block == []
        assert comment is None
        s = str(cmd)
        assert False

    assert block == []
    comment_string = dump_comment(comment)

    if cmd == 'attr':
        assert comment == None
        return dump_attr(expr, indent)
    elif cmd == 'infix':
        assert comment == None
        args_string = dump_args(args, ' ', 'infix', indent)
        assert block == []
        if context == 'infix':
            return f'({args_string})'
        else:
            return args_string
    elif cmd == 'comment':
        assert comment == None
        assert len(args) == 1
        assert block     == []
        comment_text = '# ' + args[0].lstrip('#')
        return comment_text + '\n'
    elif cmd == 'expr':
        args_string = dump_args(args, ' ', context, indent)
        expr_string = f'{args_string}{comment_string}'
        return expr_string
    else:
        cmd_string = dump_expr(cmd, context, indent)
        args_string = dump_args(args, ', ', 'neoteric', indent)
        return f'{cmd_string}({args_string}){comment_string}'

def contains_comments(expr):
    if not isinstance(expr, list):
        return False

    cmd, args, block, comment = expr

    if cmd == 'comment':
        return True

    if comment:
        return True

    for arg in args:
        if contains_comments(arg):
            return True

    return False

def dump_args(args, sep, context, indent):
    has_named_args = False
    has_comments   = False

    if args == []:
        return ''

    for arg in args:
        if not isinstance(arg, list):
            continue

        if has_comments == False and contains_comments(arg):
            has_comments = True

        cmd, arg_args, block, comment = arg

        if cmd != 'infix':
            continue

        op = arg[1][1]
        if op == '=':
            has_named_args = True
            break
        #print(arg[1][1])

    if has_named_args or has_comments:
        indent_string = '    ' * (indent + 1)
        lines =  dump_block(args, context, indent+1)
        return '\n' + '\n'.join(lines) + f'\n{indent_string}'

    return ' ' + sep.join(dump_expr(a, context, indent) for a in args)

print('*'*40)
print()
dumps(ast)
print()

