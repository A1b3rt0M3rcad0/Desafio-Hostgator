from typing import Any
from uuid import UUID

from sqlalchemy import and_, func, or_, select

from src.application.contracts.repositories import CustomerRepository
from src.application.dtos.analytics import CustomerFilterOption
from src.application.dtos.cursor_page import CursorPage
from src.application.dtos.list_customers import CustomerListItem, ListCustomersInput
from src.application.dtos.ticket_ingestion import CustomerSourceResult
from src.domain.entities import CustomerEntity
from src.infra.database.models import Customer
from src.infra.database.repositories.common import (
    SqlAlchemyRepositoryBase,
    decode_json_cursor,
    decode_uuid_cursor,
    encode_json_cursor,
    encode_uuid_cursor,
    escape_like,
)


class SqlAlchemyCustomerRepository(SqlAlchemyRepositoryBase, CustomerRepository):
    async def add(self, entity: CustomerEntity) -> None:
        orm = Customer(**entity.model_dump(exclude={"id", "created_at", "updated_at"}))
        self._session.add(orm)
        await self._session.flush()

    async def get(self, entity_id: UUID) -> CustomerEntity | None:
        orm = await self._session.get(Customer, entity_id)
        return CustomerEntity.model_validate(orm) if orm else None

    async def update(self, entity: CustomerEntity) -> None:
        orm = await self._session.get(Customer, entity.id)
        if not orm:
            return
        for key, value in entity.model_dump(
            exclude={"id", "created_at", "updated_at"}
        ).items():
            setattr(orm, key, value)
        await self._session.flush()

    async def delete(self, entity_id: UUID) -> None:
        orm = await self._session.get(Customer, entity_id)
        if not orm:
            return
        await self._session.delete(orm)
        await self._session.flush()

    async def page(
        self,
        cursor: str | None,
        page_size: int = 20,
    ) -> CursorPage[CustomerEntity]:
        stmt = select(Customer).order_by(Customer.id).limit(page_size + 1)
        if cursor:
            stmt = stmt.where(Customer.id > decode_uuid_cursor(cursor))
        rows = list((await self._session.execute(stmt)).scalars().all())
        entities = [CustomerEntity.model_validate(row) for row in rows[:page_size]]
        has_next = len(rows) > page_size
        return CursorPage(
            items=entities,
            next_cursor=(
                encode_uuid_cursor(entities[-1].id)
                if has_next and entities and entities[-1].id is not None
                else None
            ),
            previous_cursor=None,
            has_next=has_next,
            has_previous=cursor is not None,
        )

    async def page_list(
        self,
        input_dto: ListCustomersInput,
    ) -> CursorPage[CustomerListItem]:
        predicates: list[Any] = []
        if input_dto.search:
            search = input_dto.search
            escaped = escape_like(search)
            conditions: list[Any] = [
                Customer.requester_name.like(f"{escaped}%", escape="\\"),
                Customer.requester_email.like(f"{escaped}%", escape="\\"),
            ]
            if search.isdigit():
                conditions.insert(0, Customer.external_requester_id == int(search))
            predicates.append(or_(*conditions))

        if input_dto.cursor:
            payload = decode_json_cursor(input_dto.cursor)
            cursor_name = payload.get("requester_name")
            cursor_id = payload.get("id")
            if cursor_name is None or cursor_id is None:
                raise ValueError("Invalid customer cursor")
            parsed_id = UUID(cursor_id)
            predicates.append(
                or_(
                    Customer.requester_name > cursor_name,
                    and_(
                        Customer.requester_name == cursor_name,
                        Customer.id > parsed_id,
                    ),
                )
            )

        rows = (
            await self._session.execute(
                select(
                    Customer.id,
                    Customer.external_requester_id,
                    Customer.requester_name,
                    Customer.requester_email,
                    Customer.created_at,
                )
                .where(*predicates)
                .order_by(Customer.requester_name.asc(), Customer.id.asc())
                .limit(input_dto.page_size + 1)
            )
        ).mappings().all()
        items = [
            CustomerListItem(
                id=row["id"],
                external_requester_id=row["external_requester_id"],
                requester_name=row["requester_name"],
                requester_email=row["requester_email"],
                created_at=row["created_at"],
            )
            for row in rows[: input_dto.page_size]
        ]
        has_next = len(rows) > input_dto.page_size
        return CursorPage(
            items=items,
            next_cursor=(
                encode_json_cursor(
                    {
                        "requester_name": items[-1].requester_name,
                        "id": str(items[-1].id),
                    }
                )
                if has_next and items
                else None
            ),
            previous_cursor=None,
            has_next=has_next,
            has_previous=input_dto.cursor is not None,
        )

    async def upsert_from_source(
        self,
        *,
        external_requester_id: int,
        requester_name: str,
        requester_email: str,
    ) -> CustomerSourceResult:
        email = requester_email.strip().lower()
        rows = (
            await self._session.execute(
                select(Customer)
                .where(
                    or_(
                        func.lower(Customer.requester_email) == email,
                        Customer.external_requester_id == external_requester_id,
                    )
                )
                .with_for_update()
            )
        ).scalars().all()

        email_match = next(
            (
                customer
                for customer in rows
                if customer.requester_email.strip().lower() == email
            ),
            None,
        )
        id_match = next(
            (
                customer
                for customer in rows
                if customer.external_requester_id == external_requester_id
            ),
            None,
        )
        if (
            email_match is not None
            and id_match is not None
            and email_match.id != id_match.id
        ):
            raise ValueError(
                "Requester email and external ID belong to different customers"
            )

        customer = email_match or id_match
        created = False
        if customer is None:
            customer = Customer(
                external_requester_id=external_requester_id,
                requester_name=requester_name,
                requester_email=email,
            )
            self._session.add(customer)
            created = True
        else:
            if (
                customer.external_requester_id != external_requester_id
                or customer.requester_email.strip().lower() != email
            ):
                raise ValueError(
                    "Requester identity conflicts with an existing customer"
                )
            if customer.requester_name != requester_name:
                customer.requester_name = requester_name

        await self._session.flush()
        return CustomerSourceResult(
            customer=CustomerEntity.model_validate(customer),
            created=created,
        )

    async def list_filter_options(self) -> list[CustomerFilterOption]:
        rows = (
            await self._session.execute(
                select(
                    Customer.id,
                    Customer.requester_name,
                    Customer.requester_email,
                ).order_by(Customer.requester_name.asc(), Customer.requester_email.asc())
            )
        ).all()
        return [
            CustomerFilterOption(
                id=customer_id,
                requester_name=requester_name,
                requester_email=requester_email,
            )
            for customer_id, requester_name, requester_email in rows
        ]
