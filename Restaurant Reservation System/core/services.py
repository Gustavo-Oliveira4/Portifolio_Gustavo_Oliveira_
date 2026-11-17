"""Camada de serviços: concentra TODAS as regras de negócio do sistema.

A interface (Streamlit) apenas chama estes métodos; nenhuma regra fica na tela.
Os identificadores RN-xx e RU-xx remetem ao documento de requisitos.
"""
from __future__ import annotations

import heapq
import math
from datetime import datetime, timedelta

from bson import ObjectId
from bson.errors import InvalidId

from core import config
from core.utils import agora, limpar_cpf, minutos_entre, validar_cpf, verificar_senha, fmt_hora

# ------------------------------------------------------------------ Constantes
LIVRE = "livre"
RESERVADA = "reservada"                 # estado exibido (derivado das reservas)
NAO_ATENDIDA = "ocupada_nao_atendida"
ATENDIDA = "ocupada_atendida"
EM_LIBERACAO = "em_liberacao"
STATUS_OCUPADA = (NAO_ATENDIDA, ATENDIDA)

ROTULO_MESA = {
    LIVRE: "Livre", RESERVADA: "Reservada", NAO_ATENDIDA: "Ocupada – não atendida",
    ATENDIDA: "Ocupada – atendida", EM_LIBERACAO: "Em liberação",
}

# Ciclo do pedido (RN-16)
RECEBIDO, EM_PREPARO, PRONTO, RETIRADO, ENTREGUE, CANCELADO = (
    "recebido", "em_preparo", "pronto", "retirado", "entregue", "cancelado")
SEQUENCIA_PEDIDO = [RECEBIDO, EM_PREPARO, PRONTO, RETIRADO, ENTREGUE]
PEDIDO_NA_COZINHA = (RECEBIDO, EM_PREPARO)
PEDIDO_ABERTO = (RECEBIDO, EM_PREPARO, PRONTO, RETIRADO)
ROTULO_PEDIDO = {
    RECEBIDO: "Recebido", EM_PREPARO: "Em preparo", PRONTO: "Pronto",
    RETIRADO: "A caminho da mesa", ENTREGUE: "Entregue", CANCELADO: "Cancelado",
}

# Reservas
R_ATIVA, R_CHECKIN, R_CANCELADA, R_EXPIRADA, R_CONCLUIDA = (
    "ativa", "checkin", "cancelada", "expirada", "concluida")
ROTULO_RESERVA = {R_ATIVA: "Confirmada", R_CHECKIN: "Em andamento", R_CANCELADA: "Cancelada",
                  R_EXPIRADA: "Expirada", R_CONCLUIDA: "Concluída"}


class RegraNegocioErro(Exception):
    """Erro de validação de regra de negócio, exibido ao usuário."""


def _oid(valor) -> ObjectId:
    if isinstance(valor, ObjectId):
        return valor
    try:
        return ObjectId(str(valor))
    except (InvalidId, TypeError):
        raise RegraNegocioErro("Identificador inválido.")


class Servico:
    def __init__(self, db):
        self.db = db

    # ================================================================ Auditoria
    def _evento(self, tipo: str, entidade: str, ref, usuario: str | None,
                de: str | None = None, para: str | None = None, detalhe: str | None = None):
        """RN-26: toda mudança de estado é registrada com data, hora e usuário."""
        self.db.eventos.insert_one({
            "tipo": tipo, "entidade": entidade, "ref": ref, "usuario": usuario or "sistema",
            "de": de, "para": para, "detalhe": detalhe, "em": agora()})

    # ================================================================ Acesso
    def autenticar(self, matricula: str, senha: str) -> dict | None:
        """RN-22: acesso de funcionário com matrícula e senha."""
        doc = self.db.funcionarios.find_one(
            {"matricula": (matricula or "").strip().upper(), "ativo": True})
        if not doc or not verificar_senha(senha or "", doc["senha"]):
            return None
        doc.pop("senha", None)
        self._evento("login", "funcionario", doc["matricula"], doc["matricula"])
        return doc

    def funcionario(self, matricula: str) -> dict | None:
        return self.db.funcionarios.find_one({"matricula": matricula}, {"senha": 0})

    def garcons_do_pavimento(self, pavimento: str) -> list[str]:
        return [g["matricula"] for g in self.db.funcionarios.find(
            {"perfil": "garcom", "ativo": True, "pavimento": pavimento}, {"matricula": 1})]

    def _exigir_perfil(self, matricula: str, perfil: str):
        f = self.funcionario(matricula)
        if not f or f.get("perfil") != perfil:
            raise RegraNegocioErro("Ação não permitida para este perfil.")
        return f

    # ================================================================ Notificações
    def _notificar(self, tipo: str, mensagem: str, destinatario: str, mesa: int | None = None,
                   ref=None, escalonar_min: int | None = None):
        mesa_doc = self.db.mesas.find_one({"numero": mesa}) if mesa else None
        momento = agora()
        self.db.notificacoes.insert_one({
            "tipo": tipo, "mensagem": mensagem, "mesa": mesa,
            "pavimento": mesa_doc["pavimento"] if mesa_doc else None,
            "destinatarios": [destinatario], "destinatario_original": destinatario,
            "ref": ref, "criada_em": momento, "confirmada": False,
            "confirmada_por": None, "confirmada_em": None, "escalonada": False,
            "escalonar_apos": momento + timedelta(minutes=escalonar_min) if escalonar_min else None,
        })

    def notificacoes(self, matricula: str, pendentes: bool = True, limite: int = 50) -> list[dict]:
        filtro = {"destinatarios": matricula}
        if pendentes:
            filtro["confirmada"] = False
        return list(self.db.notificacoes.find(filtro).sort("criada_em", -1).limit(limite))

    def confirmar_notificacao(self, notificacao_id, matricula: str):
        res = self.db.notificacoes.update_one(
            {"_id": _oid(notificacao_id), "destinatarios": matricula, "confirmada": False},
            {"$set": {"confirmada": True, "confirmada_por": matricula, "confirmada_em": agora()}})
        if res.modified_count == 0:
            raise RegraNegocioErro("Notificação já confirmada ou indisponível.")

    def _confirmar_por_ref(self, ref, tipos: tuple, matricula: str):
        self.db.notificacoes.update_many(
            {"ref": ref, "tipo": {"$in": list(tipos)}, "confirmada": False},
            {"$set": {"confirmada": True, "confirmada_por": matricula, "confirmada_em": agora()}})

    # ================================================================ Mesas
    def mesa(self, numero: int) -> dict:
        doc = self.db.mesas.find_one({"numero": int(numero)})
        if not doc:
            raise RegraNegocioErro(f"Mesa {numero} não encontrada.")
        return doc

    def _mudar_status_mesa(self, numero: int, novo: str, usuario: str, extra: dict | None = None):
        atual = self.mesa(numero)
        campos = {"status": novo, "status_desde": agora(), **(extra or {})}
        self.db.mesas.update_one({"numero": numero}, {"$set": campos})
        self._evento("status_mesa", "mesa", numero, usuario, atual["status"], novo)

    def _reserva_proxima(self, numero: int, momento: datetime | None = None) -> dict | None:
        """Reserva ativa da mesa dentro da janela em que a mesa aparece como Reservada."""
        momento = momento or agora()
        return self.db.reservas.find_one({
            "mesa": numero, "status": R_ATIVA,
            "data_hora": {"$gte": momento - timedelta(minutes=config.TOLERANCIA_ATRASO_MIN),
                          "$lte": momento + timedelta(minutes=config.JANELA_EXIBIR_RESERVADA_MIN)},
        }, sort=[("data_hora", 1)])

    def proxima_reserva(self, numero: int) -> dict | None:
        """Próxima reserva ativa da mesa (a partir do início da tolerância)."""
        return self.db.reservas.find_one({
            "mesa": int(numero), "status": R_ATIVA,
            "data_hora": {"$gte": agora() - timedelta(minutes=config.TOLERANCIA_ATRASO_MIN)}},
            sort=[("data_hora", 1)])

    def listar_mesas(self, pavimento: str | None = None) -> list[dict]:
        """Mapa de mesas com estado exibido, espera e alertas (RU-GAR-02, RU-GAR-08, RN-12)."""
        filtro = {"pavimento": pavimento} if pavimento else {}
        mesas = list(self.db.mesas.find(filtro).sort("numero", 1))
        momento = agora()
        lim_inf = momento - timedelta(minutes=config.TOLERANCIA_ATRASO_MIN)
        lim_sup = momento + timedelta(minutes=config.JANELA_EXIBIR_RESERVADA_MIN)
        reservas = {}
        for r in self.db.reservas.find({"status": R_ATIVA,
                                        "data_hora": {"$gte": lim_inf, "$lte": lim_sup}}).sort("data_hora", 1):
            reservas.setdefault(r["mesa"], r)
        atendimentos = {a["_id"]: a for a in self.db.atendimentos.find({"fim": None})}
        pedidos_por_at: dict = {}
        for p in self.db.pedidos.find({"status": {"$in": list(PEDIDO_ABERTO)}}, {"atendimento_id": 1, "status": 1}):
            pedidos_por_at.setdefault(p["atendimento_id"], []).append(p["status"])

        for m in mesas:
            m["status_exibicao"] = m["status"]
            m["reserva"] = reservas.get(m["numero"])
            if m["status"] == LIVRE and m["reserva"]:
                m["status_exibicao"] = RESERVADA
            at = atendimentos.get(m.get("atendimento_id"))
            m["atendimento"] = at
            m["espera_min"] = minutos_entre(at["inicio"], momento) if at and m["status"] == NAO_ATENDIDA else 0
            m["alerta"] = m["status"] == NAO_ATENDIDA and m["espera_min"] > config.ALERTA_NAO_ATENDIDA_MIN
            st = pedidos_por_at.get(m.get("atendimento_id"), [])
            m["pedidos_abertos"] = len(st)
            m["pedidos_prontos"] = st.count(PRONTO)
        return mesas

    # ================================================================ Reservas
    @staticmethod
    def turno(data_hora: datetime) -> str:
        return "almoco" if data_hora.hour < config.HORA_INICIO_JANTAR else "jantar"

    def _validar_horario(self, data_hora: datetime):
        fim_ultimo = config.HORARIO_FECHAMENTO - 1  # última reserva 1h antes de fechar
        if not (config.HORARIO_ABERTURA <= data_hora.hour <= fim_ultimo):
            raise RegraNegocioErro(
                f"Reservas são aceitas entre {config.HORARIO_ABERTURA}h e {fim_ultimo}h.")

    def capacidade_maxima(self) -> int:
        doc = self.db.mesas.find_one(sort=[("capacidade", -1)])
        return doc["capacidade"] if doc else 0

    def _mesa_disponivel(self, mesa: dict, data_hora: datetime, ignorar_reserva=None) -> bool:
        """RN-03: sem sobreposição de horários na mesma mesa."""
        janela = timedelta(minutes=config.DURACAO_PERMANENCIA_MIN)
        filtro = {"mesa": mesa["numero"], "status": {"$in": [R_ATIVA, R_CHECKIN]},
                  "data_hora": {"$gt": data_hora - janela, "$lt": data_hora + janela}}
        if ignorar_reserva:
            filtro["_id"] = {"$ne": ignorar_reserva}
        if self.db.reservas.count_documents(filtro):
            return False
        # Mesa ocupada agora: considera a permanência média a partir da chegada dos clientes.
        if mesa["status"] in STATUS_OCUPADA:
            at = self.db.atendimentos.find_one({"_id": mesa.get("atendimento_id")}) or {}
            if data_hora < at.get("inicio", mesa["status_desde"]) + janela:
                return False
        return True

    def mesas_disponiveis(self, data_hora: datetime, pessoas: int, ambiente: str | None = None,
                          apenas_reservaveis: bool = True, ignorar_reserva=None) -> list[dict]:
        """RN-04: mesas compatíveis, priorizando a menor capacidade ociosa."""
        filtro = {"capacidade": {"$gte": int(pessoas)}}
        if ambiente:
            filtro["pavimento"] = ambiente
        if apenas_reservaveis:
            filtro["reservavel"] = True
        candidatas = self.db.mesas.find(filtro).sort([("capacidade", 1), ("numero", 1)])
        return [m for m in candidatas if self._mesa_disponivel(m, data_hora, ignorar_reserva)]

    def _validar_dados_reserva(self, cpf: str, nome: str, telefone: str, pessoas: int):
        if not validar_cpf(cpf):
            raise RegraNegocioErro("CPF inválido. Verifique os 11 dígitos.")  # RN-01
        if not (nome or "").strip():
            raise RegraNegocioErro("Informe o nome para a reserva.")
        if len(limpar_cpf(telefone)) < 10:
            raise RegraNegocioErro("Informe um telefone válido com DDD.")
        if int(pessoas) < 1:
            raise RegraNegocioErro("Informe ao menos 1 pessoa.")
        if int(pessoas) > self.capacidade_maxima():
            raise RegraNegocioErro(
                f"Para grupos acima de {self.capacidade_maxima()} pessoas, fale com o restaurante.")

    def _validar_unica_por_turno(self, cpf: str, data_hora: datetime, ignorar=None):
        """RN-02: uma reserva ativa por CPF, por data e turno."""
        inicio = data_hora.replace(hour=0, minute=0, second=0)
        filtro = {"cpf": cpf, "status": {"$in": [R_ATIVA, R_CHECKIN]},
                  "data_hora": {"$gte": inicio, "$lt": inicio + timedelta(days=1)}}
        if ignorar:
            filtro["_id"] = {"$ne": ignorar}
        for r in self.db.reservas.find(filtro):
            if self.turno(r["data_hora"]) == self.turno(data_hora):
                raise RegraNegocioErro("Este CPF já possui uma reserva ativa nesta data e turno.")

    def criar_reserva(self, cpf: str, nome: str, telefone: str, data_hora: datetime, pessoas: int,
                      ambiente: str | None = None, origem: str = "cliente",
                      usuario: str | None = None, mesa_numero: int | None = None) -> dict:
        cpf = limpar_cpf(cpf)
        self._validar_dados_reserva(cpf, nome, telefone, pessoas)
        data_hora = data_hora.replace(second=0, microsecond=0)
        self._validar_horario(data_hora)
        if data_hora <= agora():
            raise RegraNegocioErro("A data e o horário da reserva devem ser futuros.")
        if origem == "cliente" and data_hora < agora() + timedelta(minutes=config.ANTECEDENCIA_MIN_RESERVA):
            raise RegraNegocioErro(  # RN-05
                f"Reservas exigem antecedência mínima de {config.ANTECEDENCIA_MIN_RESERVA} minutos.")
        self._validar_unica_por_turno(cpf, data_hora)

        if mesa_numero:  # escolha manual pelo garçom
            mesa = self.mesa(mesa_numero)
            if mesa["capacidade"] < int(pessoas):
                raise RegraNegocioErro("A mesa escolhida não comporta o número de pessoas.")
            if not self._mesa_disponivel(mesa, data_hora):
                raise RegraNegocioErro("A mesa escolhida já está comprometida nesse horário.")
        else:
            opcoes = self.mesas_disponiveis(data_hora, pessoas, ambiente,
                                            apenas_reservaveis=(origem == "cliente"))
            if not opcoes:
                raise RegraNegocioErro("Não há mesas disponíveis para esse horário e número de pessoas.")
            mesa = opcoes[0]

        doc = {"cpf": cpf, "nome": nome.strip(), "telefone": telefone.strip(),
               "data_hora": data_hora, "turno": self.turno(data_hora), "pessoas": int(pessoas),
               "ambiente": mesa["pavimento"], "mesa": mesa["numero"], "status": R_ATIVA,
               "origem": origem, "criada_por": usuario or "cliente", "criada_em": agora()}
        doc["_id"] = self.db.reservas.insert_one(doc).inserted_id
        self._evento("reserva_criada", "reserva", doc["_id"], usuario or "cliente", None, R_ATIVA,
                     f"Mesa {mesa['numero']} – {data_hora:%d/%m %H:%M}")
        return doc

    def reserva(self, reserva_id) -> dict:
        doc = self.db.reservas.find_one({"_id": _oid(reserva_id)})
        if not doc:
            raise RegraNegocioErro("Reserva não encontrada.")
        return doc

    def reservas_do_cliente(self, cpf: str) -> list[dict]:
        """RN-23: o cliente vê apenas o que está vinculado ao seu CPF."""
        return list(self.db.reservas.find({"cpf": limpar_cpf(cpf)}).sort("data_hora", -1).limit(20))

    def _checar_prazo_alteracao(self, reserva: dict):
        if reserva["status"] != R_ATIVA:
            raise RegraNegocioErro("Somente reservas confirmadas podem ser alteradas ou canceladas.")
        if reserva["data_hora"] - agora() < timedelta(minutes=config.ANTECEDENCIA_MIN_RESERVA):
            raise RegraNegocioErro(  # RN-05
                f"Alterações e cancelamentos são permitidos até {config.ANTECEDENCIA_MIN_RESERVA} "
                "minutos antes do horário reservado.")

    def alterar_reserva(self, reserva_id, cpf: str, data_hora: datetime, pessoas: int,
                        ambiente: str | None = None) -> dict:
        reserva = self.reserva(reserva_id)
        if reserva["cpf"] != limpar_cpf(cpf):
            raise RegraNegocioErro("Reserva não pertence a este CPF.")
        self._checar_prazo_alteracao(reserva)
        self._validar_dados_reserva(reserva["cpf"], reserva["nome"], reserva["telefone"], pessoas)
        data_hora = data_hora.replace(second=0, microsecond=0)
        self._validar_horario(data_hora)
        if data_hora < agora() + timedelta(minutes=config.ANTECEDENCIA_MIN_RESERVA):
            raise RegraNegocioErro(
                f"O novo horário exige antecedência mínima de {config.ANTECEDENCIA_MIN_RESERVA} minutos.")
        self._validar_unica_por_turno(reserva["cpf"], data_hora, ignorar=reserva["_id"])
        opcoes = self.mesas_disponiveis(data_hora, pessoas, ambiente, True, ignorar_reserva=reserva["_id"])
        if not opcoes:
            raise RegraNegocioErro("Não há mesas disponíveis para o novo horário.")
        mesa = next((m for m in opcoes if m["numero"] == reserva["mesa"]), opcoes[0])
        novos = {"data_hora": data_hora, "turno": self.turno(data_hora), "pessoas": int(pessoas),
                 "mesa": mesa["numero"], "ambiente": mesa["pavimento"], "alterada_em": agora()}
        self.db.reservas.update_one({"_id": reserva["_id"]}, {"$set": novos})
        self._evento("reserva_alterada", "reserva", reserva["_id"], "cliente",
                     detalhe=f"Mesa {mesa['numero']} – {data_hora:%d/%m %H:%M}")
        return {**reserva, **novos}

    def cancelar_reserva(self, reserva_id, cpf: str | None = None, usuario: str | None = None):
        reserva = self.reserva(reserva_id)
        if cpf is not None:  # cancelamento pelo cliente
            if reserva["cpf"] != limpar_cpf(cpf):
                raise RegraNegocioErro("Reserva não pertence a este CPF.")
            self._checar_prazo_alteracao(reserva)
        elif reserva["status"] != R_ATIVA:
            raise RegraNegocioErro("Somente reservas confirmadas podem ser canceladas.")
        self.db.reservas.update_one({"_id": reserva["_id"]},
                                    {"$set": {"status": R_CANCELADA, "cancelada_em": agora()}})
        self._evento("reserva_cancelada", "reserva", reserva["_id"], usuario or "cliente",
                     R_ATIVA, R_CANCELADA)

    def reservas_do_dia(self, dia: datetime | None = None, pavimento: str | None = None) -> list[dict]:
        dia = (dia or agora()).replace(hour=0, minute=0, second=0, microsecond=0)
        filtro = {"data_hora": {"$gte": dia, "$lt": dia + timedelta(days=1)}}
        if pavimento:
            filtro["ambiente"] = pavimento
        return list(self.db.reservas.find(filtro).sort("data_hora", 1))

    # ================================================================ Ocupação
    def _abrir_atendimento(self, mesa: dict, usuario: str, pessoas: int, cpf: str | None,
                           nome: str | None, reserva_id=None) -> ObjectId:
        momento = agora()
        at_id = self.db.atendimentos.insert_one({
            "mesa": mesa["numero"], "pavimento": mesa["pavimento"], "reserva_id": reserva_id,
            "cpf": cpf, "nome": nome, "pessoas": int(pessoas), "inicio": momento,
            "primeiro_atendimento_em": None, "fim": None, "aberto_por": usuario,
        }).inserted_id
        self._mudar_status_mesa(mesa["numero"], NAO_ATENDIDA, usuario, {"atendimento_id": at_id})
        # RU-GAR-03 / RN-10: notifica o garçom do setor, com escalonamento
        self._notificar("entrada", f"Clientes acomodados na mesa {mesa['numero']} ({pessoas} pessoas).",
                        mesa["garcom"], mesa["numero"], ref=at_id,
                        escalonar_min=config.TIMEOUT_NOTIFICACAO_MIN)
        return at_id

    def fazer_checkin(self, reserva_id, usuario: str) -> ObjectId:
        """RU-GAR-05: registra a chegada de clientes com reserva."""
        self._exigir_perfil(usuario, "garcom")
        reserva = self.reserva(reserva_id)
        if reserva["status"] != R_ATIVA:
            raise RegraNegocioErro("A reserva não está ativa.")
        momento = agora()
        if reserva["data_hora"] - momento > timedelta(minutes=config.JANELA_EXIBIR_RESERVADA_MIN):
            raise RegraNegocioErro(
                f"O check-in só pode ser feito a partir de {config.JANELA_EXIBIR_RESERVADA_MIN} min antes do horário.")
        mesa = self.mesa(reserva["mesa"])
        if mesa["status"] != LIVRE:
            raise RegraNegocioErro(f"A mesa {mesa['numero']} ainda não está livre.")
        at_id = self._abrir_atendimento(mesa, usuario, reserva["pessoas"], reserva["cpf"],
                                        reserva["nome"], reserva["_id"])
        self.db.reservas.update_one({"_id": reserva["_id"]},
                                    {"$set": {"status": R_CHECKIN, "checkin_em": momento}})
        self._evento("checkin", "reserva", reserva["_id"], usuario, R_ATIVA, R_CHECKIN)
        return at_id

    def ocupar_sem_reserva(self, numero: int, pessoas: int, usuario: str,
                           cpf: str | None = None, nome: str | None = None) -> ObjectId:
        """RU-GAR-06 / RN-08: alocação manual de clientes sem agendamento."""
        self._exigir_perfil(usuario, "garcom")
        mesa = self.mesa(numero)
        if mesa["status"] != LIVRE:
            raise RegraNegocioErro(f"A mesa {numero} não está livre.")
        if int(pessoas) < 1 or mesa["capacidade"] < int(pessoas):
            raise RegraNegocioErro(f"A mesa {numero} comporta até {mesa['capacidade']} pessoas.")
        cpf = limpar_cpf(cpf) or None
        if cpf and not validar_cpf(cpf):
            raise RegraNegocioErro("CPF inválido. Deixe em branco caso o cliente não queira informar.")
        # RN-03: não ocupar mesa que tem reserva começando dentro da permanência média
        conflito = self.db.reservas.find_one({
            "mesa": numero, "status": R_ATIVA,
            "data_hora": {"$gte": agora() - timedelta(minutes=config.TOLERANCIA_ATRASO_MIN),
                          "$lt": agora() + timedelta(minutes=config.DURACAO_PERMANENCIA_MIN)}})
        if conflito:
            raise RegraNegocioErro(
                f"A mesa {numero} possui reserva às {fmt_hora(conflito['data_hora'])}. Escolha outra mesa.")
        return self._abrir_atendimento(mesa, usuario, pessoas, cpf, (nome or "").strip() or None)

    def registrar_atendimento(self, numero: int, usuario: str):
        """RN-11: encerra a contagem de espera no primeiro atendimento."""
        mesa = self.mesa(numero)
        if mesa["status"] != NAO_ATENDIDA:
            raise RegraNegocioErro("A mesa não está aguardando o primeiro atendimento.")
        momento = agora()
        self.db.atendimentos.update_one({"_id": mesa["atendimento_id"]},
                                        {"$set": {"primeiro_atendimento_em": momento,
                                                  "atendido_por": usuario}})
        self._mudar_status_mesa(numero, ATENDIDA, usuario)
        self._confirmar_por_ref(mesa["atendimento_id"], ("entrada", "chamado"), usuario)

    def liberar_mesa(self, numero: int, usuario: str):
        """RN-13 / RU-GAR-11: encerra o atendimento e envia a mesa para higienização."""
        mesa = self.mesa(numero)
        if mesa["status"] not in STATUS_OCUPADA:
            raise RegraNegocioErro("A mesa não está ocupada.")
        if self.db.pedidos.count_documents({"atendimento_id": mesa["atendimento_id"],
                                            "status": {"$in": list(PEDIDO_ABERTO)}}):
            raise RegraNegocioErro("Há pedidos em andamento nesta mesa. Conclua ou cancele antes de liberar.")
        momento = agora()
        at = self.db.atendimentos.find_one({"_id": mesa["atendimento_id"]})
        self.db.atendimentos.update_one({"_id": at["_id"]}, {"$set": {"fim": momento, "fechado_por": usuario}})
        if at.get("reserva_id"):
            self.db.reservas.update_one({"_id": at["reserva_id"]}, {"$set": {"status": R_CONCLUIDA}})
        self._confirmar_por_ref(at["_id"], ("entrada", "chamado"), usuario)
        self._mudar_status_mesa(numero, EM_LIBERACAO, usuario, {"atendimento_id": None})
        # RU-GAR-04: notifica a saída para providenciar a limpeza
        self._notificar("saida", f"Mesa {numero} liberada – aguardando higienização.",
                        mesa["garcom"], numero, ref=at["_id"],
                        escalonar_min=config.TIMEOUT_NOTIFICACAO_MIN)

    def confirmar_limpeza(self, numero: int, usuario: str):
        mesa = self.mesa(numero)
        if mesa["status"] != EM_LIBERACAO:
            raise RegraNegocioErro("A mesa não está em liberação.")
        self.db.notificacoes.update_many(
            {"mesa": numero, "tipo": "saida", "confirmada": False},
            {"$set": {"confirmada": True, "confirmada_por": usuario, "confirmada_em": agora()}})
        self._mudar_status_mesa(numero, LIVRE, usuario)

    def atendimento_do_cliente(self, cpf: str) -> dict | None:
        return self.db.atendimentos.find_one({"cpf": limpar_cpf(cpf), "fim": None})

    def chamar_garcom(self, cpf: str):
        """RU-CLI-08: chamado do cliente ao garçom do setor."""
        at = self.atendimento_do_cliente(cpf)
        if not at:
            raise RegraNegocioErro("Você não está acomodado em nenhuma mesa no momento.")
        if self.db.notificacoes.find_one({"ref": at["_id"], "tipo": "chamado", "confirmada": False}):
            raise RegraNegocioErro("Seu chamado já foi enviado. O garçom está a caminho.")
        mesa = self.mesa(at["mesa"])
        self._notificar("chamado", f"A mesa {mesa['numero']} está chamando o garçom.",
                        mesa["garcom"], mesa["numero"], ref=at["_id"],
                        escalonar_min=config.TIMEOUT_NOTIFICACAO_MIN)
        self._evento("chamado_cliente", "mesa", mesa["numero"], "cliente")

    # ================================================================ Cardápio
    def cardapio(self) -> list[dict]:
        return list(self.db.cardapio.find({"ativo": True}).sort([("categoria", 1), ("nome", 1)]))

    # ================================================================ Pedidos
    def pedido(self, pedido_id) -> dict:
        doc = self.db.pedidos.find_one({"_id": _oid(pedido_id)})
        if not doc:
            raise RegraNegocioErro("Pedido não encontrado.")
        return doc

    def lancar_pedido(self, numero: int, itens: list[dict], usuario: str) -> ObjectId:
        """RU-GAR-07 / RN-14 / RN-15: lança o pedido e envia aos totens."""
        self._exigir_perfil(usuario, "garcom")
        mesa = self.mesa(numero)
        if mesa["status"] not in STATUS_OCUPADA:
            raise RegraNegocioErro("Pedidos só podem ser lançados para mesas ocupadas.")
        itens = [i for i in itens if int(i.get("quantidade", 0)) > 0]
        if not itens:
            raise RegraNegocioErro("Adicione ao menos um item ao pedido.")
        cardapio = {c["codigo"]: c for c in self.cardapio()}
        linhas = []
        for i in itens:
            c = cardapio.get(int(i["codigo"]))
            if not c:
                raise RegraNegocioErro("Item de cardápio inválido.")
            linhas.append({"codigo": c["codigo"], "nome": c["nome"], "quantidade": int(i["quantidade"]),
                           "observacao": (i.get("observacao") or "").strip(),
                           "tempo_preparo_min": c["tempo_preparo_min"], "preco": c["preco"]})
        if mesa["status"] == NAO_ATENDIDA:  # RN-11: o primeiro pedido encerra a espera
            self.registrar_atendimento(numero, usuario)
        at = self.db.atendimentos.find_one({"_id": mesa["atendimento_id"]})
        momento = agora()
        pid = self.db.pedidos.insert_one({
            "mesa": numero, "pavimento": mesa["pavimento"], "atendimento_id": at["_id"],
            "cpf": at.get("cpf"), "garcom": mesa["garcom"], "lancado_por": usuario,
            "itens": linhas, "tempo_preparo_min": max(l["tempo_preparo_min"] for l in linhas),
            "status": RECEBIDO, "lancado_em": momento, "prioridade": 0, "ajuste_min": 0,
            "chefe": None, "historico": [{"status": RECEBIDO, "em": momento, "por": usuario}],
            "ajustes": [], "previsao_inicial": None, "previsao_entrega": None,
        }).inserted_id
        self._evento("pedido_lancado", "pedido", pid, usuario, None, RECEBIDO, f"Mesa {numero}")
        self.recalcular_fila(fixar_previsao_de=pid)
        return pid

    def _avancar(self, pedido: dict, esperado: str, novo: str, usuario: str, extra: dict | None = None):
        """RN-16: garante a sequência Recebido → Em preparo → Pronto → Retirado → Entregue."""
        if pedido["status"] != esperado:
            raise RegraNegocioErro(
                f"Ação inválida: o pedido está como '{ROTULO_PEDIDO[pedido['status']]}'.")
        momento = agora()
        res = self.db.pedidos.update_one(
            {"_id": pedido["_id"], "status": esperado},  # evita concorrência entre totens
            {"$set": {"status": novo, f"{novo}_em": momento, **(extra or {})},
             "$push": {"historico": {"status": novo, "em": momento, "por": usuario}}})
        if res.modified_count == 0:
            raise RegraNegocioErro("O pedido foi atualizado por outro usuário. Atualize a tela.")
        self._evento("status_pedido", "pedido", pedido["_id"], usuario, esperado, novo)

    def cancelar_pedido(self, pedido_id, usuario: str):
        """RN-19: cancelamento apenas antes do início do preparo."""
        self._exigir_perfil(usuario, "garcom")
        p = self.pedido(pedido_id)
        if p["status"] != RECEBIDO:
            raise RegraNegocioErro("O pedido só pode ser cancelado antes de entrar em preparo.")
        self._avancar(p, RECEBIDO, CANCELADO, usuario)
        self.recalcular_fila()

    def iniciar_preparo(self, pedido_id, chefe: str):
        """RU-COZ-04 / RU-COZ-05: o chefe assume o pedido."""
        self._exigir_perfil(chefe, "cozinha")
        p = self.pedido(pedido_id)
        self._avancar(p, RECEBIDO, EM_PREPARO, chefe, {"chefe": chefe})
        self.recalcular_fila()

    def marcar_pronto(self, pedido_id, chefe: str):
        """RU-COZ-06 / RN-21: pronto → chama o garçom responsável."""
        self._exigir_perfil(chefe, "cozinha")
        p = self.pedido(pedido_id)
        self._avancar(p, EM_PREPARO, PRONTO, chefe)
        self._notificar("pronto", f"Pedido da mesa {p['mesa']} pronto para retirada.",
                        p["garcom"], p["mesa"], ref=p["_id"], escalonar_min=config.TIMEOUT_RETIRADA_MIN)
        self.recalcular_fila()

    def confirmar_retirada(self, pedido_id, usuario: str):
        """RU-GAR-10"""
        self._exigir_perfil(usuario, "garcom")
        p = self.pedido(pedido_id)
        self._avancar(p, PRONTO, RETIRADO, usuario, {"retirado_por": usuario})
        self._confirmar_por_ref(p["_id"], ("pronto",), usuario)

    def confirmar_entrega(self, pedido_id, usuario: str):
        """RU-GAR-10"""
        self._exigir_perfil(usuario, "garcom")
        p = self.pedido(pedido_id)
        self._avancar(p, RETIRADO, ENTREGUE, usuario)

    def ajustar_tempo(self, pedido_id, minutos: int, justificativa: str, chefe: str):
        """RU-COZ-08: ajuste do tempo esperado mediante justificativa."""
        self._exigir_perfil(chefe, "cozinha")
        if not (justificativa or "").strip():
            raise RegraNegocioErro("Informe o motivo do ajuste.")
        if int(minutos) == 0:
            raise RegraNegocioErro("Informe um ajuste diferente de zero.")
        p = self.pedido(pedido_id)
        if p["status"] not in PEDIDO_NA_COZINHA:
            raise RegraNegocioErro("Só é possível ajustar pedidos em preparo ou na fila.")
        if p["tempo_preparo_min"] + p["ajuste_min"] + int(minutos) < 1:
            raise RegraNegocioErro("O tempo resultante deve ser de pelo menos 1 minuto.")
        momento = agora()
        self.db.pedidos.update_one({"_id": p["_id"]}, {
            "$inc": {"ajuste_min": int(minutos)},
            "$set": {"previsao_inicial": p["previsao_inicial"] + timedelta(minutes=int(minutos))},
            "$push": {"ajustes": {"minutos": int(minutos), "motivo": justificativa.strip(),
                                  "por": chefe, "em": momento}}})
        self._evento("ajuste_tempo", "pedido", p["_id"], chefe, detalhe=f"{minutos:+d} min: {justificativa}")
        self.recalcular_fila()

    def priorizar(self, pedido_id, justificativa: str, chefe: str):
        """RN-18: reordenação da fila exige justificativa do chefe."""
        self._exigir_perfil(chefe, "cozinha")
        if not (justificativa or "").strip():
            raise RegraNegocioErro("Informe a justificativa para priorizar o pedido.")
        p = self.pedido(pedido_id)
        if p["status"] != RECEBIDO:
            raise RegraNegocioErro("Apenas pedidos aguardando preparo podem ser priorizados.")
        maior = self.db.pedidos.find_one({"status": RECEBIDO}, sort=[("prioridade", -1)])
        self.db.pedidos.update_one({"_id": p["_id"]}, {
            "$set": {"prioridade": (maior["prioridade"] if maior else 0) + 1},
            "$push": {"ajustes": {"minutos": 0, "motivo": f"Priorizado: {justificativa.strip()}",
                                  "por": chefe, "em": agora()}}})
        self._evento("priorizacao", "pedido", p["_id"], chefe, detalhe=justificativa)
        self.recalcular_fila()

    # ---------------------------------------------------------------- Fila
    def fila_cozinha(self) -> list[dict]:
        """RN-18: prioridade, depois agrupamento por mesa, depois ordem de lançamento."""
        pedidos = list(self.db.pedidos.find({"status": {"$in": list(PEDIDO_NA_COZINHA)}}))
        ancora: dict = {}
        for p in pedidos:
            a = ancora.get(p["atendimento_id"])
            ancora[p["atendimento_id"]] = min(a, p["lancado_em"]) if a else p["lancado_em"]
        pedidos.sort(key=lambda p: (p["status"] != EM_PREPARO, -p.get("prioridade", 0),
                                    ancora[p["atendimento_id"]], p["lancado_em"]))
        momento = agora()
        for p in pedidos:
            p["decorrido_min"] = minutos_entre(p["lancado_em"], momento)
            p["atrasado"] = bool(p.get("previsao_inicial")) and momento > p["previsao_inicial"]
        return pedidos

    def recalcular_fila(self, fixar_previsao_de=None):
        """RN-17: tempo esperado = preparo do prato + tempo estimado da fila.

        Simula os chefes como 'estações' paralelas: cada pedido ocupa a primeira
        estação livre durante o seu tempo de preparo (o maior entre os itens).
        """
        momento = agora()
        estacoes = [momento] * max(1, self.db.funcionarios.count_documents(
            {"perfil": "cozinha", "ativo": True}))
        heapq.heapify(estacoes)
        for p in self.fila_cozinha():
            duracao = timedelta(minutes=p["tempo_preparo_min"] + p.get("ajuste_min", 0))
            inicio_estacao = heapq.heappop(estacoes)
            if p["status"] == EM_PREPARO:
                previsto = p["em_preparo_em"] + duracao
                if previsto < momento:  # RN-20: atrasado → novo prazo para o cliente
                    previsto = momento + timedelta(minutes=2)
            else:
                previsto = max(inicio_estacao, momento) + duracao
            heapq.heappush(estacoes, max(previsto, inicio_estacao))
            campos = {"previsao_entrega": previsto,
                      "tempo_esperado_min": math.ceil(minutos_entre(p["lancado_em"], previsto))}
            if p["_id"] == fixar_previsao_de or not p.get("previsao_inicial"):
                campos["previsao_inicial"] = previsto
            self.db.pedidos.update_one({"_id": p["_id"]}, {"$set": campos})

    def pedidos_do_atendimento(self, atendimento_id) -> list[dict]:
        if not atendimento_id:
            return []
        return list(self.db.pedidos.find({"atendimento_id": atendimento_id}).sort("lancado_em", 1))

    def pedidos_prontos(self, pavimento: str | None = None) -> list[dict]:
        filtro = {"status": PRONTO}
        if pavimento:
            filtro["pavimento"] = pavimento
        return list(self.db.pedidos.find(filtro).sort("pronto_em", 1))

    def acompanhamento_cliente(self, cpf: str) -> dict | None:
        """RU-CLI-06 / RU-CLI-07: mesa atual e pedidos com tempo estimado."""
        at = self.atendimento_do_cliente(cpf)
        if not at:
            return None
        pedidos = self.pedidos_do_atendimento(at["_id"])
        momento = agora()
        for p in pedidos:
            p["atrasado"] = (p["status"] in PEDIDO_NA_COZINHA and p.get("previsao_inicial")
                             and momento > p["previsao_inicial"])
            p["restante_min"] = (max(0.0, minutos_entre(momento, p["previsao_entrega"]))
                                 if p["status"] in PEDIDO_NA_COZINHA and p.get("previsao_entrega") else 0)
        chamado = self.db.notificacoes.find_one({"ref": at["_id"], "tipo": "chamado", "confirmada": False})
        return {"atendimento": at, "mesa": self.mesa(at["mesa"]), "pedidos": pedidos,
                "chamado_pendente": bool(chamado)}

    # ================================================================ Rotinas
    def processar_rotinas(self) -> dict:
        """Executada a cada atualização de tela: expira reservas e escalona avisos."""
        momento = agora()
        resultado = {"reservas_expiradas": 0, "notificacoes_escalonadas": 0}

        # RN-06: tolerância de atraso
        limite = momento - timedelta(minutes=config.TOLERANCIA_ATRASO_MIN)
        for r in list(self.db.reservas.find({"status": R_ATIVA, "data_hora": {"$lt": limite}})):
            res = self.db.reservas.update_one({"_id": r["_id"], "status": R_ATIVA},
                                              {"$set": {"status": R_EXPIRADA, "expirada_em": momento}})
            if res.modified_count:
                resultado["reservas_expiradas"] += 1
                self._evento("reserva_expirada", "reserva", r["_id"], None, R_ATIVA, R_EXPIRADA)
                mesa = self.mesa(r["mesa"])
                self._notificar("reserva_expirada",
                                f"Reserva das {fmt_hora(r['data_hora'])} na mesa {r['mesa']} expirou "
                                "(no-show). Mesa disponível.", mesa["garcom"], r["mesa"], ref=r["_id"])

        # RN-10 / RN-21: sem confirmação → todos os garçons do pavimento
        for n in list(self.db.notificacoes.find({"confirmada": False, "escalonada": False,
                                                 "escalonar_apos": {"$ne": None, "$lte": momento}})):
            todos = self.garcons_do_pavimento(n["pavimento"]) if n.get("pavimento") else []
            self.db.notificacoes.update_one({"_id": n["_id"], "escalonada": False}, {"$set": {
                "destinatarios": sorted(set(todos) | set(n["destinatarios"])), "escalonada": True,
                "mensagem": "[Sem resposta] " + n["mensagem"]}})
            resultado["notificacoes_escalonadas"] += 1

        self.recalcular_fila()
        return resultado

    # ================================================================ Indicadores
    def resumo_ocupacao(self, pavimento: str | None = None) -> dict:
        mesas = self.listar_mesas(pavimento)
        cont = {k: 0 for k in ROTULO_MESA}
        for m in mesas:
            cont[m["status_exibicao"]] += 1
        cont["total"] = len(mesas)
        cont["alertas"] = sum(m["alerta"] for m in mesas)
        return cont
