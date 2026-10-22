"""Offline TEST DOUBLES only; no product routes or workflow decisions."""
from contextlib import contextmanager
from copy import deepcopy


class MemoryRepository:
    """Transactional KV port, NOT PostgreSQL durability/security/race evidence.

    transaction() yields a detached dict of namespaces; commit swaps it atomically.
    Domain rules belong to product. Sequential offline behavior only.
    """
    def __init__(self):
        self.data = {name: {} for name in ("work_orders", "jobs", "idempotency", "answers")}
        self.fail_commit = False
        self.commits = 0

    @contextmanager
    def transaction(self):
        pending = deepcopy(self.data)
        yield pending
        if self.fail_commit:
            raise OSError("SYN-storage-unavailable")
        self.data = deepcopy(pending)
        self.commits += 1

    def snapshot(self):
        return deepcopy(self.data)


class FakeERP:
    """One synthetic org, one site, five warehouses. No customer catalog."""
    org_id = "00000000-0000-0000-0000-000000000001"
    sites = {"SYN-SITE-A"}
    assets = {"SYN-ASSET-001": "SYN-SITE-A"}
    warehouses = {f"SYN-WH-{letter}": "SYN-SITE-A" for letter in "ABCDE"}

    def validate_context(self, *, asset_id, site_id, target_warehouse_id):
        return (site_id in self.sites and self.assets.get(asset_id) == site_id
                and self.warehouses.get(target_warehouse_id) == site_id)

    def lookup_exact(self, *, facts):
        return None


class FakeLLM:
    """Scripted extraction, not business state/approval/job output.

    extract consumes one structured JSON entry or raises one scripted exception.
    Product must validate it. No network fallback.
    """
    def __init__(self):
        self.script = []
        self.calls = []

    def extract(self, *, text, answers):
        self.calls.append({"text": text, "answers": deepcopy(answers)})
        assert self.script, "Unplanned LLM call"
        result = self.script.pop(0)
        if isinstance(result, Exception):
            raise result
        return deepcopy(result)


def extraction(*, missing=(), gap=False, conflicts=()):
    return {"facts": [], "missing_attributes": list(missing),
            "knowledge_gap": gap, "conflicts": list(conflicts)}
