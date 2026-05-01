-- Opcional: alinhar o BD ao fluxo completo (coluna chave NF-e, código de rastreio, status "aguardando_aprovacao").
-- Só execute se quiser essas colunas; o app já funciona sem elas (usa pendente + marca em observacoes).

-- ALTER TABLE produtos_tt ADD COLUMN chave_nfe VARCHAR(44) NULL;
-- ALTER TABLE compras_tt ADD COLUMN codigo_rastreio VARCHAR(32) NULL;
-- CREATE UNIQUE INDEX idx_compras_codigo_rastreio ON compras_tt (codigo_rastreio);

-- Incluir novo valor no ENUM de status (liste todos os valores que o campo deve aceitar):
-- ALTER TABLE compras_tt MODIFY COLUMN status ENUM(
--   'pendente',
--   'aguardando_aprovacao',
--   'processando',
--   'enviado',
--   'entregue',
--   'cancelado'
-- ) DEFAULT 'pendente';
