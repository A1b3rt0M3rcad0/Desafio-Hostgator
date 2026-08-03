from uuid import UUID

import pytest

from src.application.contracts.use_cases import GetUser
from src.application.dtos.auth import AuthenticatedUser, UserView
from src.application.dtos.get_user import GetUserInput, GetUserOutput
from src.presentation.http.controllers.auth_controller import CurrentUserController
from src.presentation.http.schemas.request import Request


pytestmark = pytest.mark.unit


class StubGetUser(GetUser):
    def __init__(self, user: UserView | None) -> None:
        self._output = GetUserOutput(user=user)
        self.received_input: GetUserInput | None = None

    async def execute(self, input_dto: GetUserInput) -> GetUserOutput:
        self.received_input = input_dto
        return self._output


@pytest.mark.asyncio
async def test_current_user_returns_email_and_session_id() -> None:
    user_id = UUID("019fc9b7-2d79-75fb-9605-4e50d67d5c0c")
    session_id = UUID("019fc9c0-9cd6-72ab-8c16-a7d25603879a")
    use_case = StubGetUser(
        UserView(
            id=user_id,
            email="admin@example.com",
        ),
    )
    controller = CurrentUserController(use_case)

    response = await controller.handle(
        Request(
            user=AuthenticatedUser(
                id=user_id,
                session_id=session_id,
            ),
        ),
    )

    assert response.status_code == 200
    assert response.body["id"] == user_id
    assert response.body["email"] == "admin@example.com"
    assert response.body["session_id"] == session_id
    assert response.headers == {
        "Cache-Control": "no-store",
        "Pragma": "no-cache",
    }
    assert use_case.received_input == GetUserInput(user_id=user_id)


@pytest.mark.asyncio
async def test_current_user_rejects_request_without_authenticated_user() -> None:
    use_case = StubGetUser(None)
    controller = CurrentUserController(use_case)

    response = await controller.handle(Request())

    assert response.status_code == 401
    assert use_case.received_input is None


@pytest.mark.asyncio
async def test_current_user_rejects_session_for_missing_user() -> None:
    user_id = UUID("019fc9b7-2d79-75fb-9605-4e50d67d5c0c")
    session_id = UUID("019fc9c0-9cd6-72ab-8c16-a7d25603879a")
    use_case = StubGetUser(None)
    controller = CurrentUserController(use_case)

    response = await controller.handle(
        Request(
            user=AuthenticatedUser(
                id=user_id,
                session_id=session_id,
            ),
        ),
    )

    assert response.status_code == 401
    assert use_case.received_input == GetUserInput(user_id=user_id)
