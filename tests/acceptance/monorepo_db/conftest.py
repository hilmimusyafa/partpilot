"""Collection never reads credentials or connects to PostgreSQL."""
import pytest

@pytest.fixture
def db(request):
    connection = getattr(request.config, "monorepo_connection", None)
    if connection is None:
        pytest.fail("Use run_checks.py runtime for dedicated rollback-only SQL", pytrace=False)
    connection.execute("SAVEPOINT acceptance_case")
    try:
        yield connection
    finally:
        connection.execute("ROLLBACK TO SAVEPOINT acceptance_case")
        connection.execute("RELEASE SAVEPOINT acceptance_case")

def pytest_collection_modifyitems(items):
    for item in items:
        if any(item.get_closest_marker(m) for m in ("skip", "skipif", "xfail")):
            raise pytest.UsageError("No skipped or expected-failing acceptance cases")
