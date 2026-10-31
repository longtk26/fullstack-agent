import uuid
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Annotated

from fastapi import Depends

from src.libs.decorators.transactional_decorator import Transactional
from src.libs.exceptions import NotFoundException
from src.modules.cards.ports.output import ICardRepoDep
from src.modules.cards.presenter.dtos import CardResponseDto
from src.modules.cards.presenter.dtos.review_card_dto import ReviewCardRequestDto
from src.modules.review_logs.ports.output import IReviewLogRepoDep
from src.modules.shared.domain.entities import ReviewLogEntity


class ReviewCardUsecase:
    def __init__(self, card_repo: ICardRepoDep, review_log_repo: IReviewLogRepoDep):
        self.card_repo = card_repo
        self.review_log_repo = review_log_repo

    @Transactional
    async def execute(self, id: uuid.UUID, body: ReviewCardRequestDto) -> CardResponseDto:
        card = self.card_repo.find_by_id(id)
        if not card:
            raise NotFoundException("Card not found", details={"id": str(id)})

        rating = body.rating
        ease = float(card.ease) if card.ease is not None else 2.5
        interval = card.interval_days or 0
        rep = card.repetition_count or 0

        if rating == "again":
            rep = 0
            interval = 1
            ease = max(1.3, ease - 0.2)
        elif rating == "hard":
            interval = max(1, int(interval * 1.2)) if interval > 0 else 1
            rep += 1
            ease = max(1.3, ease - 0.15)
        elif rating == "good":
            if rep == 0:
                interval = 1
            elif rep == 1:
                interval = 6
            else:
                interval = int(interval * ease)
            rep += 1
        elif rating == "easy":
            if rep == 0:
                interval = 1
            elif rep == 1:
                interval = 6
            else:
                interval = int(interval * ease * 1.3)
            rep += 1
            ease = ease + 0.15

        due = date.today() + timedelta(days=interval)
        card.interval_days = interval
        card.ease = Decimal(str(round(ease, 2)))
        card.repetition_count = rep
        card.due_date = due

        updated = self.card_repo.update(card)

        log = ReviewLogEntity(
            id=uuid.uuid4(),
            card_id=card.id,
            rating=rating,
            interval_days=interval,
            ease=Decimal(str(round(ease, 2))),
            reviewed_at=datetime.now(UTC),
        )
        self.review_log_repo.create(log)

        return CardResponseDto.from_entity(updated)


ReviewCardUsecaseDep = Annotated[ReviewCardUsecase, Depends(ReviewCardUsecase)]
