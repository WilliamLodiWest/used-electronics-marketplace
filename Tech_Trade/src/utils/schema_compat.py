"""Detecção de colunas / ENUM no MySQL para o app funcionar com BD legado e com migrações novas."""

import re
from typing import Optional, Set

_CACHE: dict = {}

TAG_AGUARDA_APROVACAO = "[TECHTRADE_AGUARDA_APROVACAO]"


def _cache_get(key):
    return _CACHE.get(key)


def _cache_set(key, val):
    _CACHE[key] = val


def table_has_column(conexao, table: str, column: str) -> bool:
    key = ("col", table.lower(), column.lower())
    hit = _cache_get(key)
    if hit is not None:
        return hit
    rows = conexao.select(
        """
        SELECT 1 FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s AND COLUMN_NAME = %s
        LIMIT 1
        """,
        (table, column),
    )
    ok = bool(rows)
    _cache_set(key, ok)
    return ok


def column_allows_null(conexao, table: str, column: str) -> bool:
    """True se a coluna aceita NULL (information_schema)."""
    key = ("nullable", table.lower(), column.lower())
    hit = _cache_get(key)
    if hit is not None:
        return hit
    rows = conexao.select(
        """
        SELECT IS_NULLABLE FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s AND COLUMN_NAME = %s
        LIMIT 1
        """,
        (table, column),
    )
    ok = bool(rows and str(rows[0][0]).upper() == "YES")
    _cache_set(key, ok)
    return ok


def compras_status_enum_values(conexao) -> Optional[Set[str]]:
    """Retorna os valores do ENUM de compras_tt.status, ou None se não for ENUM."""
    key = ("compras_status_enum",)
    hit = _cache_get(key)
    if hit is not None:
        return hit
    rows = conexao.select(
        """
        SELECT COLUMN_TYPE FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s AND COLUMN_NAME = %s
        LIMIT 1
        """,
        ("compras_tt", "status"),
    )
    if not rows or not rows[0] or not rows[0][0]:
        _cache_set(key, None)
        return None
    col_type = str(rows[0][0])
    if not col_type.upper().startswith("ENUM"):
        _cache_set(key, None)
        return None
    vals = set(re.findall(r"'([^']*)'", col_type))
    _cache_set(key, vals)
    return vals


def pedido_aguarda_aprovacao_admin(status, observacoes, codigo_rastreio_db) -> bool:
    """Pedido criado pelo fluxo novo (estoque só após aprovar), e não legado pendente."""
    s = (status or "").strip().lower()
    if s == "aguardando_aprovacao":
        return True
    obs = observacoes or ""
    if TAG_AGUARDA_APROVACAO in obs and "|COD:" in obs:
        return True
    cr = (codigo_rastreio_db or "").strip()
    if s == "pendente" and cr.upper().startswith("TT-"):
        return True
    return False


def embutir_codigo_em_observacoes(codigo_rastreio: str, observacoes_usuario: str) -> str:
    prefix = f"{TAG_AGUARDA_APROVACAO}|COD:{codigo_rastreio}|"
    rest = (observacoes_usuario or "").strip()
    if rest:
        return prefix + "\n" + rest
    return prefix


def extrair_codigo_rastreio_obs(observacoes: str) -> str:
    m = re.search(r"\|COD:(TT-[A-Za-z0-9]+)\|", observacoes or "")
    return m.group(1) if m else ""


def status_pedido_label(status: str) -> str:
    """Rótulo amigável alinhado à linha do tempo do cliente."""
    s = (status or "").strip().lower()
    labels = {
        "aguardando_aprovacao": "Aguardando aprovação",
        "pendente": "Aguardando aprovação",
        "pago": "Aprovado — em preparação",
        "processando": "Aprovado — em preparação",
        "enviado": "Despachado / em transporte",
        "entregue": "Entregue",
        "cancelado": "Cancelado",
    }
    return labels.get(s, (status or "").replace("_", " ").title())
