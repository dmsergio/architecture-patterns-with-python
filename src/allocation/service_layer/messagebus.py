import logging
from typing import Callable, Dict, List, Type, Union

from tenacity import Retrying, RetryError, stop_after_attempt, wait_exponential

from allocation.domain import events, commands
from allocation.service_layer import unit_of_work, handlers

logger = logging.getLogger(__name__)
Message = Union[commands.Command, events.Event]


def handle(message: Message, uow: unit_of_work.AbstractUnitOfWork) -> List:
    results = []
    queue = [message]
    while queue:
        message = queue.pop(0)
        if isinstance(message, events.Event):
            handle_event(message, queue, uow)
        elif isinstance(message, commands.Command):
            command_result = handle_command(message, queue, uow)
            results.append(command_result)
        else:
            raise Exception(f"{message} was not an Event or Command!")
    return results


def handle_event(
        event: events.Event,
        queue: List[Message],
        uow: unit_of_work.AbstractUnitOfWork,
):
    for handler in EVENT_HANDLERS[type(event)]:
        try:
            for attempt in Retrying(
                stop=stop_after_attempt(3),
                wait=wait_exponential(),
            ):
                with attempt:
                    logger.debug("handling event %s with handler %s",
                                 event, handler)
                    handler(event, uow=uow)
                    queue.extend(uow.collect_new_events())
        except RetryError as retry_failure:
            logger.error(
                "Failed to handle event %s times, giving up!",
                retry_failure.last_attempt.attempt_number,
            )
            continue


def handle_command(
        command: commands.Command,
        queue: List[Message],
        uow: unit_of_work.AbstractUnitOfWork,
):
        logger.debug("handling command %s", command)
        try:
            handler = COMMAND_HANDLERS[type(command)]
            result = handler(command, uow=uow)
            queue.extend(uow.collect_new_events())
            return result
        except Exception:
            logger.exception("Exception handling command %s", command)
            raise


EVENT_HANDLERS = {
    events.OutOfStock: [handlers.send_out_of_stock_notification],
}  # type: Dict[Type[events.Event], List[Callable]]


COMMAND_HANDLERS = {
    commands.Allocate: handlers.allocate,
    commands.CreateBatch: handlers.add_batch,
    commands.ChangeBatchQuantity: handlers.change_batch_quantity,
}  # type: Dict[Type[commands.Command], Callable]
