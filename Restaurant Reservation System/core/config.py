"""Configurações e parâmetros de negócio do sistema.

Todos os valores numéricos das regras de negócio ficam centralizados aqui
para que possam ser ajustados pela gestão sem alterar o código (Seção 5).
Qualquer valor pode ser sobrescrito por variável de ambiente.
"""
import os


def _int(nome: str, padrao: int) -> int:
    try:
        return int(os.getenv(nome, padrao))
    except ValueError:
        return padrao


# ---------------------------------------------------------------- Banco de dados
# Use "mongomock://" para rodar em memória (modo demonstração, sem MongoDB).
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB = os.getenv("MONGO_DB", "restaurante")

# ---------------------------------------------------------------- Estrutura física
MESAS_TERREO = 70
MESAS_MEZANINO = 30
GARCONS_TERREO = 21          # 70 mesas / 21 garçons ≈ 3,3 mesas por garçom
GARCONS_MEZANINO = 9         # 30 mesas /  9 garçons ≈ 3,3 mesas por garçom
TOTAL_CHEFES = 5

# ---------------------------------------------------------------- Regras de negócio
DURACAO_PERMANENCIA_MIN = _int("DURACAO_PERMANENCIA_MIN", 120)   # RN-03
ANTECEDENCIA_MIN_RESERVA = _int("ANTECEDENCIA_MIN_RESERVA", 60)  # RN-05
TOLERANCIA_ATRASO_MIN = _int("TOLERANCIA_ATRASO_MIN", 15)        # RN-06
PERCENTUAL_SEM_RESERVA = _int("PERCENTUAL_SEM_RESERVA", 20)      # RN-07
TIMEOUT_NOTIFICACAO_MIN = _int("TIMEOUT_NOTIFICACAO_MIN", 3)     # RN-10
ALERTA_NAO_ATENDIDA_MIN = _int("ALERTA_NAO_ATENDIDA_MIN", 5)     # RN-12
TIMEOUT_RETIRADA_MIN = _int("TIMEOUT_RETIRADA_MIN", 2)           # RN-21
JANELA_EXIBIR_RESERVADA_MIN = _int("JANELA_EXIBIR_RESERVADA_MIN", 60)
HORA_INICIO_JANTAR = 16      # define o turno (RN-02): antes = almoço, depois = jantar
HORARIO_ABERTURA = 11
HORARIO_FECHAMENTO = 23

# ---------------------------------------------------------------- Interface
INTERVALO_ATUALIZACAO_S = 5  # RU-QLD-02: atualização em até 5 segundos
