import json
import logging
from abc import ABC, abstractmethod

from openai import AsyncOpenAI
from anthropic import AsyncAnthropic

from app.taxonomy import format_taxonomy_for_prompt, VALID_CODES

logger = logging.getLogger(__name__)

CLASSIFICATION_PROMPT = """You are an expert classifier for ferrofluid / magnetic fluid research literature.

You must classify the following document using ONLY the abstract text below.
Do NOT use the title or keywords for classification — only the abstract content.

ABSTRACT:
{abstract}

{taxonomy}

INSTRUCTIONS:
- Assign a Primary class code (most relevant to the abstract).
- Assign a Secondary class code (second most relevant).
- Assign a Tertiary class code (third most relevant).
- If the abstract covers only one clear subject, all three may be the same code.
- Use ONLY the numeric codes listed above (11-51).
- Provide brief reasoning explaining your classification choices.

Respond ONLY with valid JSON in this exact format:
{{
    "primary": <integer code>,
    "secondary": <integer code>,
    "tertiary": <integer code>,
    "reasoning": "<brief justification>"
}}
"""


class ClassificationError(Exception):
    """Raised when an AI classification call fails."""


def parse_response(raw: str, model_name: str) -> dict:
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        raise ClassificationError(
            f"Model '{model_name}' returned invalid JSON: {e}\nRaw: {text[:200]}"
        ) from e

    primary = int(data["primary"])
    secondary = int(data["secondary"])
    tertiary = int(data["tertiary"])

    # Validate codes
    for code in [primary, secondary, tertiary]:
        if code not in VALID_CODES:
            raise ClassificationError(
                f"Model '{model_name}' returned invalid class code {code}. "
                f"Valid codes: {sorted(VALID_CODES)}"
            )

    return {
        "primary": primary,
        "secondary": secondary,
        "tertiary": tertiary,
        "reasoning": data.get("reasoning", ""),
    }


class BaseClassifier(ABC):
    @abstractmethod
    async def classify(self, abstract: str) -> dict:
        ...


class GPTClassifier(BaseClassifier):
    def __init__(self, api_key: str, model: str = "gpt-4o"):
        self._client = AsyncOpenAI(api_key=api_key)
        self._model = model

    async def classify(self, abstract: str) -> dict:
        prompt = CLASSIFICATION_PROMPT.format(
            abstract=abstract,
            taxonomy=format_taxonomy_for_prompt(),
        )
        try:
            response = await self._client.chat.completions.create(
                model=self._model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
            )
            raw = response.choices[0].message.content
        except Exception as e:
            logger.error("GPT call failed: %s", e)
            raise ClassificationError(f"GPT API call failed: {e}") from e

        return parse_response(raw, self._model)


class ClaudeClassifier(BaseClassifier):
    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514"):
        self._client = AsyncAnthropic(api_key=api_key)
        self._model = model

    async def classify(self, abstract: str) -> dict:
        prompt = CLASSIFICATION_PROMPT.format(
            abstract=abstract,
            taxonomy=format_taxonomy_for_prompt(),
        )
        try:
            response = await self._client.messages.create(
                model=self._model,
                max_tokens=512,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
            )
            raw = response.content[0].text
        except Exception as e:
            logger.error("Claude call failed: %s", e)
            raise ClassificationError(f"Claude API call failed: {e}") from e

        return parse_response(raw, self._model)
