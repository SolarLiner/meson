import logging
from urllib import parse
from pathlib import Path
import re
from typing import Optional

logger = logging.getLogger(__name__)


class Document:
    uri: str
    contents: Optional[str]
    version: int

    def __init__(self, uri, contents=None, version=None):
        self.uri = uri
        self.contents = contents
        self.version = version if version is not None else 1

    @property
    def lines(self):
        return self.contents.splitlines(True)

    def get_position_character_count(self, line=0, character=0):
        if line > len(self.lines):
            return len(self.contents)
        ccount = 0
        for i, line_content in enumerate(self.lines):
            if i == line:
                if character > len(line_content):
                    ccount += len(line_content)
                else:
                    ccount += character
                return ccount
            ccount += len(line_content)

    def get_char_count_position(self, ccount=0):
        count = 0
        for i, content in enumerate(self.lines):
            line_len = len(content)
            if count + line_len > ccount:
                return i, (ccount - count)
            count += line_len
        return len(self.lines), len(self.lines[-1])

    def update(self, changes):
        if not 'change_range' in changes:
            self.contents = changes.get('text')
            return
        start_pos = self.get_position_character_count(
            changes.get('start').get('line'),
            changes.get('start').get('character'))
        end_pos = self.get_position_character_count(
            changes.get('end').get('line'),
            changes.get('end').get('character'))

        self.update_range(start_pos, end_pos, changes.get('text'))

    def update_range(self, start_pos, end_pos, contents):
        self.contents = self.contents[
            start_pos:] + contents + self.contents[:end_pos]

    def refresh(self):
        path = parse.unquote(parse.urlparse(self.uri).path)
        self.contents = Path(path).read_text()

    def get_word_at_position(self, line=0, character=0):
        cpos = self.get_position_character_count(line, character)
        for i in range(cpos, 0, -1):
            if re.match(r'\W', self.contents[i]):
                start_pos = i
                break
        for i in range(cpos, len(self.contents)):
            if re.match(r'\W', self.contents[i]):
                end_pos = i
                break
        return start_pos, end_pos, self.contents[start_pos:end_pos]
