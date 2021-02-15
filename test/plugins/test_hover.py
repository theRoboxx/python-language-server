# Copyright 2017 Palantir Technologies, Inc.

from pyls import uris
from pyls.plugins.hover import pyls_hover
from pyls.workspace import Document

DOC_URI = uris.from_fs_path(__file__)
DOC = """

def main():
    \"\"\"hello world\"\"\"
    pass
"""

NUMPY_DOC = """

import numpy as np
np.sin

"""


def test_numpy_hover(workspace):
    # Over the blank line
    no_hov_position = {'line': 1, 'character': 0}
    # Over 'numpy' in import numpy as np
    numpy_hov_position_1 = {'line': 2, 'character': 8}
    # Over 'np' in import numpy as np
    numpy_hov_position_2 = {'line': 2, 'character': 17}
    # Over 'np' in np.sin
    numpy_hov_position_3 = {'line': 3, 'character': 1}
    # Over 'sin' in np.sin
    numpy_sin_hov_position = {'line': 3, 'character': 4}

    doc = Document(DOC_URI, workspace, NUMPY_DOC)

    contents = ''
    assert contents in pyls_hover(doc, no_hov_position)['contents']

    contents = 'NumPy\n=====\n\nProvides\n'
    hov_1 = pyls_hover(doc, numpy_hov_position_1)['contents'][0]
    assert hov_1['kind'] == 'markdown'
    assert contents in hov_1['value']

    contents = 'NumPy\n=====\n\nProvides\n'
    hov_2 = pyls_hover(doc, numpy_hov_position_2)['contents'][0]
    assert hov_2['kind'] == 'markdown'
    assert contents in hov_2['value']

    contents = 'NumPy\n=====\n\nProvides\n'
    hov_3 = pyls_hover(doc, numpy_hov_position_3)['contents'][0]
    assert hov_3['kind'] == 'markdown'
    assert contents in hov_3['value']

    contents = 'Trigonometric sine, element-wise.\n\n'
    hov_sin = pyls_hover(doc, numpy_sin_hov_position)['contents'][0]
    assert hov_sin['kind'] == 'markdown'
    assert contents in hov_sin['value']


def test_hover(workspace):
    # Over 'main' in def main():
    hov_position = {'line': 2, 'character': 6}
    # Over the blank second line
    no_hov_position = {'line': 1, 'character': 0}

    doc = Document(DOC_URI, workspace, DOC)

    contents = [{'language': 'python', 'value': 'main()'}, 'hello world']

    assert {
        'contents': contents
    } == pyls_hover(doc, hov_position)

    assert {'contents': ''} == pyls_hover(doc, no_hov_position)
