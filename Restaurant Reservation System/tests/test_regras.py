from datetime import timedelta

import pytest

from core import config
from core.services import (ATENDIDA, EM_LIBERACAO, LIVRE, NAO_ATENDIDA, RESERVADA,
                           RegraNegocioErro)
from core.utils import mascarar_cpf, validar_cpf
from tests.conftest import CPF_A, CPF_B

G_TERREO = "G01"


def _reserva(svc, relogio, cpf=CPF_A, minutos=120, pessoas=4, **kw):
    return svc.criar_reserva(cpf, "Maria", "(11) 99999-0000",
                             relogio() + timedelta(minutes=minutos), pessoas, **kw)


# ----------------------------------------------------------------- Carga inicial
def test_carga_inicial(svc):
    assert svc.db.mesas.count_documents({"pavimento": "terreo"}) == 70
    assert svc.db.mesas.count_documents({"pavimento": "mezanino"}) == 30
    assert svc.db.funcionarios.count_documents({"perfil": "garcom"}) == 30
    assert svc.db.funcionarios.count_documents({"perfil": "cozinha"}) == 5
    assert svc.db.mesas.count_documents({"reservavel": False}) == 20          # RN-07 (20%)
    # RN-09: garçom do térreo só tem mesas do térreo
    for g in svc.db.funcionarios.find({"perfil": "garcom"}):
        pavs = {m["pavimento"] for m in svc.db.mesas.find({"garcom": g["matricula"]})}
        assert pavs == {g["pavimento"]}
        assert 3 <= svc.db.mesas.count_documents({"garcom": g["matricula"]}) <= 4


def test_autenticacao(svc):
    assert svc.autenticar("g01", "garcom123")["perfil"] == "garcom"
    assert svc.autenticar("C01", "chef123")["perfil"] == "cozinha"
    assert svc.autenticar("G01", "errada") is None
    assert "senha" not in svc.autenticar("G01", "garcom123")


# ----------------------------------------------------------------- CPF
def test_cpf():
    assert validar_cpf(CPF_A) and validar_cpf(CPF_B)
    assert not validar_cpf("123.456.789-00") and not validar_cpf("111.111.111-11")
    assert mascarar_cpf(CPF_A) == "•••.982.•••-••"


# ----------------------------------------------------------------- Reservas
def test_reserva_basica_e_rn04(svc, relogio):
    r = _reserva(svc, relogio, pessoas=3)
    mesa = svc.mesa(r["mesa"])
    assert mesa["capacidade"] == 4 and mesa["reservavel"]          # menor ociosidade
    assert r["status"] == "ativa"


def test_rn01_cpf_invalido(svc, relogio):
    with pytest.raises(RegraNegocioErro, match="CPF"):
        _reserva(svc, relogio, cpf="123.456.789-00")


def test_rn02_uma_por_turno(svc, relogio):
    _reserva(svc, relogio, minutos=120)                 # 14h almoço
    with pytest.raises(RegraNegocioErro, match="turno"):
        _reserva(svc, relogio, minutos=180)             # 15h almoço
    assert _reserva(svc, relogio, minutos=420)          # 19h jantar → permitido


def test_rn03_sem_sobreposicao(svc, relogio):
    alvo = _reserva(svc, relogio, pessoas=8, ambiente="mezanino")["mesa"]
    mesas_8_mez = [m["numero"] for m in svc.db.mesas.find(
        {"capacidade": {"$gte": 8}, "pavimento": "mezanino", "reservavel": True})]
    usados = {alvo}
    cpfs = ["39053344705", "15350946056", "74682489070", "86288366757"]
    for cpf in cpfs[:len(mesas_8_mez) - 1]:
        usados.add(_reserva(svc, relogio, cpf=cpf, pessoas=8, ambiente="mezanino")["mesa"])
    assert usados == set(mesas_8_mez)                   # cada uma em mesa diferente
    with pytest.raises(RegraNegocioErro, match="Não há mesas"):
        _reserva(svc, relogio, cpf=cpfs[-1], pessoas=8, ambiente="mezanino")


def test_rn05_antecedencia(svc, relogio):
    with pytest.raises(RegraNegocioErro, match="antecedência"):
        _reserva(svc, relogio, minutos=30)
    r = _reserva(svc, relogio, minutos=90)
    relogio.avancar(40)                                  # faltam 50 min
    with pytest.raises(RegraNegocioErro, match="até 60"):
        svc.cancelar_reserva(r["_id"], cpf=CPF_A)


def test_alterar_e_cancelar(svc, relogio):
    r = _reserva(svc, relogio, minutos=180)
    nova = svc.alterar_reserva(r["_id"], CPF_A, relogio() + timedelta(minutes=240), 6)
    assert svc.mesa(nova["mesa"])["capacidade"] >= 6
    with pytest.raises(RegraNegocioErro, match="não pertence"):
        svc.cancelar_reserva(r["_id"], cpf=CPF_B)
    svc.cancelar_reserva(r["_id"], cpf=CPF_A)
    assert svc.reserva(r["_id"])["status"] == "cancelada"


def test_rn06_expiracao_e_estado_reservada(svc, relogio):
    r = _reserva(svc, relogio, minutos=90)
    relogio.avancar(40)                                  # a 50 min → aparece Reservada
    m = next(m for m in svc.listar_mesas() if m["numero"] == r["mesa"])
    assert m["status_exibicao"] == RESERVADA
    relogio.avancar(50 + config.TOLERANCIA_ATRASO_MIN + 1)
    assert svc.processar_rotinas()["reservas_expiradas"] == 1
    assert svc.reserva(r["_id"])["status"] == "expirada"
    assert svc.notificacoes(svc.mesa(r["mesa"])["garcom"])[0]["tipo"] == "reserva_expirada"


def test_rn07_cliente_nao_reserva_mesa_cota(svc, relogio):
    for _ in range(3):
        r = _reserva(svc, relogio, cpf=CPF_A, minutos=120)
        assert svc.mesa(r["mesa"])["reservavel"]
        svc.cancelar_reserva(r["_id"], cpf=CPF_A)


# ----------------------------------------------------------------- Ocupação e atendimento
def test_fluxo_checkin_atendimento_liberacao(svc, relogio):
    r = _reserva(svc, relogio, minutos=70)
    relogio.avancar(15)
    garcom = svc.mesa(r["mesa"])["garcom"]
    svc.fazer_checkin(r["_id"], garcom)
    assert svc.mesa(r["mesa"])["status"] == NAO_ATENDIDA
    assert svc.notificacoes(garcom)[0]["tipo"] == "entrada"           # RU-GAR-03
    relogio.avancar(config.ALERTA_NAO_ATENDIDA_MIN + 1)
    m = next(m for m in svc.listar_mesas() if m["numero"] == r["mesa"])
    assert m["alerta"]                                                # RN-12
    svc.registrar_atendimento(r["mesa"], garcom)
    at = svc.atendimento_do_cliente(CPF_A)
    assert at["primeiro_atendimento_em"] is not None                  # RN-11
    assert svc.mesa(r["mesa"])["status"] == ATENDIDA
    assert svc.notificacoes(garcom) == []                             # confirmada
    svc.liberar_mesa(r["mesa"], garcom)
    assert svc.mesa(r["mesa"])["status"] == EM_LIBERACAO               # RN-13
    assert svc.reserva(r["_id"])["status"] == "concluida"
    assert svc.notificacoes(garcom)[0]["tipo"] == "saida"             # RU-GAR-04
    svc.confirmar_limpeza(r["mesa"], garcom)
    assert svc.mesa(r["mesa"])["status"] == LIVRE


def test_rn08_sem_reserva(svc, relogio):
    svc.ocupar_sem_reserva(5, 2, G_TERREO)                            # sem CPF
    assert svc.mesa(5)["status"] == NAO_ATENDIDA
    with pytest.raises(RegraNegocioErro, match="não está livre"):
        svc.ocupar_sem_reserva(5, 2, G_TERREO)
    with pytest.raises(RegraNegocioErro, match="comporta"):
        svc.ocupar_sem_reserva(1, 9, G_TERREO)
    with pytest.raises(RegraNegocioErro, match="CPF"):
        svc.ocupar_sem_reserva(2, 2, G_TERREO, cpf="12345678900")


def test_ocupar_mesa_com_reserva_proxima(svc, relogio):
    r = _reserva(svc, relogio, minutos=90)
    with pytest.raises(RegraNegocioErro, match="possui reserva"):
        svc.ocupar_sem_reserva(r["mesa"], 2, svc.mesa(r["mesa"])["garcom"])


def test_rn10_escalonamento(svc, relogio):
    svc.ocupar_sem_reserva(1, 2, G_TERREO)
    garcom = svc.mesa(1)["garcom"]
    outros = [g for g in svc.garcons_do_pavimento("terreo") if g != garcom]
    assert svc.notificacoes(outros[0]) == []
    relogio.avancar(config.TIMEOUT_NOTIFICACAO_MIN + 0.5)
    assert svc.processar_rotinas()["notificacoes_escalonadas"] == 1
    assert len(svc.notificacoes(outros[0])) == 1
    assert svc.notificacoes("G25") == []                              # mezanino não recebe
    n = svc.notificacoes(outros[0])[0]
    svc.confirmar_notificacao(n["_id"], outros[0])
    assert svc.notificacoes(garcom) == []


def test_chamado_cliente(svc, relogio):
    svc.ocupar_sem_reserva(3, 2, G_TERREO, cpf=CPF_B)
    svc.chamar_garcom(CPF_B)
    with pytest.raises(RegraNegocioErro, match="já foi enviado"):
        svc.chamar_garcom(CPF_B)
    with pytest.raises(RegraNegocioErro, match="não está acomodado"):
        svc.chamar_garcom(CPF_A)


# ----------------------------------------------------------------- Pedidos
def _mesa_ocupada(svc, numero=1, cpf=CPF_A):
    svc.ocupar_sem_reserva(numero, 2, G_TERREO, cpf=cpf)
    return svc.mesa(numero)["garcom"]


def test_rn14_rn15(svc, relogio):
    with pytest.raises(RegraNegocioErro, match="mesas ocupadas"):
        svc.lancar_pedido(10, [{"codigo": 5, "quantidade": 1}], G_TERREO)
    _mesa_ocupada(svc)
    with pytest.raises(RegraNegocioErro, match="perfil"):
        svc.lancar_pedido(1, [{"codigo": 5, "quantidade": 1}], "C01")


def test_ciclo_completo_do_pedido(svc, relogio):
    g = _mesa_ocupada(svc)
    pid = svc.lancar_pedido(1, [{"codigo": 5, "quantidade": 1, "observacao": "sem queijo"},
                                {"codigo": 14, "quantidade": 2}], g)
    assert svc.mesa(1)["status"] == ATENDIDA                         # primeiro pedido = atendimento
    p = svc.pedido(pid)
    assert p["tempo_preparo_min"] == 25 and p["tempo_esperado_min"] == 25   # RN-17
    with pytest.raises(RegraNegocioErro):
        svc.marcar_pronto(pid, "C01")                                  # RN-16 pula etapa
    svc.iniciar_preparo(pid, "C01")
    assert svc.pedido(pid)["chefe"] == "C01"
    with pytest.raises(RegraNegocioErro, match="cancelado"):
        svc.cancelar_pedido(pid, g)                                    # RN-19
    with pytest.raises(RegraNegocioErro, match="Conclua"):
        svc.liberar_mesa(1, g)
    relogio.avancar(20)
    svc.marcar_pronto(pid, "C01")
    assert svc.notificacoes(g)[0]["tipo"] == "pronto"                # RN-21
    relogio.avancar(config.TIMEOUT_RETIRADA_MIN + 0.5)
    svc.processar_rotinas()
    assert any(n["tipo"] == "pronto" for n in svc.notificacoes("G05"))  # escalonou
    svc.confirmar_retirada(pid, "G05")
    assert svc.notificacoes("G05") == [] and svc.notificacoes(g) == []
    svc.confirmar_entrega(pid, "G05")
    assert svc.pedido(pid)["status"] == "entregue"
    acomp = svc.acompanhamento_cliente(CPF_A)
    assert acomp["mesa"]["numero"] == 1 and acomp["pedidos"][0]["status"] == "entregue"
    svc.liberar_mesa(1, g)


def test_rn17_fila_com_cinco_chefes(svc, relogio):
    ids = []
    for mesa in range(1, 8):                                          # 7 pedidos de 25 min
        g = _mesa_ocupada(svc, mesa, cpf=None)
        ids.append(svc.lancar_pedido(mesa, [{"codigo": 5, "quantidade": 1}], g))
    tempos = [svc.pedido(i)["tempo_esperado_min"] for i in ids]
    assert tempos[:5] == [25] * 5 and tempos[5:] == [50, 50]           # 5 estações paralelas


def test_rn18_agrupamento_e_priorizacao(svc, relogio):
    g1 = _mesa_ocupada(svc, 1, cpf=None)
    a = svc.lancar_pedido(1, [{"codigo": 1, "quantidade": 1}], g1)
    relogio.avancar(1)
    g2 = _mesa_ocupada(svc, 2, cpf=None)
    b = svc.lancar_pedido(2, [{"codigo": 1, "quantidade": 1}], g2)
    relogio.avancar(1)
    c = svc.lancar_pedido(1, [{"codigo": 12, "quantidade": 1}], g1)
    assert [p["_id"] for p in svc.fila_cozinha()] == [a, c, b]        # mesa 1 agrupada
    with pytest.raises(RegraNegocioErro, match="justificativa"):
        svc.priorizar(b, "", "C02")
    svc.priorizar(b, "Cliente com restrição de horário", "C02")
    assert svc.fila_cozinha()[0]["_id"] == b


def test_rn20_atraso_e_ajuste(svc, relogio):
    g = _mesa_ocupada(svc)
    pid = svc.lancar_pedido(1, [{"codigo": 9, "quantidade": 1}], g)  # 15 min
    svc.iniciar_preparo(pid, "C01")
    relogio.avancar(16)
    svc.processar_rotinas()
    fila = svc.fila_cozinha()
    assert fila[0]["atrasado"]
    p = svc.pedido(pid)
    assert p["previsao_entrega"] > relogio()                          # novo prazo ao cliente
    assert svc.acompanhamento_cliente(CPF_A)["pedidos"][0]["atrasado"]
    with pytest.raises(RegraNegocioErro, match="motivo"):
        svc.ajustar_tempo(pid, 10, " ", "C01")
    svc.ajustar_tempo(pid, 10, "Forno sobrecarregado", "C01")
    assert not svc.fila_cozinha()[0]["atrasado"]


def test_cancelamento_recebido(svc, relogio):
    g = _mesa_ocupada(svc)
    pid = svc.lancar_pedido(1, [{"codigo": 1, "quantidade": 1}], g)
    svc.cancelar_pedido(pid, g)
    assert svc.pedido(pid)["status"] == "cancelado"
    assert svc.fila_cozinha() == []
    svc.liberar_mesa(1, g)                                            # cancelado não bloqueia


def test_rn26_eventos_registrados(svc, relogio):
    g = _mesa_ocupada(svc)
    svc.lancar_pedido(1, [{"codigo": 1, "quantidade": 1}], g)
    tipos = {e["tipo"] for e in svc.db.eventos.find()}
    assert {"status_mesa", "pedido_lancado"} <= tipos
    assert all(e["em"] and e["usuario"] for e in svc.db.eventos.find())


def test_resumo_ocupacao(svc, relogio):
    _mesa_ocupada(svc)
    r = svc.resumo_ocupacao()
    assert r["total"] == 100 and r["ocupada_nao_atendida"] == 1 and r["livre"] == 99


def test_mesa_ocupada_nao_recebe_reserva_proxima(svc, relogio):
    # ocupa todas as mesas de 8 lugares reserváveis do mezanino
    mesas8 = [m["numero"] for m in svc.db.mesas.find(
        {"capacidade": 8, "pavimento": "mezanino", "reservavel": True})]
    for n in mesas8:
        svc.ocupar_sem_reserva(n, 8, svc.mesa(n)["garcom"])
    with pytest.raises(RegraNegocioErro, match="Não há mesas"):
        _reserva(svc, relogio, minutos=90, pessoas=8, ambiente="mezanino")
    assert _reserva(svc, relogio, minutos=150, pessoas=8, ambiente="mezanino")  # após a permanência


def test_validacoes_de_reserva(svc, relogio):
    with pytest.raises(RegraNegocioErro, match="nome"):
        svc.criar_reserva(CPF_A, " ", "11999990000", relogio() + timedelta(hours=3), 2)
    with pytest.raises(RegraNegocioErro, match="telefone"):
        svc.criar_reserva(CPF_A, "Ana", "123", relogio() + timedelta(hours=3), 2)
    with pytest.raises(RegraNegocioErro, match="grupos acima"):
        svc.criar_reserva(CPF_A, "Ana", "11999990000", relogio() + timedelta(hours=3), 12)
    with pytest.raises(RegraNegocioErro, match="aceitas entre"):
        svc.criar_reserva(CPF_A, "Ana", "11999990000", relogio().replace(hour=23, minute=30), 2)


def test_checkin_fora_da_janela(svc, relogio):
    r = _reserva(svc, relogio, minutos=180)
    with pytest.raises(RegraNegocioErro, match="check-in"):
        svc.fazer_checkin(r["_id"], svc.mesa(r["mesa"])["garcom"])
