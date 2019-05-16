import logging
from pathlib import Path
from urllib import parse
from typing import Dict

from pyls_jsonrpc.endpoint import Endpoint

from .document import Document
from . import lsp_const
from ..ast.interpreter import AstInterpreter

logger = logging.getLogger(__name__)


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
        return variables + assignments + functions
