from src.infra.database.repositories.tickets.analytics_customers import (
    TicketCustomerAnalyticsMixin,
)
from src.infra.database.repositories.tickets.analytics_dashboard import (
    TicketDashboardAnalyticsMixin,
)


class TicketAnalyticsMixin(
    TicketDashboardAnalyticsMixin,
    TicketCustomerAnalyticsMixin,
):
    pass
