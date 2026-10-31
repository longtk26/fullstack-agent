import uuid
from datetime import date
from typing import Annotated

from fastapi import Depends

from src.modules.cards.ports.output import ICardRepoDep
from src.modules.cards.presenter.dtos import CardResponseDto


class ListDueCardUsecase:
    def __init__(self, card_repo: ICardRepoDep):
        self.card_repo = card_repo

    async def execute(self, deck_id: uuid.UUID | None = None) -> list[CardResponseDto]:
        filters = {"deck_id": deck_id} if deck_id is not None else {}
        cards, total = self.card_repo.list(filters=filters, sort=None, limit=1000, offset=0)
        due = [c for c in cards if c.due_date and c.due_date <= date.today()]
        return [CardResponseDto.from_entity(c) for c in due]


ListDueCardUsecaseDep = Annotated[ListDueCardUsecase, Depends(ListDueCardUsecase)]
