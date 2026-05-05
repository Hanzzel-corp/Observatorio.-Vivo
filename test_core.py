"""
P2 #24: Tests unitarios mínimos
"""
import pytest
import sqlite3
from pathlib import Path
import tempfile
import sys

# Importar funciones a testear desde app.py
from app import (
    is_numeric_noise,
    is_generic_term,
    is_component_of_better_phrase,
    phrases_from_title,
    canonicalize,
    calculate_confidence,
    classify_outbreak,
)


class TestIsNumericNoise:
    """Tests para is_numeric_noise"""
    
    def test_years_are_noise(self):
        assert is_numeric_noise("2026") is True
        assert is_numeric_noise("1999") is True
        assert is_numeric_noise("2050") is True
    
    def test_single_digits_are_noise(self):
        assert is_numeric_noise("5") is True
        assert is_numeric_noise("0") is True
    
    def test_words_are_not_noise(self):
        assert is_numeric_noise("bitcoin") is False
        assert is_numeric_noise("inteligencia artificial") is False
        assert is_numeric_noise("covid-19") is False


class TestIsGenericTerm:
    """Tests para is_generic_term"""
    
    def test_generic_words(self):
        assert is_generic_term("new") is True
        assert is_generic_term("top") is True
        assert is_generic_term("best") is True
        assert is_generic_term("free") is True
    
    def test_specific_terms(self):
        assert is_generic_term("bitcoin") is False
        assert is_generic_term("inteligencia artificial") is False
        assert is_generic_term("covid") is False


class TestIsComponentOfBetterPhrase:
    """Tests para is_component_of_better_phrase"""
    
    def test_component_detection(self):
        all_terms = ["nuggets", "nuggets denver", "denver nuggets vs lakers"]
        assert is_component_of_better_phrase("nuggets", all_terms) is True
        assert is_component_of_better_phrase("denver", all_terms) is True
    
    def test_full_phrase_not_component(self):
        all_terms = ["nuggets", "nuggets denver"]
        assert is_component_of_better_phrase("nuggets denver", all_terms) is False


class TestPhrasesFromTitle:
    """Tests para phrases_from_title"""
    
    def test_reduces_ngrams(self):
        title = "Los Denver Nuggets ganaron el campeonato de la NBA"
        phrases = phrases_from_title(title)
        # P0: Debería reducir de ~34 a ~10 n-grams
        assert len(phrases) <= 12
        # Debe incluir frases, no solo palabras sueltas
        phrases_text = [p[0] for p in phrases]
        assert any(len(p.split()) >= 2 for p in phrases_text)
    
    def test_no_stop_words_alone(self):
        title = "El La Los Las Un Una De Del Al Y O En A"
        phrases = phrases_from_title(title)
        # No debe retornar solo conectores
        for phrase, _ in phrases:
            assert len(phrase) > 3


class TestCanonicalize:
    """Tests para canonicalize"""
    
    def test_lowercase(self):
        # Usar término sin alias para test de lowercase puro
        assert canonicalize("Hello") == "hello"
        assert canonicalize("NBA") == "nba"
    
    def test_accents(self):
        assert canonicalize("México") == "mexico"
        assert canonicalize("café") == "cafe"


class TestCalculateConfidence:
    """Tests para calculate_confidence"""
    
    def test_high_confidence(self):
        stat = {"term": "covid", "score": 0.85, "regions": 3, "sources": 4, "delta": 0.15, "runs": 5}
        assert calculate_confidence(stat) == "ALTA"
    
    def test_low_confidence(self):
        term = {
            "term": "foo",
            "regions": 1,
            "sources": 1,
            "hits": 2,
            "total": 5.0
        }
        confidence = calculate_confidence(term)
        assert confidence == "BAJA"


class TestClassifyOutbreak:
    """Tests para classify_outbreak"""
    
    def test_evento(self):
        summary = {"term": "evento_test", "regions": 3, "sources": 3, "runs": 2, "total_score": 60, "delta": 0.3, "emergency": 80, "age_hours": 10}
        result = classify_outbreak(summary)
        assert result == "EVENTO"

    def test_brote(self):
        summary = {"term": "brote_test", "regions": 1, "sources": 1, "runs": 2, "total_score": 100, "delta": 0.8, "emergency": 50, "age_hours": 10}
        result = classify_outbreak(summary)
        assert result == "BROTE"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
