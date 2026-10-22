"""Transport boundary: persist event before calling send; retries reuse its ID.

A future real adapter must deduplicate by event_id or report uncertain delivery.
It must never create a new logical counteroffer when network delivery is uncertain.
"""
from typing import Protocol
from .models import VendorResponse

class VendorTransport(Protocol):
    def send(self, event: dict) -> VendorResponse: ...
