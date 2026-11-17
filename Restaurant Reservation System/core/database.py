"""Conexão com o MongoDB e criação dos índices."""
from functools import lru_cache

from pymongo import ASCENDING, DESCENDING

from core import config

COLECOES = ("mesas", "funcionarios", "reservas", "atendimentos",
            "pedidos", "cardapio", "notificacoes", "eventos")


def criar_cliente(uri: str | None = None):
    uri = uri or config.MONGO_URI
    if uri.startswith("mongomock://"):
        import mongomock  # modo demonstração (dados em memória)
        return mongomock.MongoClient()
    from pymongo import MongoClient
    cliente = MongoClient(uri, serverSelectionTimeoutMS=3000)
    cliente.admin.command("ping")  # falha cedo se o servidor não estiver ativo
    return cliente


@lru_cache(maxsize=1)
def obter_db(uri: str | None = None, nome: str | None = None):
    db = criar_cliente(uri)[nome or config.MONGO_DB]
    criar_indices(db)
    return db


def criar_indices(db) -> None:
    db.mesas.create_index([("numero", ASCENDING)], unique=True)
    db.mesas.create_index([("pavimento", ASCENDING), ("status", ASCENDING)])
    db.funcionarios.create_index([("matricula", ASCENDING)], unique=True)
    db.reservas.create_index([("cpf", ASCENDING), ("status", ASCENDING)])
    db.reservas.create_index([("mesa", ASCENDING), ("data_hora", ASCENDING)])
    db.atendimentos.create_index([("mesa", ASCENDING), ("fim", ASCENDING)])
    db.pedidos.create_index([("status", ASCENDING), ("lancado_em", ASCENDING)])
    db.pedidos.create_index([("atendimento_id", ASCENDING)])
    db.notificacoes.create_index([("destinatarios", ASCENDING), ("confirmada", ASCENDING)])
    db.eventos.create_index([("em", DESCENDING)])
