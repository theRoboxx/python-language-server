# Copyright 2021 Michal Krassowski
from keyword import iskeyword
from string import ascii_lowercase
from typing import Dict

from jedi.api.classes import Completion


def sort_text(definition: Completion, relative_frequencies: Dict[str, float] = None, sort_by_count=False):
    """Use frequency-based and rule-based sorting"""
    if not definition.name:
        # TODO: why would the name be None (it is allowed)?
        return 'z'

    if definition.type == 'param':
        prefix = 'a'
    elif sort_by_count and definition.name in relative_frequencies:
        # frequency is a number between 0 and 1
        rarity = 1 - relative_frequencies[definition.name]
        # assign a-j for the frequency-based sorting
        prefix = ascii_lowercase[round(rarity * 10)]
    elif definition.name.startswith('_'):
        if definition.name.startswith('__'):
            # move double dunders to the very bottom
            prefix = 'z'
        else:
            # move hidden properties down
            prefix = 'o'
    elif iskeyword(definition.name):
        # show keywords near the top
        prefix = 'b'
    else:
        # this name does not appear in the document and is in now way special;
        # show it just after the names that appear in the documents
        prefix = 'k'
    return prefix + definition.name
