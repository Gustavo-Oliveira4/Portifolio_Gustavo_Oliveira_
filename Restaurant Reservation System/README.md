# MesaFácil – Gestão de Reservas, Ocupação de Mesas e Acompanhamento de Pedidos

Sistema desenvolvido em **Python + Streamlit + MongoDB** para um restaurante com
**100 mesas** (70 no térreo e 30 no mezanino), **30 garçons** e **5 chefes**.
Ele implementa os requisitos de usuário (RU) e as regras de negócio (RN) do documento
*Requisitos_Sistema_Restaurante_ABNT*.

## 1. Como executar

### Opção A – Modo demonstração (sem instalar o MongoDB)
Os dados ficam em memória e o salão já começa movimentado (mesas ocupadas, pedidos e reservas).

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate    |    Linux/Mac: source .venv/bin/activate
pip install -r requirements.txt

# Windows (PowerShell)
$env:MONGO_URI="mongomock://"; streamlit run app.py
# Linux/Mac
MONGO_URI=mongomock:// streamlit run app.py
```

> No modo demonstração os dados são perdidos quando o servidor é encerrado.

### Opção B – Com MongoDB (persistente)
1. Suba o MongoDB: `docker compose up -d` (ou instale o MongoDB Community / use o MongoDB Atlas).
2. Instale as dependências: `pip install -r requirements.txt`
3. Execute: `streamlit run app.py`

Na primeira execução o sistema cria automaticamente as 100 mesas, os 35 funcionários e o cardápio.

| Variável     | Padrão                       | Descrição                                   |
|--------------|------------------------------|---------------------------------------------|
| `MONGO_URI`  | `mongodb://localhost:27017`  | Conexão (use `mongomock://` para demo)       |
| `MONGO_DB`   | `restaurante`                | Nome do banco                                |
| `DEMO`       | `1` em mongomock, `0` no Mongo | Gera o cenário de demonstração             |

Comandos úteis: `python -m core.seed --reset` (recria a carga inicial) e `python -m core.demo`
(gera o cenário de demonstração no MongoDB real).

## 2. Acessos

| Perfil   | Login                                   | Senha       |
|----------|-----------------------------------------|-------------|
| Garçom   | `G01` a `G21` (térreo), `G22` a `G30` (mezanino) | `garcom123` |
| Cozinha  | `C01` a `C05` (um por totem)            | `chef123`   |
| Cliente  | Qualquer CPF válido. No modo demo, `529.982.247-25` já está em uma mesa com pedido | – |

Dica: abra três abas do navegador (Cliente, Garçom e Cozinha) para ver a integração em tempo real.
As telas se atualizam automaticamente a cada 5 segundos.

## 3. Estrutura do projeto

```
restaurante/
├── app.py                # ponto de entrada (roteia para a visão de cada perfil)
├── core/
│   ├── config.py         # parâmetros das regras de negócio (tolerâncias, prazos, percentuais)
│   ├── database.py       # conexão com o MongoDB e índices
│   ├── services.py       # TODAS as regras de negócio (RN-01 a RN-26)
│   ├── seed.py           # carga inicial: mesas, setores, funcionários, cardápio
│   ├── demo.py           # cenário de demonstração
│   └── utils.py          # CPF, senhas (PBKDF2), formatação de datas
├── ui/
│   ├── login.py          # campos Funcionário e Cliente lado a lado
│   ├── cliente.py        # reserva por CPF e acompanhamento do pedido
│   ├── garcom.py         # mapa de mesas, notificações, atendimento, retiradas e reservas
│   ├── cozinha.py        # totem com a fila de preparo
│   ├── comum.py          # componentes compartilhados
│   └── estilo.py         # identidade visual (vermelho, laranja, amarelo e branco)
├── tests/                # 33 testes automatizados (regras de negócio + interface)
├── docker-compose.yml
└── requirements.txt
```

A interface **não contém regras de negócio**: ela apenas chama a camada `core/services.py`.
Assim, a mesma lógica poderia ser reaproveitada por uma API ou um aplicativo móvel.

## 4. Modelo de dados (MongoDB)

| Coleção        | Conteúdo principal |
|----------------|--------------------|
| `mesas`        | número, pavimento, capacidade, `reservavel` (cota RN-07), garçom do setor, status, atendimento atual |
| `funcionarios` | matrícula, nome, perfil (`garcom`/`cozinha`), pavimento, senha com hash |
| `reservas`     | CPF, nome, telefone, data/hora, turno, pessoas, mesa, status, origem (cliente/manual) |
| `atendimentos` | cada ocupação de mesa: início, primeiro atendimento (tempo de espera), fim |
| `pedidos`      | itens embutidos, status, histórico de status, chefe, prioridade, previsões de entrega |
| `cardapio`     | itens com tempo padrão de preparo |
| `notificacoes` | destinatários, tipo, confirmação e escalonamento |
| `eventos`      | trilha de auditoria (RN-26): toda mudança de estado com data, hora e usuário |

Os itens do pedido e o histórico ficam **embutidos** no documento do pedido, aproveitando o
modelo orientado a documentos: um pedido é lido e gravado de uma só vez.

## 5. Rastreabilidade: requisitos × implementação

| Requisito / Regra | Onde |
|---|---|
| RU-CLI-01..08 | `ui/cliente.py` + `Servico.criar_reserva/alterar_reserva/cancelar_reserva/acompanhamento_cliente/chamar_garcom` |
| RU-GAR-01..12 | `ui/garcom.py` + `Servico.listar_mesas/fazer_checkin/ocupar_sem_reserva/lancar_pedido/confirmar_retirada/liberar_mesa` |
| RU-COZ-01..08 | `ui/cozinha.py` + `Servico.fila_cozinha/iniciar_preparo/marcar_pronto/ajustar_tempo/priorizar` |
| RU-QLD-02 (≤ 5 s) | `st.fragment(run_every=5)` nas telas dinâmicas |
| RN-01 CPF | `utils.validar_cpf` |
| RN-02 uma reserva por turno | `Servico._validar_unica_por_turno` |
| RN-03 sem sobreposição | `Servico._mesa_disponivel` (permanência média de 120 min) |
| RN-04 menor ociosidade | `Servico.mesas_disponiveis` (ordena por capacidade) |
| RN-05 antecedência | `criar_reserva` / `_checar_prazo_alteracao` |
| RN-06 tolerância 15 min | `processar_rotinas` (expira e notifica o garçom) |
| RN-07 cota 20% | campo `reservavel` criado no `seed.py` |
| RN-08 alocação manual | `ocupar_sem_reserva` (CPF opcional) |
| RN-09 setorização | `seed._setores` |
| RN-10 / RN-21 escalonamento | `_notificar(escalonar_min)` + `processar_rotinas` |
| RN-11 / RN-12 espera e alerta | `registrar_atendimento`, `listar_mesas` (`alerta`) |
| RN-13 liberação | `liberar_mesa` → `confirmar_limpeza` |
| RN-14..RN-21 pedidos | `lancar_pedido`, `_avancar`, `recalcular_fila`, `cancelar_pedido`, `marcar_pronto` |
| RN-22..RN-25 acesso e privacidade | `autenticar`, CPF mascarado (`mascarar_cpf`), totens sem dados pessoais |
| RN-26 auditoria | `Servico._evento` → coleção `eventos` |

### Como o tempo esperado é calculado (RN-17)
Cada chefe é tratado como uma "estação" de preparo. Os pedidos são distribuídos, na ordem da
fila, para a primeira estação livre. A duração de um pedido é o maior tempo de preparo entre os
seus itens (eles são preparados em paralelo), somado a eventuais ajustes do chefe. Assim, com 5
chefes, os 5 primeiros pedidos começam na hora e o 6º espera a primeira estação liberar. A
previsão é recalculada a cada mudança de status.

## 6. Testes

```bash
pytest -q
```

Os testes usam `mongomock` e um relógio simulado para validar prazos (tolerância, escalonamento,
atraso) sem esperar o tempo real.

## 7. Limitações conhecidas (escopo acadêmico)
- Estados da mesa usam as cores sugeridas no documento (verde, azul, vermelho, amarelo e cinza);
  o restante da interface segue a paleta vermelho, laranja, amarelo e branco.
- As rotinas automáticas (expirar reservas e escalonar avisos) rodam a cada atualização das telas
  abertas. Em produção, recomenda-se um agendador dedicado (ex.: APScheduler ou cron).
- Não há módulo de pagamento nem de cadastro de cardápio/funcionários pela interface.
