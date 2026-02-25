import logging

from app.taxonomy import get_class_description

logger = logging.getLogger(__name__)


def check_consensus(gpt_result: dict, claude_result: dict) -> dict:
    """
    Compare GPT and Claude classifications.
    Agreement = primary class codes match.
    Returns finalized classification dict with status.
    """
    gpt_p = gpt_result["primary"]
    claude_p = claude_result["primary"]

    if gpt_p == claude_p:
        # Full agreement on primary — accept GPT's full result
        # (use GPT secondary/tertiary but merge reasoning)
        reasoning = (
            f"Both models agreed on primary class {gpt_p} ({get_class_description(gpt_p)}). "
            f"GPT reasoning: {gpt_result['reasoning']} | "
            f"Claude reasoning: {claude_result['reasoning']}"
        )
        return {
            "primary": gpt_p,
            "secondary": gpt_result["secondary"],
            "tertiary": gpt_result["tertiary"],
            "reasoning": reasoning,
            "status": "agreed",
        }
    else:
        # Disagreement — flag for review, use GPT as tentative
        reasoning = (
            f"DISAGREEMENT: GPT chose {gpt_p} ({get_class_description(gpt_p)}), "
            f"Claude chose {claude_p} ({get_class_description(claude_p)}). "
            f"GPT reasoning: {gpt_result['reasoning']} | "
            f"Claude reasoning: {claude_result['reasoning']}"
        )
        logger.warning(
            "Disagreement on document: GPT=%d vs Claude=%d", gpt_p, claude_p
        )
        return {
            "primary": gpt_p,
            "secondary": gpt_result["secondary"],
            "tertiary": gpt_result["tertiary"],
            "reasoning": reasoning,
            "status": "disagreed",
        }
