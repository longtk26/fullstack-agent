# Gemini Image Generation (`gemini-3.1-flash-lite-image`)

Documented findings and probe results from 2026-10-31 (Epic 19, Story 19.2).

## API Endpoint & Model

- **Model**: `gemini-3.1-flash-lite-image` ("Nano Banana" family)
- **Endpoint**: `POST https://generativelanguage.googleapis.com/v1beta/interactions`
- **Authentication**: `x-goog-api-key: <GEMINI_IMAGE_API_KEY>` header. Photos are opt-in: with `IMAGE_PROVIDER=gemini`
  (the default) and no `GEMINI_IMAGE_API_KEY`, photos are off; `GEMINI_API_KEY` (Antigravity's key) is never used.
- **Cost**: $0.0336 per image at 1K resolution.
- **Aspect Ratios**: `1:1`, `3:4`, `4:3`, `16:9`, `21:9` (all supported by FrontendSpec).
- **Supported Size**: `1K`

## Request Format

```http
POST /v1beta/interactions HTTP/1.1
Host: generativelanguage.googleapis.com
x-goog-api-key: <KEY>
Content-Type: application/json

{
  "model": "gemini-3.1-flash-lite-image",
  "input": "<prompt>. <style>. Photorealistic photograph. No text, letters, logos or watermarks in the image.",
  "response_format": {
    "type": "image",
    "mime_type": "image/jpeg",
    "aspect_ratio": "16:9",
    "image_size": "1K"
  }
}
```

## Response Format (Success)

HTTP Status: `200 OK`

```json
{
  "id": "v1_...",
  "status": "completed",
  "usage": {
    "total_tokens": 1561,
    "total_input_tokens": 47,
    "input_tokens_by_modality": [{"modality": "text", "tokens": 47}],
    "total_output_tokens": 1514,
    "output_tokens_by_modality": [{"modality": "image", "tokens": 1120}]
  },
  "created": "2026-10-31T14:16:09Z",
  "steps": [
    {
      "type": "user_input",
      "content": [{"text": "...", "type": "text"}]
    },
    {
      "type": "thought",
      "signature": "..."
    },
    {
      "type": "model_output",
      "content": [
        {
          "type": "image",
          "mime_type": "image/jpeg",
          "data": "/9j/4AAQSkZJRg..."
        }
      ]
    }
  ],
  "object": "interaction",
  "model": "gemini-3.1-flash-lite-image"
}
```

- **Image Data**: Base64 encoded JPEG in `steps[].content[]` where `step.type == "model_output"` and `item.type == "image"`.
- **Measured Latency**: ~8.7s.
- **Measured Image Size**: ~682 KB JPEG, 1376x768 pixels (for 16:9 1K).
- SynthID watermark is embedded in the returned image.

## Response Format (Blocked / Refused Prompt)

HTTP Status: `200 OK`

```json
{
  "id": "v1_...",
  "status": "completed",
  "steps": [
    {
      "type": "model_output",
      "content": [
        {
          "type": "text",
          "text": "I can't generate an image of ..."
        }
      ]
    }
  ]
}
```

When refused, the model output step contains only a `text` item explaining the refusal, with no `image` item. In this case, `GeminiImageGenerator` raises `ImageBlocked(reason=text)`.

## How the agent uses it (2026-11-02)

- Photos are made at the end of drafting only (`orchestrator/drafting.py`), at most `FRONTEND_MAX_PHOTOS` (default 8)
  paid calls per draft; the rest stay placeholders with an assumption note. The generation graph has no
  `generate_assets` node (removed in 1e224de), so drawings (`source: "generate"`) render as placeholders.
- `source: "photo"` is valid for kinds `image`, `illustration` and `logo` (logos and illustrations get their own
  prompt suffix, `images/prompt.py`).
- A bad or truncated image, or an unreadable cache entry, never fails a draft: the asset gets a `failed` image call
  (cost kept when the API returned an image) and stays a placeholder; cache files are written atomically.
- `POST /api/v1/spec-drafts/{id}/assets/{assetId}/regenerate` skips the cache read (a new take), works only on a
  finished draft (409 `CONFLICT` otherwise) and stores the upload under the draft's owner. The UI does not call it yet.
- Tests never reach the API: `GeminiImageGenerator(transport=httpx.MockTransport(...))`.
