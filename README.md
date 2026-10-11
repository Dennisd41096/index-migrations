# index-migrations

A prefix tree (trie) for fast autocomplete over a fixed vocabulary, with deterministic ranking by a pluggable scorer.

## Usage

```python
from index_migrations import TrieIndex

trie = TrieIndex()
trie.insert("apple")
trie.insert("apply")
trie.insert("app")

# Ranked by descending score, ties by insertion order.
print(trie.search("app"))        # ['apples'-style ordering by default: longer first
print(trie.search("app", limit=2))

# A custom scorer: (word, index, prefix) -> number, higher ranks earlier.
trie_custom = TrieIndex(scorer=lambda word, index, prefix: float(-index))
print(trie_custom.search("app"))  # insertion order preserved

# Prefix membership.
print("app" in trie)             # True
print("ban" in trie)             # False
print(len(trie))                 # 3
```

## Why this exists

The problem is fast prefix lookup over a vocabulary that is built once and queried many times. A trie gives lookup time proportional to the prefix length rather than the vocabulary size. The trade-off is memory: a trie stores per-character nodes rather than a flat list, so for very small vocabularies a linear scan is cheaper. This library is for the case where the vocabulary is large enough for that trade-off to pay.

One interpretation, stated plainly: `search` returns matches ranked by `(score, insertion_index)`. The default scorer ranks longer continuations of the prefix first. There is no second ranking mode and no configurator object — one rule, one method. Duplicate insertions are silently ignored and the first insertion's index is preserved, so the vocabulary is effectively fixed once built.

## Awkward edges

- Empty-string prefix is rejected: a prefix of length zero matches everything, which is uninformative and a likely caller bug.
- `limit` must be an `int` or `None`; a `bool` is rejected because `bool` is a subclass of `int` in Python and passing `True` is almost always a mistake.
- `in trie` tests prefix membership, not whole-word membership. `"app" in trie` is `True` if any inserted word starts with `app`.

## Running the tests

```
PYTHONPATH=src python -m unittest discover -s tests
```
