"""Load real future product factory, never substitute a route stub."""
import importlib
import socket
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from doubles import FakeERP, FakeLLM, MemoryRepository

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def deny(*args, **kwargs):
        raise AssertionError("Network forbidden in offline acceptance")
    monkeypatch.setattr(socket.socket, "connect", deny)
    monkeypatch.setattr(socket, "create_connection", deny)
    monkeypatch.setattr(socket, "getaddrinfo", deny)


@pytest.fixture
def rig():
    try:
        module = importlib.import_module("partpilot.app")
    except ModuleNotFoundError as exc:
        if exc.name not in {"partpilot", "partpilot.app"}:
            raise
        pytest.fail("MISSING_IMPLEMENTATION: src/partpilot/app.py create_app required", pytrace=False)
    repo, erp, llm = MemoryRepository(), FakeERP(), FakeLLM()
    app = module.create_app(repository=repo, erp=erp, llm=llm)
    assert isinstance(app, FastAPI), "Real FastAPI app required"
    assert callable(app.state.workflow.run_once), "Finite real worker step required"
    with TestClient(app, base_url="http://127.0.0.1", client=("127.0.0.1", 55000)) as client:
        yield SimpleNamespace(client=client, repo=repo, erp=erp, llm=llm,
                              app=app, step=app.state.workflow.run_once)
