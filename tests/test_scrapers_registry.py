"""Tests for the scraper registry completeness."""

import pytest


def test_all_scrapers_importable():
    """All scraper classes in ALL_SCRAPERS must be importable."""
    from regutrack.scrapers import ALL_SCRAPERS
    assert len(ALL_SCRAPERS) == 31, f"Expected 31 scrapers, got {len(ALL_SCRAPERS)}"


def test_scrapers_have_required_attributes():
    """Every scraper must define entity_name, entity_url, entity_group."""
    from regutrack.scrapers import ALL_SCRAPERS
    for cls in ALL_SCRAPERS:
        assert cls.entity_name, f"{cls.__name__} missing entity_name"
        assert cls.entity_url, f"{cls.__name__} missing entity_url"
        assert cls.entity_group, f"{cls.__name__} missing entity_group"


def test_scrapers_by_key_coverage():
    """Every key in SCRAPERS_BY_KEY must map to a class in ALL_SCRAPERS."""
    from regutrack.scrapers import ALL_SCRAPERS, SCRAPERS_BY_KEY
    all_set = set(ALL_SCRAPERS)
    for key, cls in SCRAPERS_BY_KEY.items():
        assert cls in all_set, f"Key '{key}' maps to {cls} which is not in ALL_SCRAPERS"


def test_no_duplicate_entity_names():
    """Entity names must be unique across all scrapers."""
    from regutrack.scrapers import ALL_SCRAPERS
    names = [cls.entity_name for cls in ALL_SCRAPERS]
    assert len(names) == len(set(names)), "Duplicate entity names found"
