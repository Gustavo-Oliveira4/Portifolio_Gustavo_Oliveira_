"""Cenário de demonstração: preenche o salão com mesas ocupadas, reservas e pedidos.

Uso:  python -m core.demo     (ou automaticamente no modo mongomock://)
"""
import random
from datetime import timedelta

from core.services import Servico
from core.utils import agora

def gerar_cpf(rnd: random.Random) -> str:
    """Gera um CPF fictício com dígitos verificadores válidos."""
    base = [rnd.randint(0, 9) for _ in range(9)]
    for tamanho in (9, 10):
        soma = sum(d * (tamanho + 1 - i) for i, d in enumerate(base))
        base.append((soma * 10 % 11) % 10)
    return "".join(map(str, base))



CPF_EXEMPLO = "52998224725"  # use este CPF na visão Cliente para ver a mesa em andamento
NOMES = ["Maria Souza", "João Lima", "Ana Ribeiro", "Pedro Alves", "Luiza Rocha",
         "Carlos Melo", "Fernanda Dias", "Rafael Nunes", "Juliana Costa", "Marcos Pinto"]


def _recuar(svc: Servico, mesa: int, minutos: int):
    """Ajusta horários para simular clientes que chegaram há algum tempo."""
    m = svc.mesa(mesa)
    antes = agora() - timedelta(minutes=minutos)
    svc.db.mesas.update_one({"numero": mesa}, {"$set": {"status_desde": antes}})
    svc.db.atendimentos.update_one({"_id": m["atendimento_id"]}, {"$set": {"inicio": antes}})


def gerar_cenario(svc: Servico, semente: int = 7) -> None:
    if svc.db.atendimentos.count_documents({}):
        return
    rnd = random.Random(semente)
    garcom = lambda n: svc.mesa(n)["garcom"]  # noqa: E731

    ocupadas = rnd.sample(range(1, 101), 42)
    for i, numero in enumerate(ocupadas):
        cap = svc.mesa(numero)["capacidade"]
        cpf = (CPF_EXEMPLO if i == 0 else gerar_cpf(rnd)) if i < len(NOMES) else None
        nome = NOMES[i] if i < len(NOMES) else None
        svc.ocupar_sem_reserva(numero, rnd.randint(1, cap), garcom(numero), cpf=cpf, nome=nome)
        _recuar(svc, numero, rnd.randint(2, 70))
        if i % 6 == 5:
            continue                                   # permanece "não atendida"
        itens = [{"codigo": rnd.randint(1, 13), "quantidade": rnd.randint(1, 2)},
                 {"codigo": rnd.choice([14, 15, 16]), "quantidade": rnd.randint(1, 3)}]
        if i % 4 == 0:
            itens[0]["observacao"] = rnd.choice(["sem cebola", "ao ponto", "sem glúten"])
        pid = svc.lancar_pedido(numero, itens, garcom(numero))
        # simula pedidos lançados há alguns minutos
        recuo = timedelta(minutes=rnd.randint(1, 12))
        p = svc.pedido(pid)
        svc.db.pedidos.update_one({"_id": pid}, {"$set": {
            "lancado_em": p["lancado_em"] - recuo, "previsao_inicial": p["previsao_inicial"] - recuo,
            "previsao_entrega": p["previsao_entrega"] - recuo}})
    svc.db.notificacoes.update_many({"tipo": "entrada", "ref": {"$in": [
        svc.mesa(n)["atendimento_id"] for n in ocupadas if svc.mesa(n)["status"] != "ocupada_nao_atendida"]}},
        {"$set": {"confirmada": True, "confirmada_por": "demo", "confirmada_em": agora()}})

    svc.recalcular_fila()
    fila = svc.fila_cozinha()
    for p in fila[:8]:
        svc.iniciar_preparo(p["_id"], f"C0{rnd.randint(1, 5)}")
    for p in fila[:3]:
        svc.marcar_pronto(p["_id"], p.get("chefe") or "C01")

    livres = [m["numero"] for m in svc.listar_mesas() if m["status"] == "livre" and m["reservavel"]]
    base = agora().replace(second=0, microsecond=0)
    for k, numero in enumerate(rnd.sample(livres, min(6, len(livres)))):
        cpf = gerar_cpf(rnd)
        try:
            svc.criar_reserva(cpf, f"Cliente reserva {k + 1}", "11988887777",
                              base + timedelta(minutes=20 + 25 * k), 2, origem="manual",
                              usuario="G01", mesa_numero=numero)
        except Exception:  # noqa: BLE001 – cenário ilustrativo
            pass


if __name__ == "__main__":
    from core.database import obter_db
    from core.seed import popular
    db = obter_db()
    popular(db)
    gerar_cenario(Servico(db))
    print("Cenário de demonstração criado.")
