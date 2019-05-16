import logging
import os
import pkgutil
from pathlib import Path
from urllib import parse
from typing import Dict, List

from pyls_jsonrpc.endpoint import Endpoint

from .document import Document
from . import lsp_const
from .ast import LSPInterpreter
from ..mparser import Lexer, ParseException

logger = logging.getLogger(__name__)

KEYWORDS_BLOCK = ["if", "foreach"]
KEYWORDS_BLOCK_END = [f"end{v}" for v in KEYWORDS_BLOCK]
KEYWORDS_LOGIC = ["and", "or", "not"]
KEYWORDS_OTHER = ["else", "elif"]
KEYWORDS_ALL = KEYWORDS_BLOCK + KEYWORDS_BLOCK_END + KEYWORDS_LOGIC + KEYWORDS_OTHER

MODULES = [
    dict(
        name=m.name.replace('unstable_', ''),
        deprecated=('unstable' in m.name)) for m in pkgutil.iter_modules([(
            Path(__file__) / '../../modules').resolve()])
]


class Workspace:
    documents: Dict[str, Document]
    errors: List[ParseException]

    def __init__(self, root_uri: str, endpoint: Endpoint):
        logger.debug('Workspace(%s, %s)', root_uri, endpoint)
        self.root_uri = root_uri
        self.endpoint = endpoint
        self.documents = dict()
        self.errors = list()

        self.build_ast()

    def update(self, document, changes=None):
        if document.get('uri') in self.documents:
            self.documents.get(document.get('uri')).update(changes)
        else:
            self.documents[document.get('uri')] = Document(
                document.get('uri'), document.get('text'))

    def get_document(self, uri: str) -> Document:
        return self.documents.get(uri)

    def pop_document(self, document):
        return self.documents.pop(document.get('uri'))

    def build_ast(self):
        logger.info('Rebuilding AST')
        self.errors = list()
        self.interpreter = LSPInterpreter(self, '')
        try:
            self.interpreter.load_root_meson_file()
            self.interpreter.parse_project()
            self.interpreter.run()
        except ParseException as pe:
            self.errors.append(pe)
        except:
            logger.exception('AST parsing failed')
            raise
        self.endpoint.notify(
            'textDocument/publishDiagnostics',
            params={
                'uri':
                os.path.join(self.root_uri, 'meson.build'),
                'diagnostics': [{
                    'source': 'meson',
                    'range': {
                        'start': {
                            'line': e.lineno,
                            'character': e.colno
                        },
                        'end': {
                            'line': e.lineno,
                            'character': e.colno
                        }
                    },
                    'message': str(e),
                    'severity': lsp_const.DiagnosticSeverity.Error,
                    'code': '-1'
                } for e in self.errors]
            })

    def get_symbols(self):
        keywords = [
            dict(label=k, kind=lsp_const.CompletionItemKind.Keyword)
            for k in Lexer("").keywords
        ] + [
            dict(
                label=k,
                kind=lsp_const.CompletionItemKind.Keyword,
                deprecated=True) for k in Lexer("").future_keywords
        ]
        modules = [
            dict(
                label=k['name'],
                detail=f"{k['name']} module (unstable)"
                if k['deprecated'] else f"{k['name']} module",
                deprecated=k['deprecated'],
                insertText=f"import('{k['name']}')",
                kind=lsp_const.CompletionItemKind.Module) for k in MODULES
        ]
        variables = [
            dict(
                label=k,
                kind=lsp_const.CompletionItemKind.Variable,
                documentation="TODO (variables)",
                detail=str(type(v)))
            for k, v in self.interpreter.variables.items()
        ]
        assignments = [
            dict(
                label=k,
                kind=lsp_const.CompletionItemKind.Variable,
                documentation=f"TODO (assignments) - evaluates to {str(v)}",
                detail=str(type(v)))
            for k, v in self.interpreter.assign_vals.items()
        ]
        functions = [
            dict(
                label=k,
                kind=lsp_const.CompletionItemKind.Function,
                documentation="TODO",
                detail='Function') for k in self.interpreter.funcs.keys()
        ]
        subdirs = [
            dict(
                label=f"{k} (subproject)",
                kind=lsp_const.CompletionItemKind.Reference,
                detail=f"subproject('{k}')",
                insertText=f"subproject('{k}')")
            for k in self.interpreter.visited_subdirs.keys()
        ]
        return keywords + modules + variables + assignments + functions + subdirs
