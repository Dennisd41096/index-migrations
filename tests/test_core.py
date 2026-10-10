import unittest

from index_migrations import TrieIndex


class TestInsertAndBasic(unittest.TestCase):
    def test_insert_single_word_and_search_exact_prefix(self):
        trie = TrieIndex()
        trie.insert("apple")
        self.assertEqual(trie.search("app"), ["apple"])

    def test_insert_non_string_raises_type_error(self):
        trie = TrieIndex()
        with self.assertRaises(TypeError):
            trie.insert(123)
        with self.assertRaises(TypeError):
            trie.insert(None)
        with self.assertRaises(TypeError):
            trie.insert(["apple"])

    def test_insert_empty_string_raises_value_error(self):
        trie = TrieIndex()
        with self.assertRaises(ValueError):
            trie.insert("")

    def test_duplicate_insert_is_ignored(self):
        trie = TrieIndex()
        trie.insert("apple")
        trie.insert("apple")
        self.assertEqual(len(trie), 1)
        self.assertEqual(trie.search("app"), ["apple"])


class TestSearchRanking(unittest.TestCase):
    def test_ranking_favors_longer_continuations_with_default_scorer(self):
        trie = TrieIndex()
        trie.insert("app")
        trie.insert("apple")
        trie.insert("apples")
        # All three start with "app". The default scorer ranks by
        # (len(word) - len(prefix)), so longer words rank first. Ties on
        # score are broken by insertion order.
        results = trie.search("app")
        self.assertEqual(results, ["apples", "apple", "app"])

    def test_ranking_ties_break_by_insertion_order(self):
        trie = TrieIndex()
        trie.insert("apple")
        trie.insert("apply")
        # Same score, same length; insertion order decides. "apple" first.
        results = trie.search("appl")
        self.assertEqual(results, ["apple", "apply"])

    def test_custom_scorer_orders_results_by_returned_number(self):
        trie = TrieIndex(scorer=lambda word, idx, prefix: float(-idx))
        trie.insert("apple")   # idx 0
        trie.insert("apply")   # idx 1
        trie.insert("app")     # idx 2
        # Scorer returns -idx, so higher idx => lower score => later.
        # Thus insertion order is preserved.
        results = trie.search("app")
        self.assertEqual(results, ["apple", "apply", "app"])


class TestSearchEdges(unittest.TestCase):
    def test_search_empty_prefix_raises_value_error(self):
        trie = TrieIndex()
        trie.insert("apple")
        with self.assertRaises(ValueError):
            trie.search("")

    def test_search_non_string_prefix_raises_type_error(self):
        trie = TrieIndex()
        trie.insert("apple")
        with self.assertRaises(TypeError):
            trie.search(123)
        with self.assertRaises(TypeError):
            trie.search(None)

    def test_search_no_match_returns_empty_list(self):
        trie = TrieIndex()
        trie.insert("apple")
        self.assertEqual(trie.search("ban"), [])

    def test_search_limit_zero_returns_empty_list(self):
        trie = TrieIndex()
        trie.insert("apple")
        self.assertEqual(trie.search("app", limit=0), [])

    def test_search_limit_truncates_results(self):
        trie = TrieIndex()
        trie.insert("app")
        trie.insert("apple")
        trie.insert("apples")
        self.assertEqual(trie.search("app", limit=2), ["apples", "apple"])

    def test_search_limit_larger_than_pool_returns_all(self):
        trie = TrieIndex()
        trie.insert("apple")
        trie.insert("apply")
        self.assertEqual(trie.search("appl", limit=10), ["apple", "apply"])

    def test_search_negative_limit_raises_value_error(self):
        trie = TrieIndex()
        trie.insert("apple")
        with self.assertRaises(ValueError):
            trie.search("app", limit=-1)

    def test_search_bool_limit_raises_type_error(self):
        # bool is a subclass of int; we reject it to avoid silent misuse.
        trie = TrieIndex()
        trie.insert("apple")
        with self.assertRaises(TypeError):
            trie.search("app", limit=True)


class TestContainsAndLen(unittest.TestCase):
    def test_contains_returns_true_for_existing_prefix(self):
        trie = TrieIndex()
        trie.insert("apple")
        self.assertTrue("app" in trie)
        self.assertTrue("apple" in trie)

    def test_contains_returns_false_for_missing_prefix(self):
        trie = TrieIndex()
        trie.insert("apple")
        self.assertFalse("ban" in trie)
        self.assertFalse("b" in trie)

    def test_contains_returns_false_for_non_string(self):
        trie = TrieIndex()
        trie.insert("apple")
        self.assertFalse(123 in trie)
        self.assertFalse(None in trie)

    def test_len_counts_distinct_words(self):
        trie = TrieIndex()
        trie.insert("apple")
        trie.insert("apply")
        trie.insert("apple")
        self.assertEqual(len(trie), 2)


class TestEmptyTrie(unittest.TestCase):
    def test_search_empty_trie_returns_empty_list(self):
        trie = TrieIndex()
        self.assertEqual(trie.search("app"), [])

    def test_len_of_empty_trie_is_zero(self):
        self.assertEqual(len(TrieIndex()), 0)

    def test_contains_empty_trie_returns_false(self):
        self.assertFalse("app" in TrieIndex())


if __name__ == "__main__":
    unittest.main()
