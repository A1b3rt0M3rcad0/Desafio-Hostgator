from abc import ABC, abstractmethod

from src.application.dtos.add_customer import AddCustomerInput, AddCustomerOutput
from src.application.dtos.add_satisfaction_rating import AddSatisfactionRatingInput, AddSatisfactionRatingOutput
from src.application.dtos.add_tag import AddTagInput, AddTagOutput
from src.application.dtos.add_ticket import AddTicketInput, AddTicketOutput
from src.application.dtos.add_ticket_tag import AddTicketTagInput, AddTicketTagOutput
from src.application.dtos.add_user import AddUserInput, AddUserOutput
from src.application.dtos.delete_customer import DeleteCustomerInput, DeleteCustomerOutput
from src.application.dtos.delete_satisfaction_rating import DeleteSatisfactionRatingInput, DeleteSatisfactionRatingOutput
from src.application.dtos.delete_tag import DeleteTagInput, DeleteTagOutput
from src.application.dtos.delete_ticket import DeleteTicketInput, DeleteTicketOutput
from src.application.dtos.delete_ticket_tag import DeleteTicketTagInput, DeleteTicketTagOutput
from src.application.dtos.delete_user import DeleteUserInput, DeleteUserOutput
from src.application.dtos.get_customer import GetCustomerInput, GetCustomerOutput
from src.application.dtos.get_satisfaction_rating import GetSatisfactionRatingInput, GetSatisfactionRatingOutput
from src.application.dtos.get_tag import GetTagInput, GetTagOutput
from src.application.dtos.get_ticket import GetTicketInput, GetTicketOutput
from src.application.dtos.get_user import GetUserInput, GetUserOutput
from src.application.dtos.list_customers import ListCustomersInput, ListCustomersOutput
from src.application.dtos.list_satisfaction_ratings import ListSatisfactionRatingsInput, ListSatisfactionRatingsOutput
from src.application.dtos.list_tags import ListTagsInput, ListTagsOutput
from src.application.dtos.list_tickets import ListTicketsInput, ListTicketsOutput
from src.application.dtos.list_tickets_by_tags import ListTicketsByTagsInput, ListTicketsByTagsOutput
from src.application.dtos.list_users import ListUsersInput, ListUsersOutput
from src.application.dtos.update_customer import UpdateCustomerInput, UpdateCustomerOutput
from src.application.dtos.update_satisfaction_rating import UpdateSatisfactionRatingInput, UpdateSatisfactionRatingOutput
from src.application.dtos.update_tag import UpdateTagInput, UpdateTagOutput
from src.application.dtos.update_ticket import UpdateTicketInput, UpdateTicketOutput
from src.application.dtos.update_user import UpdateUserInput, UpdateUserOutput


class AddUser(ABC):
    @abstractmethod
    async def execute(self, input_dto: AddUserInput) -> AddUserOutput: ...


class GetUser(ABC):
    @abstractmethod
    async def execute(self, input_dto: GetUserInput) -> GetUserOutput: ...


class UpdateUser(ABC):
    @abstractmethod
    async def execute(self, input_dto: UpdateUserInput) -> UpdateUserOutput: ...


class DeleteUser(ABC):
    @abstractmethod
    async def execute(self, input_dto: DeleteUserInput) -> DeleteUserOutput: ...


class ListUsers(ABC):
    @abstractmethod
    async def execute(self, input_dto: ListUsersInput) -> ListUsersOutput: ...


class AddCustomer(ABC):
    @abstractmethod
    async def execute(self, input_dto: AddCustomerInput) -> AddCustomerOutput: ...


class GetCustomer(ABC):
    @abstractmethod
    async def execute(self, input_dto: GetCustomerInput) -> GetCustomerOutput: ...


class UpdateCustomer(ABC):
    @abstractmethod
    async def execute(self, input_dto: UpdateCustomerInput) -> UpdateCustomerOutput: ...


class DeleteCustomer(ABC):
    @abstractmethod
    async def execute(self, input_dto: DeleteCustomerInput) -> DeleteCustomerOutput: ...


class ListCustomers(ABC):
    @abstractmethod
    async def execute(self, input_dto: ListCustomersInput) -> ListCustomersOutput: ...


class AddTicket(ABC):
    @abstractmethod
    async def execute(self, input_dto: AddTicketInput) -> AddTicketOutput: ...


class GetTicket(ABC):
    @abstractmethod
    async def execute(self, input_dto: GetTicketInput) -> GetTicketOutput: ...


class UpdateTicket(ABC):
    @abstractmethod
    async def execute(self, input_dto: UpdateTicketInput) -> UpdateTicketOutput: ...


class DeleteTicket(ABC):
    @abstractmethod
    async def execute(self, input_dto: DeleteTicketInput) -> DeleteTicketOutput: ...


class ListTickets(ABC):
    @abstractmethod
    async def execute(self, input_dto: ListTicketsInput) -> ListTicketsOutput: ...


class AddSatisfactionRating(ABC):
    @abstractmethod
    async def execute(self, input_dto: AddSatisfactionRatingInput) -> AddSatisfactionRatingOutput: ...


class GetSatisfactionRating(ABC):
    @abstractmethod
    async def execute(self, input_dto: GetSatisfactionRatingInput) -> GetSatisfactionRatingOutput: ...


class UpdateSatisfactionRating(ABC):
    @abstractmethod
    async def execute(self, input_dto: UpdateSatisfactionRatingInput) -> UpdateSatisfactionRatingOutput: ...


class DeleteSatisfactionRating(ABC):
    @abstractmethod
    async def execute(self, input_dto: DeleteSatisfactionRatingInput) -> DeleteSatisfactionRatingOutput: ...


class ListSatisfactionRatings(ABC):
    @abstractmethod
    async def execute(self, input_dto: ListSatisfactionRatingsInput) -> ListSatisfactionRatingsOutput: ...


class AddTag(ABC):
    @abstractmethod
    async def execute(self, input_dto: AddTagInput) -> AddTagOutput: ...


class GetTag(ABC):
    @abstractmethod
    async def execute(self, input_dto: GetTagInput) -> GetTagOutput: ...


class UpdateTag(ABC):
    @abstractmethod
    async def execute(self, input_dto: UpdateTagInput) -> UpdateTagOutput: ...


class DeleteTag(ABC):
    @abstractmethod
    async def execute(self, input_dto: DeleteTagInput) -> DeleteTagOutput: ...


class ListTags(ABC):
    @abstractmethod
    async def execute(self, input_dto: ListTagsInput) -> ListTagsOutput: ...


class AddTicketTag(ABC):
    @abstractmethod
    async def execute(self, input_dto: AddTicketTagInput) -> AddTicketTagOutput: ...


class DeleteTicketTag(ABC):
    @abstractmethod
    async def execute(self, input_dto: DeleteTicketTagInput) -> DeleteTicketTagOutput: ...


class ListTicketsByTags(ABC):
    @abstractmethod
    async def execute(self, input_dto: ListTicketsByTagsInput) -> ListTicketsByTagsOutput: ...
