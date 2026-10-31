"""Photo prompt formatting (Story 19.2)."""

PHOTO_SUFFIX = "Photorealistic photograph. No text, letters, logos or watermarks in the image."
MAX_PROMPT_CHARS = 1000


def build_photo_prompt(prompt: str, style: str | None = None) -> str:
    """Builds the prompt text sent to the image API:
    `<prompt>. <style>. Photorealistic photograph. No text, letters, logos or watermarks in the image.`
    Trimmed to 1 000 characters.
    """
    cleaned_prompt = " ".join((prompt or "").split()).rstrip(".")
    parts = [cleaned_prompt]
    if style:
        cleaned_style = " ".join(style.split()).rstrip(".")
        if cleaned_style:
            parts.append(cleaned_style)
    parts.append(PHOTO_SUFFIX)
    full = ". ".join(p for p in parts if p)
    return full[:MAX_PROMPT_CHARS]
