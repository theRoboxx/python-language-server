# Copyright 2021 Michal Krassowski

# keywords that are ALWAYS followed by space
KEYWORDS_FOLLOWED_BY_SPACE = {
    'as',
    'assert',
    'async',
    'await',
    'class',
    'def',
    'del',
    'for',
    'from',
    'global',
    'import',
    'in',
    'is',
    'nonlocal',
    'raise',
    'while',
    'with',
    # conditional
    'elif',
    'if',
    # logical
    'and',
    'or',
    'not',
}
# note: 'yield' and 'return' can be followed by space but can also be standalone

# keywords that are ALWAYS followed by colon
KEYWORDS_FOLLOWED_BY_COLON = {
    'try',
    'finally'
}
# note: 'else' can be used in a ternary expression: x = 1 if y else 2
# note: 'lambda' can be followed by colon or argument: lambda: 1 or lambda x: x + 1


def insert_text(name: str, completion_type: str):
    if completion_type == 'keyword':
        if name in KEYWORDS_FOLLOWED_BY_SPACE:
            return name + ' '
        if name in KEYWORDS_FOLLOWED_BY_COLON:
            return name + ':'
    return name
