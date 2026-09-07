"""Phonetic village matching — demo-critical, so tested against realistic ASR noise."""

from __future__ import annotations

import pytest

from setubiz.data.loader import SampleDataSource
from setubiz.matching.village_matcher import indic_soundex, match_villages, transliterate


@pytest.fixture
def source():
    return SampleDataSource()


@pytest.mark.parametrize(
    ("devanagari", "expected"),
    [("ओरमांझी", "ormanjhi"), ("रातू", "ratu"), ("कांके", "kanke"), ("बेड़ो", "bero")],
)
def test_transliteration_of_devanagari_village_names(devanagari, expected):
    assert transliterate(devanagari) == expected


def test_transliteration_normalizes_latin_input():
    assert transliterate("  Ormanjhi-123 ") == "ormanjhi"
    assert transliterate("") == ""


@pytest.mark.parametrize(
    ("a", "b"),
    [
        ("Ormanjhi", "Ormanji"),  # the aspirate an ASR usually drops
        ("Kanke", "Kankay"),
        ("Bero", "Beroo"),
        ("Ratu", "Raatu"),
        ("Chanho", "Chano"),
    ],
)
def test_aspirates_and_long_vowels_do_not_change_the_phonetic_code(a, b):
    assert indic_soundex(a) == indic_soundex(b)


def test_soundex_separates_genuinely_different_names():
    assert indic_soundex("Ratu") != indic_soundex("Kanke")
    assert indic_soundex("") == ""


@pytest.mark.parametrize(
    "spoken", ["Ormanji", "ormanjhi", "Aurmanjhi", "ओरमांझी", "ORMANJI"]
)
def test_the_intended_village_is_the_top_match(spoken, source):
    matches = match_villages(spoken, source, state="Jharkhand")
    assert matches, spoken
    assert matches[0].name == "Ormanjhi"
    assert matches[0].reason


def test_results_are_ranked_capped_and_confirmable(source):
    matches = match_villages("Nagri", source, limit=3)
    assert 1 <= len(matches) <= 3
    assert [m.score for m in matches] == sorted((m.score for m in matches), reverse=True)
    assert all(0 <= m.score <= 1 for m in matches)
    assert all(m.shrid and m.block and m.district for m in matches)


def test_a_gps_prior_pulls_the_nearby_candidate_up(source):
    near_kanke = (23.4283, 85.3216)
    with_prior = match_villages("Nagri", source, near=near_kanke, limit=5)
    without = match_villages("Nagri", source, limit=5)
    assert with_prior[0].score > without[0].score
    assert "nearby" in with_prior[0].reason


def test_state_and_district_filters_narrow_the_pool(source):
    assert match_villages("Ratu", source, state="Kerala") == ()
    assert match_villages("Ratu", source, district="Ranchi")
    assert match_villages("Ratu", source, district="Bokaro") == ()


def test_empty_and_hopeless_queries_return_nothing(source):
    assert match_villages("   ", source) == ()
    assert match_villages("zzzzqqqq", source) == ()
