# Copyright 2017 Palantir Technologies, Inc.

import logging

from pyls import hookimpl, _utils

log = logging.getLogger(__name__)


@hookimpl
def pyls_hover(document, position):
    code_position = _utils.position_to_jedi_linecolumn(document, position)
    definitions = document.jedi_script().infer(**code_position)
    word = document.word_at_position(position)

    # Find first exact matching definition
    definition = next((x for x in definitions if x.name == word), None)

    # Ensure a definition is used if only one is available
    # even if the word doesn't match. An example of this case is 'np'
    # where 'numpy' doesn't match with 'np'. Same for NumPy ufuncs
    if len(definitions) == 1:
        definition = definitions[0]

    if not definition:
        return {'contents': ''}

    doc = _utils.format_docstring(
        definition.docstring(raw=True),
        signatures=[d.to_string() for d in definition.get_signatures()]
    )

    return {'contents': doc}
