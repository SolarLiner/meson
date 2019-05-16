import logging
import pkgutil
from pathlib import Path
from urllib import parse
from typing import Dict

from pyls_jsonrpc.endpoint import Endpoint

from .document import Document
from . import lsp_const
from ..ast.interpreter import AstInterpreter

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

    def __init__(self, root_uri: str, endpoint: Endpoint):
        logger.debug('Workspace(%s, %s)', root_uri, endpoint)
        root_path = parse.unquote(parse.urlparse(root_uri).path)
        self.root_uri = root_uri
        self.endpoint = endpoint
        self.documents = dict()
        self.ast = AstInterpreter(root_path, '')

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
        try:
            self.ast.load_root_meson_file()
            self.ast.parse_project()
            self.ast.run()
        except:
            logger.exception('AST parsing failed')

    def get_symbols(self):
        keywords = [
            dict(label=k, kind=lsp_const.CompletionItemKind.Keyword)
            for k in KEYWORDS_ALL
        ]
        modules = [
            dict(
                label=k['name'],
                detail=f"{k['name']} module",
                deprecated=k['deprecated'],
                insertText=f"import('{k['name']}')",
                kind=lsp_const.CompletionItemKind.Module) for k in MODULES
        ]
        variables = [
            dict(
                label=k,
                kind=lsp_const.CompletionItemKind.Variable,
                documentation="TODO (variables)",
                detail=str(type(v))) for k, v in self.ast.variables.items()
        ]
        assignments = [
            dict(
                label=k,
                kind=lsp_const.CompletionItemKind.Variable,
                documentation=f"TODO (assignments) - evaluates to {str(v)}",
                detail=str(type(v))) for k, v in self.ast.assign_vals.items()
        ]
        functions = [
            dict(
                label=k,
                kind=lsp_const.CompletionItemKind.Function,
                documentation="TODO",
                detail='Function') for k in self.ast.funcs.keys()
        ]
        subdirs = [
            dict(
                label=f"{k} (subproject)",
                kind=lsp_const.CompletionItemKind.Reference,
                detail=f"subproject('{k}')",
                insertText=f"subproject('{k}')")
            for k in self.ast.visited_subdirs.keys()
        ]
        return keywords + modules + variables + assignments + functions + subdirs
