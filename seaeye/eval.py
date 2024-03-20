import sys
from seaeye.parse import (
    parse_file,
    dumps
)

def my_eval(env, expr):
    if isinstance(expr, str):
        if expr[0] == '"':
            s = expr[1:-1]
            return s

        scope = lookup_scope(env, expr)
        value = scope[expr]
        return value
    elif isinstance(expr, int):
        return expr

    assert isinstance(expr, list)

    cmd, args, block, comment = expr
    cmd_scope = lookup_scope(env, cmd)
    fn = cmd_scope[cmd]
    return fn(env, expr)

def eval_print(env, expr):
    cmd, args, block, comment = expr
    assert len(args) == 1
    msg = my_eval(env, args[0])
    print(msg)
    return

def eval_assign(env, expr):
    cmd, args, block, comment = expr
    target, value = args
    try:
        scope = lookup_scope(env, target)
    except ValueError:
        scope = env[-1]
    evalated_value = my_eval(env, value)
    scope[target] = evalated_value

def eval_increment_by(env, expr):
    cmd, args, block, comment = expr
    target, value = args
    try:
        scope = lookup_scope(env, target)
    except ValueError:
        scope = env[-1]
    evalated_value = my_eval(env, value)
    old_value = scope[target]
    new_value = old_value + evalated_value
    scope[target] = new_value

def lookup_scope(env, target):
    for scope in env:
        if target in scope:
            return scope
    raise ValueError(f'unknown target: "{target}"')
ast = parse_file(sys.argv[1])
#dumps(ast)

global_env = [{
    'print': eval_print,
    '=':     eval_assign,
    '+=':    eval_increment_by,
}]

for statement in ast:
    my_eval(global_env, statement)

exit(0)

