from src.application.contracts.repositories import TicketRepository
from src.application.contracts.use_cases import UpdateTicket as UpdateTicketContract
from src.application.dtos.update_ticket import UpdateTicketInput, UpdateTicketOutput


class UpdateTicket(UpdateTicketContract):
    def __init__(self, repository: TicketRepository) -> None:
        self._repository = repository

    async def execute(self, input_dto: UpdateTicketInput) -> UpdateTicketOutput:
        entity = await self._repository.get(input_dto.ticket_id)
        if not entity:
            raise ValueError(f"Ticket {input_dto.ticket_id} not found")
        update_data = input_dto.model_dump(exclude={"ticket_id"}, exclude_none=True)
        for field, value in update_data.items():
            setattr(entity, field, value)
        await self._repository.update(entity)
        return UpdateTicketOutput(ticket=entity)
