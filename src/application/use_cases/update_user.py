from src.application.contracts.repositories import AuthSessionRepository, UserRepository
from src.application.contracts.security import PasswordHasher
from src.application.contracts.use_cases import UpdateUser as UpdateUserContract
from src.application.dtos.auth import UserView
from src.application.dtos.update_user import UpdateUserInput, UpdateUserOutput


class UpdateUser(UpdateUserContract):
    def __init__(
        self,
        repository: UserRepository,
        password_hasher: PasswordHasher,
        session_repository: AuthSessionRepository,
    ) -> None:
        self._repository = repository
        self._password_hasher = password_hasher
        self._session_repository = session_repository

    async def execute(self, input_dto: UpdateUserInput) -> UpdateUserOutput:
        entity = await self._repository.get(input_dto.user_id)
        if not entity:
            raise ValueError(f"User {input_dto.user_id} not found")

        if input_dto.email is not None:
            entity.email = input_dto.email
        password_changed = input_dto.password is not None
        if input_dto.password is not None:
            entity.password_hash = await self._password_hasher.hash(
                input_dto.password,
            )

        await self._repository.update(entity)
        if password_changed and entity.id is not None:
            await self._session_repository.revoke_all_by_user(entity.id)
        return UpdateUserOutput(user=UserView.model_validate(entity))
