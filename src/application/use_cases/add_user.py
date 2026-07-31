from src.application.contracts.repositories import UserRepository
from src.application.contracts.security import PasswordHasher
from src.application.contracts.use_cases import AddUser as AddUserContract
from src.application.dtos.add_user import AddUserInput, AddUserOutput
from src.application.dtos.auth import UserView
from src.domain.entities import UserEntity


class AddUser(AddUserContract):
    def __init__(
        self,
        repository: UserRepository,
        password_hasher: PasswordHasher,
    ) -> None:
        self._repository = repository
        self._password_hasher = password_hasher

    async def execute(self, input_dto: AddUserInput) -> AddUserOutput:
        entity = UserEntity(
            email=input_dto.email,
            password_hash=await self._password_hasher.hash(input_dto.password),
        )
        await self._repository.add(entity)
        return AddUserOutput(user=UserView.model_validate(entity))
