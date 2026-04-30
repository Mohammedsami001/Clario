import json
import logging

from groq import Groq

from app.core.config import settings

logger = logging.getLogger(__name__)

_client: Groq | None = None

SYSTEM_PROMPT = (
    "You are an expert educational content summarizer. "
    "Given a lecture transcript segment, extract the key learning content. "
    "Always respond with valid JSON only — no markdown, no explanation."
)

USER_PROMPT = """\
Analyze this lecture transcript segment and respond ONLY with JSON.

Transcript:
{transcript}

Required JSON format:
{{
  "title": "Punchy concept title (max 8 words)",
  "summary": "One clear sentence explaining the main concept",
  "bullets": [
    "Key point 1 (concise)",
    "Key point 2 (concise)",
    "Key point 3 (concise)"
  ],
  "tags": ["topic1", "topic2"]
}}"""


def _get_client() -> Groq:
    global _client
    if _client is None:
        _client = Groq(api_key=settings.GROQ_API_KEY)
    return _client


def summarize_segment(transcript: str, index: int) -> dict:
    """
    Call Groq (llama3-8b-8192) to generate a title, summary, bullets, and tags
    for a given transcript segment. Falls back gracefully if the API fails.
    """
    client = _get_client()

    # Truncate to avoid token overflow
    truncated = transcript[:3000]

    try:
        response = client.chat.completions.create(
            model="llama3-8b-8192",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": USER_PROMPT.format(transcript=truncated)},
            ],
            temperature=0.3,
            max_tokens=400,
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content
        result = json.loads(content)

        return {
            "title": result.get("title", f"Concept {index + 1}"),
            "summary": result.get("summary", ""),
            "bullets": result.get("bullets", []),
            "tags": result.get("tags", []),
        }

    except Exception as e:
        logger.error(f"Groq summarization failed for segment {index}: {e}")
        # Graceful fallback — use first sentence as summary
        first_sentence = transcript.split(".")[0].strip()
        return {
            "title": f"Concept {index + 1}",
            "summary": first_sentence or transcript[:120],
            "bullets": [],
            "tags": [],
        }
