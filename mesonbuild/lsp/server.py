import argparse
import logging
from pathlib import Path
import socketserver
import sys
from typing import Optional

from pyls_jsonrpc.dispatchers import MethodDispatcher
from pyls_jsonrpc.endpoint import Endpoint
from pyls_jsonrpc.streams import JsonRpcStreamReader, JsonRpcStreamWriter

import mesonbuild.lsp.lsp_const as consts
from mesonbuild.lsp.workspace import Workspace
from mesonbuild.lsp.config import Config

logger = logging.getLogger(__name__)


def new_with_stdio(options: argparse.Namespace):
    logger.info('Starting Meson LS using stdin/stdout (%s)', repr(options))
    server = MesonLanguageServer(sys.stdin.buffer, sys.stdout.buffer)
    server.start()
    return server


class MesonLanguageServer(MethodDispatcher):
    workspace: Optional[Workspace]
    config: Optional[Config]

    def __init__(self, rx, tx):
        self.workspace = None
        self.config = None

        self.rpc_reader = JsonRpcStreamReader(rx)
        self.rpc_writer = JsonRpcStreamWriter(tx)
        self.endpoint = Endpoint(self, self.rpc_writer.write, max_workers=64)
        self.shutdown = False

    def start(self):
        logger.info('Starting')
        self.rpc_reader.listen(self.endpoint.consume)

    def capabilities(self):
        capabilities = {
            'completionProvider': True,
            'textDocumentSync': consts.TextDocumentSyncKind.INCREMENTAL
        }
        return capabilities

    def m_initialize(self, **kwargs):
        logger.info('Initializing: %s', repr(kwargs))
        if 'rootUri' not in kwargs:
            root_uri = Path(kwargs.get('rootPath')).as_uri()
        else:
            root_uri = kwargs.get('rootUri')
        self.workspace = Workspace(root_uri, self.endpoint)
        self.config = Config(root_uri, kwargs.get('initializationOptions', {}),
                             kwargs.get('processId'),
                             kwargs.get('capabilities'))
        return dict(capabilities=self.capabilities())

    def m_initialized(self, **_kwargs):
        pass

    def m_text_document__did_open(self, textDocument):
        self.workspace.update(
            textDocument,
            dict(
                text=textDocument.get('text'),
                version=textDocument.get('version')))
        self.workspace.build_ast()

    def m_text_document__did_close(self, textDocument):
        self.workspace.pop_document(textDocument)
        self.workspace.build_ast()

    def m_text_document__did_change(self, textDocument, contentChanges):
        for change in contentChanges:
            self.workspace.update(textDocument, change)
        self.workspace.build_ast()

    def m_text_document__did_save(self, textDocument):
        self.workspace.documents.get(textDocument.get('uri')).refresh()

    def m_workspace__did_change_watched_files(self, changes):
        self.workspace.build_ast()

    def m_text_document__hover(self, textDocument, position):
        doc = self.workspace.get_document(textDocument.get('uri'))
        start_pos, end_pos, word = doc.get_word_at_position(**position)
        start_posd = doc.get_char_count_position(start_pos)
        end_posd = doc.get_char_count_position(end_pos)
        return dict(
            contents=
            f"{word} (from {start_posd[0]}:{start_posd[1]} to {end_posd[0]}:{end_posd[1]})"
        )

    def m_text_document__completion(self, **kwargs):
        return self.workspace.get_symbols()

    def m_shutdown(self, **_kwargs):
        logger.warning('Shutting down')
        self.shutdown = True

    def m_exit(self, **_kwargs):
        self.endpoint.shutdown()
        self.rpc_reader.close()
        self.rpc_writer.close()
