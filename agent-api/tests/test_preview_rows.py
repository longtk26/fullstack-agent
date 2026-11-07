"""Two preview commands at once (a backend start also writes the frontend's row): both may find no row; the second
insert must not fail the command (it left a backend preview STARTING forever, 2026-11-07)."""

from sqlmodel import Session

from src.libs.database import db_session_manager
from src.modules.previews.infrastructure.persistence.preview_repository import PreviewRepository
from src.modules.shared.domain.enums import PreviewStatus


def test_a_row_inserted_meanwhile_is_updated_not_duplicated(client, user_headers):
    res = client.post(
        "/api/v1/generations",
        json={"mode": "dynamic", "requirement": {"text": "A small library where members borrow books."},
              "options": {"engine": "fake"}},
        headers=user_headers,
    )  # fmt: skip
    gen_id = res.json()["generationId"]
    with Session(db_session_manager.engine) as first:
        PreviewRepository(first).upsert(gen_id, "frontend", status=PreviewStatus.STOPPED)
        first.commit()
    with Session(db_session_manager.engine) as second:
        repo = PreviewRepository(second)
        real = repo._model
        calls = {"n": 0}

        def stale(generation_id, kind):  # the other command's row is not seen at first, as in the race
            calls["n"] += 1
            return None if calls["n"] == 1 else real(generation_id, kind)

        repo._model = stale  # type: ignore[method-assign]
        preview = repo.upsert(gen_id, "frontend", status=PreviewStatus.STARTING)
        second.commit()
    assert preview.status == PreviewStatus.STARTING
    with Session(db_session_manager.engine) as check:
        assert PreviewRepository(check).find(gen_id, "frontend").status == PreviewStatus.STARTING
