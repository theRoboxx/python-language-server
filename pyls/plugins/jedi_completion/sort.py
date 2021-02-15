# Copyright 2021 Michal Krassowski
from keyword import iskeyword
from string import ascii_lowercase
from typing import Dict
try:
    # pylint: disable=ungrouped-imports,useless-suppression
    from keyword import issoftkeyword
except ImportError:
    # pylint: disable=unused-argument
    def issoftkeyword(s: str):
        return False

from jedi.api.classes import Completion


def sort_text(definition: Completion, relative_frequencies: Dict[str, float] = None, sort_by_count=False) -> str:
    """Use frequency-based and rule-based sorting"""
    if not definition.name:
        # TODO: why would the name be None (it is allowed)?
        return 'z'

    if definition.type == 'param':
        prefix = 'a'
    elif sort_by_count and definition.name in relative_frequencies:
        # frequency is a number between 0 and 1
        rarity = 1 - relative_frequencies[definition.name]
        # assign c-m for the frequency-based sorting
        # rarity = 0.5 will give 'h'
        priority = round(rarity * 10) + 2
        # reduce the priority for hidden
        if definition.name.startswith('_'):
            priority += 1
            # and double dunders
            if definition.name.startswith('__'):
                priority += 1
        prefix = ascii_lowercase[priority + 2]
    elif definition.name.startswith('_'):
        if definition.name.startswith('__'):
            # move double dunders to the very bottom
            prefix = 'z'
        else:
            # move hidden properties down
            prefix = 'o'
    elif iskeyword(definition.name):
        # show genuine keywords near the top, but below parameters
        prefix = 'b'
    elif issoftkeyword(definition.name):
        # soft keywords get lower priority than keywords as these might
        # include false positives, but get a higher probability than a
        # an average word occurring in text (equivalent to rarity=0.25)
        prefix = 'e'
    else:
        # this name does not appear in the document and is in now way special;
        # show it just after the names that appear in the documents
        prefix = 'n'
    return prefix + definition.name
