-- Colunas de verificação: permitir NULL em produtos novos (pendentes).
-- Execute uma vez se INSERT falhar com "cannot be null" em verificado_em.
-- Ex.: USE tech_trade_db; SOURCE 003_produtos_verificacao_nullable.sql;

ALTER TABLE produtos_tt
  MODIFY COLUMN verificado TINYINT(1) NOT NULL DEFAULT 0,
  MODIFY COLUMN verificado_por VARCHAR(100) NULL DEFAULT NULL,
  MODIFY COLUMN verificado_em DATETIME NULL DEFAULT NULL,
  MODIFY COLUMN verificacao_obs TEXT NULL DEFAULT NULL;
