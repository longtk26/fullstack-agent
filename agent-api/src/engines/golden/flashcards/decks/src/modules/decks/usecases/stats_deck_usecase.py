import uuid
from datetime import date
from typing import Annotated

from fastapi import Depends

from src.libs.exceptions import NotFoundException
from src.modules.cards.ports.output import ICardRepoDep
from src.modules.decks.ports.output import IDeckRepoDep
from src.modules.decks.presenter.dtos.stats_deck_dto import StatsDeckResponseDto


class StatsDeckUsecase:
    def __init__(self, deck_repo: IDeckRepoDep, card_repo: ICardRepoDep):
        self.deck_repo = deck_repo
        self.card_repo = card_repo

    async def execute(self, id: uuid.UUID) -> StatsDeckResponseDto:
        deck = self.deck_repo.find_by_id(id)
        if deck is None:
            raise NotFoundException("Deck not found", details={"id": str(id)})

        cards, total = self.card_repo.list(filters={"deck_id": id}, sort=None, limit=1000, offset=0)
        due_today = sum(1 for c in cards if c.due_date and c.due_date <= date.today())
        learned = sum(1 for c in cards if c.repetition_count and c.repetition_count > 0)
        return StatsDeckResponseDto(total=total, due_today=due_today, learned=learned)


StatsDeckUsecaseDep = Annotated[StatsDeckUsecase, Depends(StatsDeckUsecase)]
