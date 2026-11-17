"""Carga inicial: 100 mesas, 30 garçons, 5 chefes e cardápio.

Uso:  python -m core.seed            (cria apenas o que ainda não existe)
      python -m core.seed --reset    (apaga tudo e recria)
"""
import sys

from core import config
from core.utils import agora, gerar_hash_senha

SENHA_PADRAO_GARCOM = "garcom123"
SENHA_PADRAO_CHEFE = "chef123"

NOMES = ["Ana", "Bruno", "Carla", "Diego", "Elisa", "Fábio", "Gabriela", "Henrique",
         "Isabela", "João", "Karina", "Lucas", "Mariana", "Nicolas", "Olívia",
         "Paulo", "Queila", "Rafael", "Sofia", "Tiago", "Úrsula", "Vitor", "Wesley",
         "Xavier", "Yasmin", "Zeca", "Bianca", "Caio", "Débora", "Eduardo"]
CHEFES = ["Chef Antônio", "Chef Beatriz", "Chef Cláudio", "Chef Denise", "Chef Érico"]

CARDAPIO = [
    # nome, categoria, preço, tempo de preparo (min)
    ("Bruschetta de tomate", "Entradas", 32.0, 8),
    ("Carpaccio", "Entradas", 45.0, 10),
    ("Bolinho de bacalhau (6 un.)", "Entradas", 39.0, 12),
    ("Salada Caesar", "Entradas", 36.0, 7),
    ("Risoto de cogumelos", "Pratos principais", 78.0, 25),
    ("Filé ao molho madeira", "Pratos principais", 89.0, 22),
    ("Salmão grelhado", "Pratos principais", 95.0, 20),
    ("Parmegiana de frango", "Pratos principais", 69.0, 18),
    ("Massa à carbonara", "Pratos principais", 64.0, 15),
    ("Picanha na chapa (2 pessoas)", "Pratos principais", 159.0, 28),
    ("Petit gâteau", "Sobremesas", 32.0, 12),
    ("Pudim de leite", "Sobremesas", 22.0, 3),
    ("Tiramisù", "Sobremesas", 29.0, 4),
    ("Refrigerante lata", "Bebidas", 8.0, 1),
    ("Suco natural", "Bebidas", 14.0, 4),
    ("Água mineral", "Bebidas", 6.0, 1),
]

_CAPACIDADES = [2, 4, 4, 6, 2, 4, 8, 4, 2, 6]


def _setores(primeira: int, quantidade: int, garcons: list[str]) -> dict[int, str]:
    """Divide as mesas de um pavimento em blocos contíguos, um por garçom (RN-09)."""
    mapa, n = {}, len(garcons)
    for i in range(quantidade):
        mapa[primeira + i] = garcons[i * n // quantidade]
    return mapa


def popular(db, reset: bool = False) -> dict:
    if reset:
        for nome in db.list_collection_names():
            db[nome].delete_many({})

    criado = {"mesas": 0, "funcionarios": 0, "cardapio": 0}
    momento = agora()

    if db.funcionarios.count_documents({}) == 0:
        hash_g = gerar_hash_senha(SENHA_PADRAO_GARCOM)
        hash_c = gerar_hash_senha(SENHA_PADRAO_CHEFE)
        docs = []
        total_g = config.GARCONS_TERREO + config.GARCONS_MEZANINO
        for i in range(total_g):
            docs.append({
                "matricula": f"G{i + 1:02d}", "nome": NOMES[i % len(NOMES)],
                "perfil": "garcom", "senha": hash_g, "ativo": True,
                "pavimento": "terreo" if i < config.GARCONS_TERREO else "mezanino",
            })
        for i in range(config.TOTAL_CHEFES):
            docs.append({"matricula": f"C{i + 1:02d}", "nome": CHEFES[i % len(CHEFES)],
                         "perfil": "cozinha", "senha": hash_c, "ativo": True,
                         "pavimento": None})
        db.funcionarios.insert_many(docs)
        criado["funcionarios"] = len(docs)

    if db.mesas.count_documents({}) == 0:
        g_terreo = [f"G{i + 1:02d}" for i in range(config.GARCONS_TERREO)]
        g_mez = [f"G{config.GARCONS_TERREO + i + 1:02d}" for i in range(config.GARCONS_MEZANINO)]
        setor = _setores(1, config.MESAS_TERREO, g_terreo)
        setor.update(_setores(config.MESAS_TERREO + 1, config.MESAS_MEZANINO, g_mez))
        passo = max(1, round(100 / config.PERCENTUAL_SEM_RESERVA)) if config.PERCENTUAL_SEM_RESERVA else 0
        docs = []
        for numero in range(1, config.MESAS_TERREO + config.MESAS_MEZANINO + 1):
            docs.append({
                "numero": numero,
                "pavimento": "terreo" if numero <= config.MESAS_TERREO else "mezanino",
                "capacidade": _CAPACIDADES[(numero - 1) % len(_CAPACIDADES)],
                # RN-07: parte das mesas fica fora da reserva antecipada
                "reservavel": not (passo and numero % passo == 0),
                "garcom": setor[numero],
                "status": "livre", "status_desde": momento, "atendimento_id": None,
            })
        db.mesas.insert_many(docs)
        criado["mesas"] = len(docs)

    if db.cardapio.count_documents({}) == 0:
        db.cardapio.insert_many([
            {"codigo": i + 1, "nome": n, "categoria": c, "preco": p,
             "tempo_preparo_min": t, "ativo": True}
            for i, (n, c, p, t) in enumerate(CARDAPIO)])
        criado["cardapio"] = len(CARDAPIO)
    return criado


if __name__ == "__main__":
    from core.database import obter_db
    resultado = popular(obter_db(), reset="--reset" in sys.argv)
    print("Carga concluída:", resultado)
