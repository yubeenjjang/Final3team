from pathlib import Path

from api.providers.route_base import RouteQuery

FIXTURES = Path(__file__).parent / "fixtures"
TEST_KEY = "TEST_KEY_DO_NOT_USE"
QUERY = RouteQuery((37.5668, 126.9905), (37.5456, 126.9844))
