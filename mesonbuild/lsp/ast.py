import logging
from urllib import parse
import os, sys

from pathlib import Path
from typing import Optional, List

from .. import mesonlib, mparser, environment
from ..ast import AstInterpreter, AstVisitor

logger = logging.getLogger(__name__)


class LSPInterpreter(AstInterpreter):
    """Interpreter that works on arbitrary code not yet saved to the filesystem"""

    def __init__(self,
                 workspace: 'Workspace',
                 subdir: str,
                 visitors: Optional[List[AstVisitor]] = None):
        self.workspace = workspace
        source_root = parse.unquote(parse.urlparse(workspace.root_uri).path)
        return super().__init__(source_root, subdir, visitors=visitors)

    def load_root_meson_file(self):
        mesonfile_uri = os.path.join(self.workspace.root_uri, "meson.build")
        logger.debug('%s - %s', self.workspace.documents, mesonfile_uri)

        if mesonfile_uri in self.workspace.documents:
            document = self.workspace.get_document(mesonfile_uri)
            self.ast = mparser.Parser(document.contents, '').parse()
            if self.visitors:
                for visitor in self.visitors:
                    self.ast.accept(visitor)
        else:
            super().load_root_meson_file()

    def func_subdir(self, node, args, kwargs):
        args = self.flatten_args(args)
        if len(args) != 1 or not isinstance(args[0], str):
            sys.stderr.write(
                'Unable to evaluate subdir({}) in AstInterpreter --> Skipping\n'
                .format(args))
            return

        prev_subdir = self.subdir
        subdir = os.path.join(prev_subdir, args[0])
        absdir = os.path.join(self.source_root, subdir)
        buildfilename = os.path.join(subdir, environment.build_filename)
        absname = os.path.join(self.source_root, buildfilename)
        symlinkless_dir = os.path.realpath(absdir)
        if symlinkless_dir in self.visited_subdirs:
            sys.stderr.write(
                'Trying to enter {} which has already been visited --> Skipping\n'
                .format(args[0]))
            return
        self.visited_subdirs[symlinkless_dir] = True
        abs_uri = Path(absname).as_uri()
        if abs_uri not in self.workspace.documents:
            if not os.path.isfile(absname):
                sys.stderr.write(
                    'Unable to find build file {} --> Skipping\n'.format(
                        buildfilename))
                return
            with open(absname, encoding='utf8') as f:
                code = f.read()
            assert (isinstance(code, str))
            try:
                codeblock = mparser.Parser(code, subdir).parse()
            except mesonlib.MesonException as me:
                me.file = buildfilename
                raise me
        else:
            try:
                document = self.workspace.get_document(abs_uri)
                codeblock = mparser.Parser(document.contents).parse()
            except mesonlib.MesonException as me:
                me.file = buildfilename
                raise me

        self.subdir = subdir
        for i in self.visitors:
            codeblock.accept(i)
        self.evaluate_codeblock(codeblock)
        self.subdir = prev_subdir
