from app.services.consensus import check_consensus


class TestConsensus:
    def test_agreement(self):
        gpt = {"primary": 11, "secondary": 13, "tertiary": 14, "reasoning": "GPT says material"}
        claude = {"primary": 11, "secondary": 12, "tertiary": 14, "reasoning": "Claude says material"}

        result = check_consensus(gpt, claude)
        assert result["status"] == "agreed"
        assert result["primary"] == 11
        assert "Both models agreed" in result["reasoning"]

    def test_disagreement(self):
        gpt = {"primary": 11, "secondary": 13, "tertiary": 14, "reasoning": "GPT says material"}
        claude = {"primary": 38, "secondary": 42, "tertiary": 42, "reasoning": "Claude says application"}

        result = check_consensus(gpt, claude)
        assert result["status"] == "disagreed"
        assert "DISAGREEMENT" in result["reasoning"]

    def test_agreement_uses_gpt_secondary_tertiary(self):
        gpt = {"primary": 25, "secondary": 26, "tertiary": 22, "reasoning": "flow"}
        claude = {"primary": 25, "secondary": 21, "tertiary": 28, "reasoning": "flow comp"}

        result = check_consensus(gpt, claude)
        assert result["status"] == "agreed"
        assert result["secondary"] == 26  # GPT's secondary
        assert result["tertiary"] == 22   # GPT's tertiary
