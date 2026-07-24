import os
import json
import anthropic

MODEL = "claude-opus-4-8"

SUGGESTION_SCHEMA = {
    "type": "object",
    "properties": {
        "overall_assessment": {"type": "string"},
        "suggestions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "category": {"type": "string"},
                    "issue": {"type": "string"},
                    "suggestion": {"type": "string"}
                },
                "required": ["category", "issue", "suggestion"],
                "additionalProperties": False
            }
        }
    },
    "required": ["overall_assessment", "suggestions"],
    "additionalProperties": False
}


def _build_prompt(resume_text: str, job_description: str | None) -> str:
    prompt = f"Review this resume and give specific, actionable improvement suggestions.\n\nResume:\n{resume_text[:6000]}"
    if job_description:
        prompt += f"\n\nTailor suggestions toward this target job description:\n{job_description[:3000]}"
    return prompt


def generate_resume_suggestions(resume_text: str, job_description: str | None, fallback_data: dict) -> dict:
    """Call Claude for resume improvement suggestions. Falls back to existing rule-based
    analysis (ATS score / keyword match issues) if the API key is missing or the call fails."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return _fallback_response("AI suggestions are not configured (no API key set).", fallback_data)

    try:
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model=MODEL,
            max_tokens=1024,
            output_config={"format": {"type": "json_schema", "schema": SUGGESTION_SCHEMA}},
            messages=[{"role": "user", "content": _build_prompt(resume_text, job_description)}]
        )
        text = next(b.text for b in response.content if b.type == "text")
        result = json.loads(text)
        result["source"] = "ai"
        return result
    except anthropic.RateLimitError:
        return _fallback_response("AI suggestions are temporarily rate-limited. Showing rule-based analysis instead.", fallback_data)
    except anthropic.APIConnectionError:
        return _fallback_response("Could not reach the AI service. Showing rule-based analysis instead.", fallback_data)
    except anthropic.APIStatusError:
        return _fallback_response("The AI service returned an error. Showing rule-based analysis instead.", fallback_data)
    except Exception:
        return _fallback_response("AI suggestions are temporarily unavailable. Showing rule-based analysis instead.", fallback_data)


def _fallback_response(message: str, fallback_data: dict) -> dict:
    suggestions = []
    for issue in fallback_data.get("ats_issues", []):
        suggestions.append({"category": "ATS Compatibility", "issue": issue, "suggestion": "Address this to improve ATS parseability."})
    for skill in fallback_data.get("missing_keywords", [])[:10]:
        suggestions.append({"category": "Keywords", "issue": f"'{skill}' not found in resume", "suggestion": f"Consider adding '{skill}' if it genuinely applies to your experience."})

    return {
        "overall_assessment": message,
        "suggestions": suggestions,
        "source": "fallback"
    }
