"""Tests for hashing and change detection."""

import pytest
from datetime import date
from regutrack.utils.hashing import DocumentResult


def test_compute_hash_stability():
    """Same content must always produce the same hash."""
    doc = DocumentResult(
        title="Resolución 123 de 2024",
        url="https://www.anh.gov.co/resoluciones/123",
        number="123",
        doc_type="Resolución",
    )
    h1 = doc.compute_hash()
    h2 = doc.compute_hash()
    assert h1 == h2
    assert len(h1) == 64  # SHA-256 hex


def test_compute_hash_different_docs():
    """Different documents must produce different hashes."""
    doc1 = DocumentResult(title="Resolución 123", url="https://example.com/r123", number="123")
    doc2 = DocumentResult(title="Resolución 456", url="https://example.com/r456", number="456")
    assert doc1.compute_hash() != doc2.compute_hash()


def test_compute_hash_case_insensitive():
    """Title case should not affect hash (normalized to lowercase)."""
    doc1 = DocumentResult(title="Resolución 123", url="https://example.com/r123")
    doc2 = DocumentResult(title="resolución 123", url="https://example.com/r123")
    assert doc1.compute_hash() == doc2.compute_hash()


def test_compute_hash_whitespace_insensitive():
    """Leading/trailing whitespace should not change hash."""
    doc1 = DocumentResult(title="  Resolución 123  ", url="https://example.com/r123")
    doc2 = DocumentResult(title="Resolución 123", url="https://example.com/r123")
    assert doc1.compute_hash() == doc2.compute_hash()


def test_is_valid():
    """Documents without titles are invalid."""
    valid = DocumentResult(title="Resolución 1", url="https://example.com")
    invalid_empty = DocumentResult(title="", url="https://example.com")
    invalid_whitespace = DocumentResult(title="   ", url="https://example.com")

    assert valid.is_valid()
    assert not invalid_empty.is_valid()
    assert not invalid_whitespace.is_valid()
