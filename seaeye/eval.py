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

    if isinstance(fn, list):
        return eval_fn(env, fn, expr)

    return fn(env, expr)

def eval_fn(env, fn, expr):
    cmd, args, block, comment = expr

    _, [fn_header], fn_body, fn_comment_ = fn
    fn_name, fn_params,*header_tail = fn_header

    assert len(fn_params) == len(args)

    new_scope = {}
    for i, param in enumerate(fn_params):
        arg = args[i]
        evaled_arg = my_eval(env, arg)
        new_scope[param] = evaled_arg

    fn_env = [new_scope, *env]

    for statement in fn_body:
        r = my_eval(fn_env, statement)
        if isinstance(r, list) and r[0] == 'return':
            fn_return_value = r[1]
            return fn_return_value

def eval_def(env, expr):
    cmd, args, block, comment = expr
    assert len(args) == 1
    fn_name, fn_params, *_ = args[0]
    try:
        scope = lookup_scope(env, fn_name)
    except ValueError:
        scope = env[-1]

    scope[fn_name] = expr

def eval_return(env, expr):
    cmd, args, block, comment = expr
    assert block == []
    [return_expr] = args
    return_value = my_eval(env, return_expr)
    return ['return', return_value]

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

def eval_args(env, args):
    return_value = [my_eval(env, arg) for arg in args]
    return return_value

def eval_add(env, expr):
    cmd, args, block, comment = expr
    lhs, rhs = eval_args(env, args)
    return_value = lhs + rhs
    return return_value

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
dumps(ast)

global_env = [{
    'def':    eval_def,
    'return': eval_return,
    'print':  eval_print,
    '=':      eval_assign,
    '+':      eval_add,
    '+=':     eval_increment_by,
}]

for statement in ast:
    my_eval(global_env, statement)

exit(0)

