-- Execute no MySQL/MariaDB do TechTrade (uma vez) para avisos ao comprador após confirmação do pedido.
-- Se a tabela não existir, o sistema continua funcionando; apenas não grava notificações persistidas.

CREATE TABLE IF NOT EXISTS notificacoes_cliente_tt (
    id_notificacao INT AUTO_INCREMENT PRIMARY KEY,
    id_cliente INT NOT NULL,
    id_compra INT NULL,
    mensagem TEXT NOT NULL,
    data_envio DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    lida TINYINT(1) NOT NULL DEFAULT 0,
    INDEX idx_cliente_lida (id_cliente, lida),
    INDEX idx_compra (id_compra)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
