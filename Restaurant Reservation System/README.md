<div align="center">

# 🍽️ MesaFácil

### Sistema de Gestão de Reservas, Ocupação de Mesas e Acompanhamento de Pedidos

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?logo=streamlit&logoColor=white)
![MongoDB](https://img.shields.io/badge/MongoDB-NoSQL-47A248?logo=mongodb&logoColor=white)
![Testes](https://img.shields.io/badge/testes-33%20aprovados-2E7D32)
![Status](https://img.shields.io/badge/status-acad%C3%AAmico-F57C00)

Projeto acadêmico do curso de **Engenharia de Computação** que integra cliente, salão e cozinha
de um restaurante em tempo real.

[Sobre](#-sobre-o-projeto) •
[Funcionalidades](#-funcionalidades) •
[Tecnologias](#-tecnologias) •
[Como executar](#-como-executar) •
[Arquitetura](#-arquitetura) •
[Testes](#-testes) •
[Autor](#-autor)

</div>

---

## 📌 Sobre o projeto

Em restaurantes de grande porte, os horários de pico revelam problemas recorrentes de coordenação:
a equipe não sabe quais mesas estão livres, clientes aguardam sem atendimento e pratos prontos esfriam
no balcão por falta de aviso ao garçom.

O **MesaFácil** foi desenvolvido para um restaurante com **100 mesas** (70 no térreo e 30 no mezanino),
**30 garçons** e **5 chefes de cozinha**. O sistema oferece três visões integradas:

| Perfil | Papel no sistema |
|---|---|
| 👤 **Cliente** | Reserva mesa pelo CPF e acompanha seus pedidos com tempo estimado de entrega |
| 🧑‍🍳 **Garçom** | Gerencia ocupação, recebe notificações, lança pedidos e faz reservas manuais |
| 🔥 **Cozinha** | Totens com a fila de preparo, tempo esperado e chamada do garçom para retirada |

O projeto implementa os requisitos de usuário e as regras de negócio especificados no documento
acadêmico *Sistema de Gestão de Reservas, Ocupação de Mesas e Acompanhamento de Pedidos para Restaurantes*.

---

## ✨ Funcionalidades

### 👤 Cliente
- Acesso apenas com CPF, sem cadastro de senha
- Reserva com escolha de data, horário, número de pessoas e ambiente (térreo ou mezanino)
- Alteração e cancelamento de reservas
- Acompanhamento do pedido com barra de etapas e previsão de entrega atualizada automaticamente
- Botão para chamar o garçom

### 🧑‍🍳 Garçom
- Mapa das 100 mesas com status por cor e alerta visual para mesas aguardando atendimento
- Notificações de entrada, saída, pedido pronto, chamado do cliente e reserva expirada
- Check-in de reservas e acomodação de clientes sem agendamento
- Lançamento de pedidos com observações, enviados direto aos totens da cozinha
- Confirmação de retirada e entrega, liberação e higienização da mesa
- Reservas manuais para atendimento por telefone ou balcão

### 🔥 Cozinha
- Fila de pedidos ordenada por prioridade, agrupada por mesa e por ordem de chegada
- Tempo decorrido, previsão de entrega e destaque para pedidos atrasados
- Início de preparo, marcação de pedido pronto e chamada automática do garçom
- Ajuste de tempo esperado e priorização de pedidos, ambos com justificativa obrigatória

### 🎨 Estados da mesa

| Cor | Estado |
|---|---|
| 🟢 Verde | Livre |
| 🔵 Azul | Reservada |
| 🔴 Vermelho | Ocupada – não atendida |
| 🟡 Amarelo | Ocupada – atendida |
| ⚪ Cinza | Em liberação (higienização) |

---

## 🛠️ Tecnologias

| Tecnologia | Uso |
|---|---|
| **Python 3.10+** | Linguagem principal |
| **Streamlit** | Interface web com atualização automática |
| **MongoDB** | Banco de dados não relacional orientado a documentos |
| **PyMongo** | Driver de conexão com o MongoDB |
| **mongomock** | Banco em memória para modo demonstração e testes |
| **Pandas** | Exibição de tabelas |
| **Pytest** | Testes automatizados |
| **Docker Compose** | Execução do MongoDB local |

---

## 🚀 Como executar

### Pré-requisitos
- [Python 3.10 ou superior](https://www.python.org/downloads/)
- [Git](https://git-scm.com/)
- (Opcional) [Docker](https://www.docker.com/) para usar o MongoDB real

### 1. Clonar o repositório
```bash
git clone https://github.com/SEU-USUARIO/mesafacil.git
cd mesafacil
```

### 2. Criar e ativar o ambiente virtual
```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux / macOS
source .venv/bin/activate
```

### 3. Instalar as dependências
```bash
pip install -r requirements.txt
```

### 4. Executar

**Modo demonstração** (sem MongoDB, dados em memória e salão já movimentado):
```bash
# Windows (PowerShell)
$env:MONGO_URI="mongomock://"; streamlit run app.py

# Linux / macOS
MONGO_URI=mongomock:// streamlit run app.py
```

**Com MongoDB** (dados persistentes):
```bash
docker compose up -d
streamlit run app.py
```

Acesse **http://localhost:8501** no navegador.

### 🔑 Acessos de demonstração

| Perfil | Login | Senha |
|---|---|---|
| Garçom | `G01` a `G21` (térreo) · `G22` a `G30` (mezanino) | `garcom123` |
| Cozinha | `C01` a `C05` | `chef123` |
| Cliente | Qualquer CPF válido · `529.982.247-25` já possui mesa com pedido no modo demonstração | — |

> 💡 Abra três abas do navegador, uma para cada perfil, para ver a integração em tempo real.

### ⚙️ Variáveis de ambiente

| Variável | Padrão | Descrição |
|---|---|---|
| `MONGO_URI` | `mongodb://localhost:27017` | Conexão com o banco (`mongomock://` para demonstração) |
| `MONGO_DB` | `restaurante` | Nome do banco de dados |
| `DEMO` | `1` em mongomock, `0` no MongoDB | Gera o cenário de demonstração |

---

## 🏗️ Arquitetura

O sistema segue uma **arquitetura em camadas**: a interface não contém regras de negócio, apenas chama
a camada de serviços. Assim, a mesma lógica poderia ser reutilizada por uma API ou um aplicativo móvel.

```
┌─────────────────────────────────────────────┐
│     Interface (Streamlit)  ·  ui/            │
│   Cliente  ·  Garçom  ·  Cozinha  ·  Login   │
└───────────────────────┬─────────────────────┘
                        │
┌───────────────────────▼─────────────────────┐
│  Serviços / Regras de negócio · core/        │
│  services.py  (RN-01 a RN-26)                │
└───────────────────────┬─────────────────────┘
                        │
┌───────────────────────▼─────────────────────┐
│          MongoDB  (8 coleções)              │
└─────────────────────────────────────────────┘
```

### 📁 Estrutura de pastas
```
mesafacil/
├── app.py                 # Ponto de entrada
├── requirements.txt
├── docker-compose.yml
├── .streamlit/
│   └── config.toml        # Tema visual
├── core/
│   ├── config.py          # Parâmetros das regras de negócio
│   ├── database.py        # Conexão e índices do MongoDB
│   ├── services.py        # Regras de negócio
│   ├── seed.py            # Carga inicial (mesas, funcionários, cardápio)
│   ├── demo.py            # Cenário de demonstração
│   └── utils.py           # CPF, senhas e formatação
├── ui/
│   ├── login.py           # Tela inicial (Funcionário | Cliente)
│   ├── cliente.py
│   ├── garcom.py
│   ├── cozinha.py
│   ├── comum.py
│   └── estilo.py          # Identidade visual
└── tests/
    ├── test_regras.py     # Testes das regras de negócio
    └── test_interface.py  # Testes da interface
```

### 🗄️ Modelo de dados (MongoDB)

| Coleção | Conteúdo |
|---|---|
| `mesas` | Número, pavimento, capacidade, garçom do setor e status |
| `funcionarios` | Matrícula, perfil, pavimento e senha com hash |
| `reservas` | CPF, data/hora, turno, pessoas, mesa e status |
| `atendimentos` | Cada ocupação de mesa, com tempo de espera até o primeiro atendimento |
| `pedidos` | Itens e histórico embutidos, status, chefe responsável e previsões |
| `cardapio` | Itens com tempo padrão de preparo |
| `notificacoes` | Avisos aos garçons, com confirmação e escalonamento |
| `eventos` | Trilha de auditoria de todas as mudanças de estado |

---

## 📋 Principais regras de negócio

| Regra | Descrição |
|---|---|
| **Validação de CPF** | Verificação dos dígitos verificadores |
| **Reserva única** | Uma reserva ativa por CPF, data e turno |
| **Sem sobreposição** | Considera tempo médio de permanência de 120 minutos |
| **Alocação inteligente** | Escolhe a mesa com menor capacidade ociosa |
| **Antecedência** | Reservas, alterações e cancelamentos com no mínimo 60 minutos |
| **Tolerância de atraso** | Reserva expira 15 minutos após o horário (no-show) |
| **Mesas sem agendamento** | 20% das mesas reservadas a clientes sem reserva |
| **Alerta de espera** | Mesa sem atendimento por mais de 5 minutos é destacada |
| **Escalonamento** | Avisos sem resposta são enviados a todos os garçons do pavimento |
| **Tempo de preparo** | Simulação de 5 estações paralelas (uma por chefe) |
| **Privacidade (LGPD)** | CPF mascarado nas telas internas; cozinha sem acesso a dados pessoais |
| **Auditoria** | Toda mudança registrada com data, hora e usuário |

> Todos os valores (tolerâncias, prazos e percentuais) são configuráveis em `core/config.py`.

---

## 🧪 Testes

O projeto possui **33 testes automatizados**, cobrindo regras de negócio e interface. Os testes usam
banco em memória e um relógio simulado para validar prazos sem esperar o tempo real.

```bash
pytest -q
```

---

## 🔮 Melhorias futuras

- [ ] Agendador dedicado para rotinas automáticas (expiração de reservas e escalonamento de avisos)
- [ ] Cadastro de cardápio e funcionários pela interface
- [ ] Painel gerencial com indicadores (giro de mesas, tempo médio de espera, taxa de no-show)
- [ ] API REST para integração com aplicativo móvel
- [ ] Módulo de pagamento e fechamento de conta

---

## 👨‍💻 Autor

**Gustavo de Oliveira**
Estudante de Engenharia de Computação

[![LinkedIn](https://img.shields.io/badge/LinkedIn-0A66C2?logo=linkedin&logoColor=white)](https://www.linkedin.com/in/SEU-PERFIL)
[![GitHub](https://img.shields.io/badge/GitHub-181717?logo=github&logoColor=white)](https://github.com/SEU-USUARIO)

---

<div align="center">

Projeto desenvolvido para fins acadêmicos.

</div>
