"""
Tests for utils module

Test request ID generation functionality.
"""

import unittest
from linlog.utils import (
    generate_request_id,
    DEFAULT_ALPHABET
)


class TestGenerateRequestId(unittest.TestCase):
    """Test generate_request_id function"""

    def test_default_length(self):
        """Test default length is 7"""
        request_id = generate_request_id()
        self.assertEqual(len(request_id), 7)

    def test_custom_length(self):
        """Test custom length"""
        for length in [3, 5, 10, 20]:
            request_id = generate_request_id(length=length)
            self.assertEqual(len(request_id), length)

    def test_default_alphabet(self):
        """Test default alphabet is base62"""
        # Generate many IDs to test character set
        for _ in range(100):
            request_id = generate_request_id()
            for char in request_id:
                self.assertIn(char, DEFAULT_ALPHABET)

    def test_custom_alphabet(self):
        """Test custom alphabet"""
        alphabet = '0123456789'
        request_id = generate_request_id(length=10, alphabet=alphabet)
        
        self.assertEqual(len(request_id), 10)
        self.assertTrue(request_id.isdigit())

    def test_uniqueness(self):
        """Test generated IDs are unique"""
        ids = [generate_request_id() for _ in range(1000)]
        unique_ids = set(ids)
        
        # All IDs should be unique
        self.assertEqual(len(ids), len(unique_ids))

    def test_randomness(self):
        """Test IDs are not sequential or predictable"""
        id1 = generate_request_id()
        id2 = generate_request_id()
        
        self.assertNotEqual(id1, id2)
