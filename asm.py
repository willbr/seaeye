from rich.console import Console
from rich.traceback import install
from collections import deque

import fileinput
import argparse
import re
import operator
import sys

console = Console(markup=False)
python_print = print
print = console.print

install(show_locals=True)

# ROM0 0000 - 3fff
# ROM1 4000 - 7fff
# VRA0 8000 - 9fff
# SRA0 a000 - bfff
# WRA0 c000 - cfff
# WRA1 d000 - dfff
# ECH0 e000 - fdff
# OAM  fe00 - fe9f
# OAM  fea0 - feff
# IO   ff00 - ff7f
# HRAM ff80 - fffe
# IE   ffff - ffff

rom  = bytearray(0x8000)
pc   = 0
refs = []
labels = {}
scope = None
tokens = None
tokens_iter = None

def read_tokens(filename):
    with open(filename, 'r') as f:
        data = f.read()
    tokens = data.split()
    return tokens


def resolve():
    for label, token, ref_addr in refs:
        try:
            label_addr = labels[label]
        except KeyError:
            print(labels)
            print(f"unknown label: {repr(label)}")
            exit(1)
        #print(label, ref_addr, label_addr)
        if token == 'jr':
            delta = label_addr - ref_addr - 1
            n = u8(delta)
            poke8(ref_addr, n)
        else:
            poke16le(ref_addr, label_addr)

def write_rom(filename):
    with open(filename, 'wb') as f:
        f.write(rom)

def u8(n):
    assert n >= -128
    assert n <= 127
    u = (n + 256) & 0xff
    return u

def u16(n):
    assert n >= -32768
    assert n <= 32767
    u = (n + 0x10000) & 0xffff
    return u

def write8(n):
    global pc
    poke8(pc, n)
    pc += 1

def write16(nn):
    global pc
    poke16le(pc, nn)
    pc += 2

def poke8(offset, n):
    assert 0 <= n <= 0xff
    rom[offset] = n


def poke16le(offset, nn):
    assert 0 <= nn <= 0xffff

    high = nn >> 8
    low  = nn & 0x00ff

    poke8(offset, low)
    poke8(offset + 1, high)

def poke16be(offset, nn):
    assert 0 <= nn <= 0xffff

    high = nn >> 8
    low  = nn & 0x00ff

    poke8(offset, high)
    poke8(offset + 1, low)


def is_r8(r):
    return r in 'a b c d e f h l'.split()

def is_d8(n):
    if type(n) != int:
        return False
    return -128 <= n <= 0xff

def is_u8(n):
    if type(n) != int:
        return False
    return 0 <= n <= 0xff

def is_u16(n):
    if type(n) != int:
        return False
    return 0 <= n <= 0xffff

def is_condition(token):
    return token in 'z nz cy nc'.split()

def emit(op, *args):
    sargs = ', '.join(map(atom_to_string, args))
    print('\t' + op + ' ' + sargs)

def atom_to_string(t):
    if type(t) is int:
        return f'${t:02x}'
    else:
        return t

def create_label(args, block, comments):
    label_name = args[0]
    scope = label_name
    labels[label_name] = pc

def cp(args, block, comments):
    t = args[0]
    if t == 'a':
        assert False
    elif t == 'b':
        assert False
    elif t == 'c':
        assert False
    elif t == 'd':
        assert False
    elif t == 'e':
        assert False
    elif t == 'h':
        assert False
    elif t == 'l':
        assert False
    elif is_d8(t):
        write8(0xfe)
        write8(t)
    else:
        assert False

def xor(token):
    t = stack.pop()
    if t == 'deref':
        t = stack.pop()
        assert False
    elif t == 'a':
        write8(0xaf)
    elif t == 'b':
        assert False
    elif t == 'c':
        assert False
    elif t == 'd':
        assert False
    elif t == 'e':
        assert False
    elif t == 'h':
        assert False
    elif t == 'l':
        assert False
    elif is_d8(t):
        assert False
        write8(0xfe)
        write8(t)
    else:
        assert False

def set_origin(args, block, comments):
    global pc
    assert len(args) == 1
    n = args[0]
    try:
        n = int(n)
    except ValueError:
        pass

    if isinstance(n, str):
        if n.startswith('$'):
            n = int(n[1:], 16)
        elif n.startswith('%'):
            n = int(n[1:], 2)
        else:
            assert False
    assert type(n) is int
    pc = n


def incbin(token):
    filename = stack.pop().strip('"')
    with open(filename, 'rb') as f:
        data = f.read()
    for b in data:
        write8(b)


def constant(token):
    n = stack.pop()
    name = next_token()
    #print(token, name, n)
    words[name] = append_number(n)


def pad(token):
    global pc
    n = stack.pop()
    pc += n


def ldh(token):
    deref_dst = False
    deref_src = False

    t = stack.pop()
    if t == 'deref':
        dst = stack.pop()
        deref_dst = True
    else:
        dst = t

    t = stack.pop()
    if t == 'deref':
        src = stack.pop()
        deref_src = True
    else:
        src = t

    if is_u8(dst) and is_r8(src):
        write8(0xe0)
        write8(dst)
    else:
        assert False


def ldi(args, block, comments):
    dst, src = args

    match dst, src:
        case ['a', '*hl']:
            write8(0x2a)
        case ['*hl', 'a']:
            write8(0x22)
        case _:
            assert False


def ld(args, block, comments):
    deref_dst = False
    deref_src = False

    dst, src = args

    if dst[0] == '*':
        deref_dst = True
        dst = dst[1:]
        n = parse_number(dst)
        if n is not None:
            dst = n

    if src[0] == '*':
        deref_dst = True


    match dst, src:
        case 'b', 'b':
            write8(0x40)
            return
        case _:
            pass

    if is_r8(dst) and is_u8(src):
        write8(0x3e)
        write8(src)
    elif deref_dst and is_r8(src):
        write8(0xea)
        if type(dst) is str:
            make_reference('ld', dst)
            write16(0)
        else:
            write16(dst)
    elif deref_src and is_r8(dst):
        # fa 44 ff
        write8(0xfa)
        if type(src) is str:
            make_reference(token, src)
            write16(0)
        else:
            write16(src)
    elif dst == 'bc':
        write8(0x01)
        if type(src) is str:
            make_reference(token, src)
            write16(0)
        else:
            write16(src)
        assert False
    elif dst == 'de':
        write8(0x11)
        if type(src) is str:
            make_reference(token, src)
            write16(0)
        else:
            write16(src)
        assert False
    elif dst == 'hl':
        write8(0x21)
        if type(src) is str:
            make_reference('ld', src)
            write16(0)
        else:
            write16(src)
    elif dst == 'sp':
        write8(0x31)
        if type(src) is str:
            make_reference(token, src)
            write16(0)
        else:
            write16(src)
        assert False
    else:
        assert False
    #emit(token, dst, src)


def make_reference(token, label):
    refs.append((label, token, pc))


def jump(args, block, comments):
    match args:
        case [dst]:
            condition = None
        case [condition, dst]:
            pass
        case _:
            assert False

    if condition:
        if condition == 'z':
            write8(0xca)
        elif condition == 'nz':
            write8(0xc2)
        elif condition == 'cy':
            write8(0xda)
        elif condition == 'nc':
            write8(0xd2)
        else:
            assert False

        if is_u16(dst):
            n = dst
        else:
            make_reference('jump', dst)
            n = 0

        write16(n)

    elif is_u16(dst):
        assert False
    elif type(dst) is str:
        write8(0xc3)
        make_reference('jump', dst)
        write16(0)
    else:
        assert False


def write8_or_reference(token, t):
    if is_u8(t):
        write8(t)
    elif type(t) is str:
        make_reference(token, t)
        write8(0)
    else:
        assert False

def write16_or_reference(token, t):
    if is_u16(t):
        write16(t)
    elif type(t) is str:
        make_reference(token, t)
        write16(0)
    else:
        assert False


def relative_jump(token):
    t = stack.pop()

    if is_condition(t):
        if t == 'z':
            assert False
        elif t == 'nz':
            write8(0x20)
        elif t == 'cy':
            assert False
        elif t == 'nc':
            write8(0x30)
        else:
            assert False
        dst = stack.pop()
    else:
        dst = t
        write8(0x18)
    write8_or_reference(token, dst)

def include_file(token):
    t = stack.pop()
    print('INCLUDE', t)

def set_section(token):
    bank = stack.pop()
    offset = stack.pop()
    name = stack.pop()
    pc = offset
    #print(f"SECTION {name}, {bank}[${offset:02x}]")

def append_symbol(token):
    stack.append(token)

def append_number(n):
    def fn(token):
        stack.append(n)
    return fn

def call(token):
    t = stack.pop()

    if is_condition(t):
        assert False
        if condition == 'z':
            write8(0xcc)
            assert False
        elif condition == 'nz':
            write8(0xc4)
            assert False
        elif condition == 'cy':
            write8(0xdc)
            assert False
        elif condition == 'nc':
            write8(0xd4)
            assert False
        else:
            assert False

    else:
        write8(0xcd)
        dst = t

    write16_or_reference(token, dst)


def ret(token):
    if len(stack):
        t = stack.pop()
    else:
        t = None

    if is_condition(t):
        assert False
        if condition == 'z':
            write8(0xcc)
            assert False
        elif condition == 'nz':
            write8(0xc4)
            assert False
        elif condition == 'cy':
            write8(0xdc)
            assert False
        elif condition == 'nc':
            write8(0xd4)
            assert False
        else:
            assert False
    else:
        write8(0xc9)


def write_string(args, block, comments):
    s = args[0][1:-1]
    length = len(s) + 2
    write8(len(s))
    for c in s:
        write8(ord(c))
    write8(0)


def write_raw_data(token):
    while True:
        t = next_token()
        #print(t)
        if t == 'end-data':
            break
        elif t == None:
            break
        n = parse_number(t)
        assert n != None
        write8(n)


def parse_number(token):
    try:
        n = int(token)
    except ValueError:
        n = None

    if n is None:
        c = token[0]
        if c == '$':
            s = token.replace('_', '')
            n = int(s[1:], 16)
        elif c == '%':
            s = token.replace('_', '')
            n = int(s[1:], 2)
            #print(token, n)
        elif token.startswith('0x'):
            n = int(token, 16)
        else:
            n = None
    #print(token, n)
    return n


def apply_op(op):
    def fn(token):
        #print('applying', op, 'to', token)
        #print(stack)
        b = stack.pop()
        a = stack.pop()
        n = op(a, b)
        stack.append(n)
    return fn


def eval(token):
    c = token[0]
    n = parse_number(token)
    if n != None:
        stack.append(n)
    else:
        if c == '@':
            label_name = token[1:]
            scope = label_name
            labels[label_name] = pc
        elif c == '"':
            #print('string', token)
            stack.append(token)
        elif c == '*' and token != '*':
            #print('deref', token[1:])
            eval(token[1:])
            stack.append('deref')
        else:
            #print(token)
            fn = words.get(token, append_symbol)
            fn(token)

#stack = deque()
words = {
        'label': create_label,
        'pad': pad,
        'ld': ld,
        'ldh': ldh,
        'ldi': ldi,
        'jp': jump,
        'jr': relative_jump,
        'cp': cp,
        'xor': xor,
        'nop':  lambda *t:write8(0),
        'stop': lambda *t:write8(0x10),
        'halt': lambda *t:write8(0x76),
        'ei':   lambda *t:write8(0xfb),
        'di':   lambda *t:write8(0xf3),
        'include': include_file,
        'section': set_section,
        'a':  append_symbol,
        'z':  append_symbol,
        'nz': append_symbol,
        'cy': append_symbol,
        'nc': append_symbol,
        'call': call,
        'ret': ret,
        '*': apply_op(operator.mul),
        '/': apply_op(operator.floordiv),
        '+': apply_op(operator.add),
        '-': apply_op(operator.sub),
        '|': apply_op(operator.or_),
        '&': apply_op(operator.and_),
        '^': apply_op(operator.xor),
        '~': apply_op(operator.invert),
        'origin': set_origin,
        'incbin': incbin,
        'constant': constant,
        'data': write_raw_data,
        'string': write_string,
        }

def calc_header_checksum():
    checksum = 0
    for i in range(0x0134, 0x014d):
        j = rom[i]
        checksum = checksum - rom[i] - 1
        #print(f"rom[${i:02x}] = ${j:02x} :: ${checksum & 0xff :02x}")
    n = checksum & 0xff
    poke8(0x14d, n)

def calc_global_checksum():
    checksum = 0
    for i in range(0x0, 0x014e):
        checksum += rom[i]
    for i in range(0x0150, 0x7fff):
        checksum += rom[i]
    n = u16(checksum)
    poke16be(0x14e, n)

def next_token():
    try:
        t = next(tokens_iter)
    except StopIteration:
        t = None
    return t

def main(input_filename, output_filename):
    global tokens
    global tokens_iter
    tokens = read_tokens(input_filename)
    tokens_iter = iter(tokens)

    while True:
        t = next_token()
        if t == None:
            break
        #print(t)
        eval(t)
    if stack:
        print("stack isn't empty")
        print(stack)
        exit(1)
    resolve()
    calc_header_checksum()
    calc_global_checksum()
    write_rom(output_filename)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='asm.py')
    parser.add_argument('input')
    parser.add_argument('output')
    args = parser.parse_args()

    main(args.input, args.output)

