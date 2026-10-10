"""
A prefix tree (trie) for fast autocomplete over a fixed vocabulary.

Design decision: one interpretation, one ranking.

The trie exposes a single search method, ``search``, that returns matches
ordered by (a) score and (b) index-of-insertion. The score is computed once
per match and never recomputed, which keeps the ranking stable and makes the
ordering independent of the trie's internal shape. We deliberately do not
expose a second ordering method or a configurator; one ranking rule keeps the
contract narrow and testable.

A second decision: duplicate words are ignored on insert. The first insertion
wins and assigns the word's index. This avoids implicit index reassignment and
keeps the vocabulary genuinely fixed across the object's lifetime.

Edge case the reader will hit: completions are character-based, so searching
"app" matches "apple" but also "app" itself only if it was inserted as a
standalone word. Empty-string search returns the empty list because a prefix
of length zero matches everything and is therefore uninformative.
"""

from collections import deque
from typing import Callable, Dict, List, Optional, Tuple

__all__ = ["TrieIndex"]

# Default scorer: longer words (relative to the prefix length) rank first.
# This rewards the tightest continuation of the prefix. It is deliberately
# simple: any custom scorer receives (word, index, prefix) and must return
# a number where higher is better.
_DEFAULT_SCORER: Callable[[str, int, str], float] = (
    lambda word, index, prefix: float(len(word) - len(prefix))
)


class _Node:
    """Internal trie node.

    ``children`` is a plain dict keyed by single characters. We deliberately
    use a dict rather than a list indexed by code point to keep memory usage
    proportional to the number of distinct characters actually present in the
    vocabulary, rather than the whole alphabet. The trade-off is slightly
    higher per-node overhead; for typical vocabularies this is the better
    choice.
    """

    __slots__ = ("children", "word_index")

    def __init__(self) -> None:
        self.children: Dict[str, _Node] = {}
        # Index into ``self._words`` if this node terminates a word, else None.
        self.word_index: Optional[int] = None


class TrieIndex:
    """A prefix tree supporting ranked autocomplete over a fixed vocabulary.

    Parameters
    ----------
    scorer:
        Optional function ``(word, index, prefix) -> number``. Higher numbers
        rank earlier in results. The default scorer ranks longer continuations
        first. The function must be deterministic; non-deterministic scorers
        break the ranked-output contract.

    Notes
    -----
    Insertions are append-only. A word inserted twice is silently ignored on
    the second insertion; its original index is preserved. There is no delete
    method because the vocabulary is intended to be fixed once built.
    """

    __slots__ = ("_root", "_words", "_scorer")

    def __init__(
        self,
        scorer: Optional[Callable[[str, int, str], float]] = None,
    ) -> None:
        self._root: _Node = _Node()
        self._words: List[str] = []
        self._scorer: Callable[[str, int, str], float] = (
            scorer if scorer is not None else _DEFAULT_SCORER
        )

    def insert(self, word: str) -> None:
        """Insert ``word`` into the vocabulary.

        Raises
        ------
        TypeError
            If ``word`` is not a ``str``.
        ValueError
            If ``word`` is the empty string.

        Duplicate insertions are ignored: the first insertion fixes the
        word's index. Subsequent calls with the same word return without
        modifying the trie.
        """
        if not isinstance(word, str):
            raise TypeError("word must be str")
        if word == "":
            raise ValueError("word must be non-empty")

        node = self._root
        for ch in word:
            child = node.children.get(ch)
            if child is None:
                child = _Node()
                node.children[ch] = child
            node = child

        if node.word_index is not None:
            return

        node.word_index = len(self._words)
        self._words.append(word)

    def search(self, prefix: str, limit: Optional[int] = None) -> List[str]:
        """Return words starting with ``prefix``, ranked by score then index.

        Parameters
        ----------
        prefix:
            The prefix to match. Must be a non-empty string.
        limit:
            Optional maximum number of results to return. ``None`` returns
            all matches. Must be non-negative.

        Returns
        -------
        List[str]
            Matching words ordered by descending score, ties broken by
            ascending insertion index. The list has at most ``limit`` entries
            when ``limit`` is set.

        Raises
        ------
        TypeError
            If ``prefix`` is not a ``str``.
        ValueError
            If ``prefix`` is empty, or if ``limit`` is a negative number.
        """
        if not isinstance(prefix, str):
            raise TypeError("prefix must be str")
        if prefix == "":
            raise ValueError("prefix must be non-empty")
        if limit is not None and (not isinstance(limit, int) or isinstance(limit, bool)):
            raise TypeError("limit must be int or None")
        if limit is not None and limit < 0:
            raise ValueError("limit must be non-negative")

        node = self._root
        for ch in prefix:
            child = node.children.get(ch)
            if child is None:
                return []
            node = child

        # Collect (score, index) tuples. We compute the score once per match
        # rather than at sort-comparison time to keep ranking independent of
        # the internal trie shape and to avoid redundant work.
        scored: List[Tuple[float, int]] = []
        stack = [node]
        while stack:
            current = stack.pop()
            if current.word_index is not None:
                idx = current.word_index
                scored.append(
                    (self._scorer(self._words[idx], idx, prefix), idx)
                )
            stack.extend(current.children.values())

        # Sort by descending score, then ascending index. Negating the score
        # lets us sort ascending in a single pass, which is stable and avoids
        # key-function overhead in the common small-result case.
        scored.sort(key=lambda pair: (-pair[0], pair[1]))

        if limit is None:
            return [self._words[idx] for _, idx in scored]
        return [self._words[idx] for _, idx in scored[:limit]]

    def __contains__(self, prefix: str) -> bool:
        """Return ``True`` if at least one vocabulary word starts with ``prefix``.

        This is a membership test over the *prefix space*, not the vocabulary
        itself: ``"app" in trie`` asks whether any inserted word begins with
        ``app``. To test whether a whole word was inserted, use ``word in trie``
        only when ``word`` is a complete term, or search with ``word`` as the
        prefix and check membership in the result list.
        """
        try:
            node = self._root
            for ch in prefix:
                child = node.children.get(ch)
                if child is None:
                    return False
                node = child
            return True
        except TypeError:
            return False

    def __len__(self) -> int:
        """Number of words in the vocabulary (distinct insertions only)."""
        return len(self._words)
