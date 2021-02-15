# Copyright 2021 Michal Krassowski
import tokenize
from collections import Counter
from functools import lru_cache
from io import StringIO
from queue import Queue
from threading import Thread
from typing import Dict


class NameCounter(Thread):

    def __init__(self):
        # TODO: maybe add time expiry to avoid leaks
        self.queue = Queue()
        self._frequencies_by_document: Dict[str, Dict[str, float]] = {}
        super().__init__(daemon=True)

    def get_frequencies(self, path: str, contents: str):
        self.queue.put_nowait((path, contents))
        return self._frequencies_by_document.get(path, {})

    def run(self):
        while True:
            path, contents = self.queue.get()
            self._frequencies_by_document[path] = self._calculate_relative_frequencies(contents)

    # pylint: disable=no-self-use
    @lru_cache(maxsize=5)
    def _calculate_relative_frequencies(self, contents: str) -> Dict[str, float]:
        """The most common one gets 1, the least common one gets 0."""
        tokens = []
        try:
            for token in tokenize.generate_tokens(StringIO(contents).readline):
                if token.type == tokenize.NAME:
                    tokens.append(token.string)
        except tokenize.TokenError:
            pass
        counter = Counter(tokens)
        most_common_count: int = counter.most_common(1)[0][1]
        return {
            name: count / most_common_count
            for name, count in counter.items()
        }
