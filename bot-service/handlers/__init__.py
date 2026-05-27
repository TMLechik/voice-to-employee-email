from aiogram import Router

from ml_service import RecipientMatcher, RuBertSlotFillingService, SpeechToTextService
from services import BotService

from .add_recipient import get_router as add_recipient_router
from .fallback import get_router as fallback_router
from .help import get_router as help_router
from .ids import get_router as ids_router
from .recipients import get_router as recipients_router
from .remove_recipient import get_router as remove_recipient_router
from .send import get_router as send_router
from .start import get_router as start_router


def create_router(
    service: BotService,
    stt_service: SpeechToTextService,
    slot_filling_service: RuBertSlotFillingService,
    recipient_matcher: RecipientMatcher,
) -> Router:
    router = Router(name="bot-service")

    for router_factory in (
        start_router,
        help_router,
        ids_router,
        add_recipient_router,
        recipients_router,
        remove_recipient_router,
    ):
        router.include_router(router_factory(service))

    router.include_router(
        send_router(
            service=service,
            stt_service=stt_service,
            slot_filling_service=slot_filling_service,
            recipient_matcher=recipient_matcher,
        )
    )
    router.include_router(fallback_router(service))

    return router
