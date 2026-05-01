-- TechTrade: rastreio de pedidos, verificação NF-e e fluxo de aprovação administrativa.
-- Execute uma vez no MySQL do projeto (ex.: USE tech_trade_db; source este arquivo).

ALTER TABLE produtos_tt
  ADD COLUMN chave_nfe VARCHAR(44) NULL COMMENT 'Chave NF-e 44 digitos — consulta portal nacional';

ALTER TABLE compras_tt
  ADD COLUMN codigo_rastreio VARCHAR(32) NULL COMMENT 'Codigo publico de rastreio';

CREATE UNIQUE INDEX idx_compras_codigo_rastreio ON compras_tt (codigo_rastreio);
