// Índices do banco "restaurante" (os mesmos criados pelo core/database.py)
// Uso: mongosh "mongodb://localhost:27017/restaurante" criar_indices.js
db.mesas.createIndex({ numero: 1 }, { unique: true });
db.mesas.createIndex({ pavimento: 1, status: 1 });
db.funcionarios.createIndex({ matricula: 1 }, { unique: true });
db.reservas.createIndex({ cpf: 1, status: 1 });
db.reservas.createIndex({ mesa: 1, data_hora: 1 });
db.atendimentos.createIndex({ mesa: 1, fim: 1 });
db.pedidos.createIndex({ status: 1, lancado_em: 1 });
db.pedidos.createIndex({ atendimento_id: 1 });
db.notificacoes.createIndex({ destinatarios: 1, confirmada: 1 });
db.eventos.createIndex({ em: -1 });
print("Índices criados com sucesso.");
