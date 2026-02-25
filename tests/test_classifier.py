import pytest

from app.services.classifier import ClassificationError, parse_response


class TestParseResponse:
    def test_valid_json(self):
        raw = '{"primary": 11, "secondary": 13, "tertiary": 14, "reasoning": "Material chemistry"}'
        result = parse_response(raw, "test")
        assert result["primary"] == 11
        assert result["secondary"] == 13
        assert result["tertiary"] == 14
        assert "Material" in result["reasoning"]

    def test_json_in_code_block(self):
        raw = '```json\n{"primary": 38, "secondary": 42, "tertiary": 42, "reasoning": "test"}\n```'
        result = parse_response(raw, "test")
        assert result["primary"] == 38

    def test_all_same_code(self):
        raw = '{"primary": 50, "secondary": 50, "tertiary": 50, "reasoning": "Pure review"}'
        result = parse_response(raw, "test")
        assert result["primary"] == result["secondary"] == result["tertiary"] == 50

    def test_invalid_json(self):
        with pytest.raises(ClassificationError, match="invalid JSON"):
            parse_response("not json", "test")

    def test_invalid_code(self):
        raw = '{"primary": 99, "secondary": 11, "tertiary": 11, "reasoning": "bad"}'
        with pytest.raises(ClassificationError, match="invalid class code"):
            parse_response(raw, "test")

    def test_whitespace_handling(self):
        raw = '  \n{"primary": 21, "secondary": 22, "tertiary": 25, "reasoning": "Computation"}  '
        result = parse_response(raw, "test")
        assert result["primary"] == 21
