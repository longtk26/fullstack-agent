from fastapi import Request

from src.libs.exceptions import PayloadTooLargeException


async def read_body_limited(request: Request, max_bytes: int) -> bytes:
    """Reads the raw body (kept byte-for-byte for specs) without buffering more than `max_bytes`."""
    declared = request.headers.get("content-length")
    if declared and declared.isdigit() and int(declared) > max_bytes:
        raise PayloadTooLargeException(f"Body exceeds {max_bytes} bytes")
    chunks, size = [], 0
    async for chunk in request.stream():
        size += len(chunk)
        if size > max_bytes:
            raise PayloadTooLargeException(f"Body exceeds {max_bytes} bytes")
        chunks.append(chunk)
    return b"".join(chunks)
