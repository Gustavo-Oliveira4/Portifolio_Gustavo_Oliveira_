import sys
from datetime import datetime, timedelta
from pathlib import Path

import mongomock
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core import services as services_mod  # noqa: E402
from core.database import criar_indices  # noqa: E402
from core.seed import popular  # noqa: E402
from core.services import Servico  # noqa: E402


class Relogio:
    def __init__(self, inicio: datetime):
        self.atual = inicio

    def __call__(self):
        return self.atual

    def avancar(self, minutos: float):
        self.atual += timedelta(minutes=minutos)


@pytest.fixture
def relogio(monkeypatch):
    r = Relogio(datetime(2026, 11, 20, 12, 0))  # sexta-feira, 12h
    monkeypatch.setattr(services_mod, "agora", r)
    monkeypatch.setattr("core.utils.agora", r)
    monkeypatch.setattr("core.seed.agora", r)
    return r


@pytest.fixture(scope="session")
def _base():
    db = mongomock.MongoClient()["base"]
    popular(db)
    return {n: list(db[n].find()) for n in db.list_collection_names()}


@pytest.fixture
def svc(relogio, _base):
    db = mongomock.MongoClient()["teste"]
    criar_indices(db)
    for nome, docs in _base.items():
        if docs:
            if nome == "mesas":
                docs = [{**d, "status_desde": relogio()} for d in docs]
            db[nome].insert_many([dict(d) for d in docs])
    return Servico(db)


CPF_A = "529.982.247-25"
CPF_B = "111.444.777-35"
