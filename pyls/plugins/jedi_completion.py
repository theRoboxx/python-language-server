# Copyright 2017 Palantir Technologies, Inc.
import logging
import os.path as osp
from collections import defaultdict
from time import time

import parso

from jedi.api.classes import Completion
from pyls import _utils, hookimpl, lsp


class LabelResolver:

    def __init__(self, time_to_live=60 * 30):
        self._cache = {}
        self._time_to_live = time_to_live
        self._cache_ttl = defaultdict(set)
        self._clear_every = 2
        # see https://github.com/davidhalter/jedi/blob/master/jedi/inference/helpers.py#L194-L202
        self._cached_modules = {'pandas', 'numpy', 'tensorflow', 'matplotlib'}

    def clear_outdated(self):
        now = self.time_key()
        to_clear = [
            timestamp
            for timestamp in self._cache_ttl
            if timestamp < now
        ]
        for time_key in to_clear:
            for key in self._cache_ttl[time_key]:
                del self._cache[key]
            del self._cache_ttl[time_key]

    def time_key(self):
        return int(time() / self._time_to_live)

    def get_or_create(self, completion: Completion):
        if not completion.full_name:
            use_cache = False
        else:
            module_parts = completion.full_name.split('.')
            use_cache = module_parts and module_parts[0] in self._cached_modules

        if use_cache:
            key = self._create_completion_id(completion)
            if key not in self._cache:
                if self.time_key() % self._clear_every == 0:
                    self.clear_outdated()

                self._cache[key] = self.resolve_label(completion)
                self._cache_ttl[self.time_key()].add(key)
            return self._cache[key]
        else:
            return self.resolve_label(completion)

    def _create_completion_id(self, completion: Completion):
        return (
            completion.full_name, completion.module_path,
            completion.line, completion.column,
            self.time_key()
        )

    @staticmethod
    def resolve_label(completion):
        try:
            sig = completion.get_signatures()
            if sig and completion.type in ('function', 'method'):
                params = ', '.join(param.name for param in sig[0].params)
                label = '{}({})'.format(completion.name, params)
                return label
            else:
                return completion.name
        except Exception as e:
            log.warning(
                'Something went wrong when resolving label for {completion}: {e}'.format(
                    completion=completion, e=e
                )
            )


LABEL_RESOLVER = LabelResolver()


log = logging.getLogger(__name__)

# Map to the VSCode type
_TYPE_MAP = {
    'none': lsp.CompletionItemKind.Value,
    'type': lsp.CompletionItemKind.Class,
    'tuple': lsp.CompletionItemKind.Class,
    'dict': lsp.CompletionItemKind.Class,
    'dictionary': lsp.CompletionItemKind.Class,
    'function': lsp.CompletionItemKind.Function,
    'lambda': lsp.CompletionItemKind.Function,
    'generator': lsp.CompletionItemKind.Function,
    'class': lsp.CompletionItemKind.Class,
    'instance': lsp.CompletionItemKind.Reference,
    'method': lsp.CompletionItemKind.Method,
    'builtin': lsp.CompletionItemKind.Class,
    'builtinfunction': lsp.CompletionItemKind.Function,
    'module': lsp.CompletionItemKind.Module,
    'file': lsp.CompletionItemKind.File,
    'path': lsp.CompletionItemKind.Text,
    'xrange': lsp.CompletionItemKind.Class,
    'slice': lsp.CompletionItemKind.Class,
    'traceback': lsp.CompletionItemKind.Class,
    'frame': lsp.CompletionItemKind.Class,
    'buffer': lsp.CompletionItemKind.Class,
    'dictproxy': lsp.CompletionItemKind.Class,
    'funcdef': lsp.CompletionItemKind.Function,
    'property': lsp.CompletionItemKind.Property,
    'import': lsp.CompletionItemKind.Module,
    'keyword': lsp.CompletionItemKind.Keyword,
    'constant': lsp.CompletionItemKind.Variable,
    'variable': lsp.CompletionItemKind.Variable,
    'value': lsp.CompletionItemKind.Value,
    'param': lsp.CompletionItemKind.Variable,
    'statement': lsp.CompletionItemKind.Keyword,
}

# Types of parso nodes for which snippet is not included in the completion
_IMPORTS = ('import_name', 'import_from')

# Types of parso node for errors
_ERRORS = ('error_node', )

# most recently retrieved completion items, used for resolution
_LAST_COMPLETIONS = {}


@hookimpl
def pyls_completions(config, document, position):
    """Get formatted completions for current code position"""
    # pylint: disable=too-many-locals
    # pylint: disable=global-statement
    global _LAST_COMPLETIONS

    settings = config.plugin_settings('jedi_completion', document_path=document.path)
    resolve_eagerly = settings.get('eager', False)
    code_position = _utils.position_to_jedi_linecolumn(document, position)

    code_position["fuzzy"] = settings.get("fuzzy", False)
    completions = document.jedi_script(use_document_path=True).complete(**code_position)

    if not completions:
        return None

    completion_capabilities = config.capabilities.get('textDocument', {}).get('completion', {})
    snippet_support = completion_capabilities.get('completionItem', {}).get('snippetSupport')

    should_include_params = settings.get('include_params')
    max_labels_resolve = settings.get('resolve_at_most_labels', 25)
    should_include_class_objects = settings.get('include_class_objects', True)

    include_params = snippet_support and should_include_params and use_snippets(document, position)
    include_class_objects = snippet_support and should_include_class_objects and use_snippets(document, position)
    should_resolve_labels = len(completions) <= max_labels_resolve

    ready_completions = [
        _format_completion(
            c,
            include_params,
            resolve_label=should_resolve_labels
        )
        for c in completions
    ]

    if include_class_objects:
        for c in completions:
            if c.type == 'class':
                completion_dict = _format_completion(
                    c, False, resolve=resolve_eagerly,
                    resolve_label=should_resolve_labels
                )
                completion_dict['kind'] = lsp.CompletionItemKind.TypeParameter
                completion_dict['label'] += ' object'
                ready_completions.append(completion_dict)

    _LAST_COMPLETIONS = {
        # label is the only required property; here it is assumed to be unique
        completion['label']: (completion, data)
        for completion, data in zip(ready_completions, completions)
    }

    return ready_completions or None


@hookimpl
def pyls_completion_item_resolve(completion_item):
    """Resolve formatted completion for given non-resolved completion"""
    completion, data = _LAST_COMPLETIONS.get(completion_item['label'])
    return _resolve_completion(completion, data)


def is_exception_class(name):
    """
    Determine if a class name is an instance of an Exception.

    This returns `False` if the name given corresponds with a instance of
    the 'Exception' class, `True` otherwise
    """
    try:
        return name in [cls.__name__ for cls in Exception.__subclasses__()]
    except AttributeError:
        # Needed in case a class don't uses new-style
        # class definition in Python 2
        return False


def use_snippets(document, position):
    """
    Determine if it's necessary to return snippets in code completions.

    This returns `False` if a completion is being requested on an import
    statement, `True` otherwise.
    """
    line = position['line']
    lines = document.source.split('\n', line)
    act_lines = [lines[line][:position['character']]]
    line -= 1
    last_character = ''
    while line > -1:
        act_line = lines[line]
        if (act_line.rstrip().endswith('\\') or
                act_line.rstrip().endswith('(') or
                act_line.rstrip().endswith(',')):
            act_lines.insert(0, act_line)
            line -= 1
            if act_line.rstrip().endswith('('):
                # Needs to be added to the end of the code before parsing
                # to make it valid, otherwise the node type could end
                # being an 'error_node' for multi-line imports that use '('
                last_character = ')'
        else:
            break
    if '(' in act_lines[-1].strip():
        last_character = ')'
    code = '\n'.join(act_lines).split(';')[-1].strip() + last_character
    tokens = parso.parse(code)
    expr_type = tokens.children[0].type
    return (expr_type not in _IMPORTS and
            not (expr_type in _ERRORS and 'import' in code))


def _resolve_completion(completion, d):
    completion['detail'] = _detail(d)
    completion['documentation'] = _utils.format_docstring(d.docstring(raw=True), signature=d._get_docstring_signature())
    return completion


def _format_completion(d, include_params=True, resolve=False, resolve_label=False):
    completion = {
        'label': _label(d, resolve_label),
        'kind': _TYPE_MAP.get(d.type),
        'sortText': _sort_text(d),
        'insertText': d.name
    }

    if resolve:
        completion = _resolve_completion(completion, d)

    if d.type == 'path':
        path = osp.normpath(d.name)
        path = path.replace('\\', '\\\\')
        path = path.replace('/', '\\/')
        completion['insertText'] = path

    if include_params and not is_exception_class(d.name):
        sig = d.get_signatures()
        if not sig:
            return completion

        positional_args = [param for param in sig[0].params
                           if '=' not in param.description and
                           param.name not in {'/', '*'}]

        if len(positional_args) > 1:
            # For completions with params, we can generate a snippet instead
            completion['insertTextFormat'] = lsp.InsertTextFormat.Snippet
            snippet = d.name + '('
            for i, param in enumerate(positional_args):
                snippet += '${%s:%s}' % (i + 1, param.name)
                if i < len(positional_args) - 1:
                    snippet += ', '
            snippet += ')$0'
            completion['insertText'] = snippet
        elif len(positional_args) == 1:
            completion['insertTextFormat'] = lsp.InsertTextFormat.Snippet
            completion['insertText'] = d.name + '($0)'
        else:
            completion['insertText'] = d.name + '()'

    return completion


def _label(definition, resolve=False):
    if not resolve:
        return definition.name
    sig = LABEL_RESOLVER.get_or_create(definition)
    if sig:
        return sig
    return definition.name


def _detail(definition):
    try:
        return definition.parent().full_name or ''
    except AttributeError:
        return definition.full_name or ''


def _sort_text(definition):
    """ Ensure builtins appear at the bottom.
    Description is of format <type>: <module>.<item>
    """

    # If its 'hidden', put it next last
    prefix = 'z{}' if definition.name.startswith('_') else 'a{}'
    return prefix.format(definition.name)
