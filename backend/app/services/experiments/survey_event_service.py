from uuid import UUID

from sqlalchemy import select

from app.models.survey import Survey, SurveyItem
from app.services.experiments.experiment_event_service import ExperimentEventService


async def record_survey_event(session, survey: Survey, data, event_type: str):
    if data.survey_id != survey.id:
        raise ValueError("Survey identifier does not match the invitation")
    result = await session.execute(
        select(SurveyItem.product_id, SurveyItem.buy_click_id).where(SurveyItem.survey_id == survey.id)
    )
    click_ids = dict(result.all())
    allowed = set(click_ids)
    requested = set(data.product_ids)
    last = getattr(data, "last_product_id", None)
    if not requested.issubset(allowed) or (last is not None and last not in allowed):
        raise ValueError("Event contains a product outside this survey")
    if data.items_count != len(requested):
        raise ValueError("items_count must count the distinct product_ids in this event")
    payload = data.model_dump(mode="json", exclude={"session_id", "timestamp"})
    payload["buy_click_ids"] = {str(p): str(click_ids[p]) if click_ids[p] else None for p in requested}
    return await ExperimentEventService.create_event(
        session=session, user_id=survey.user_id, event_type=event_type,
        session_id=data.session_id, event_timestamp=data.timestamp, payload=payload,
    )
