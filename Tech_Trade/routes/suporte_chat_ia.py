"""Chat de suporte com respostas via OpenAI quando OPENAI_API_KEY está definida."""
import json
import os
import unicodedata
import urllib.error
import urllib.request
from typing import Any

from dotenv import load_dotenv
from flask import jsonify, request

load_dotenv()

try:
    from .produto import rotas_produto
except ImportError:
    from produto import rotas_produto

_OPENAI_URL = "https://api.openai.com/v1/chat/completions"

_SYSTEM_PROMPT = """Você é o assistente virtual da TechTrade, marketplace brasileiro de eletrônicos.
Responda sempre em português do Brasil, de forma clara, cordial e objetiva. Use passos numerados quando explicar processos.

Informações oficiais do site:
- Como comprar: (1) fazer login; (2) ir em Produtos; (3) escolher item e Comprar; (4) preencher endereço no checkout; (5) escolher Pix (10% desconto), cartão ou boleto; (6) finalizar. Com Pix, o cliente vê um QR Code simulado na tela, paga no app do banco e clica em "Já realizei o pagamento".
- Ver pedidos: menu "Meus Pedidos" (usuário logado) — status, pagamento e entrega.
- Pagamentos: Pix (10% off), cartão de crédito e boleto; ambiente seguro.
- Entregas: todo o Brasil; prazos variam — não invente datas exatas.
- Garantia/devolução: política da loja; casos específicos → suporte humano.
- Contato: suporte@techtrade.com; telefone (11) 96358-6157; chat no site seg–sex 8h–18h; seção Ajuda na home.
- Login/conta: tela Login; recuperar senha em "Esqueci minha senha"; perfil em Minha Conta.
- Endereço: USCS, São Caetano do Sul (SP).

Regras:
- Não invente números de pedido, status de entrega ou dados de contas.
- Sem acesso a pedidos específicos: oriente Meus Pedidos ou e-mail com número do pedido.
- Você é assistente automatizado, não humano."""


def _normalize(text: str) -> str:
    t = text.lower()
    return "".join(c for c in unicodedata.normalize("NFD", t) if unicodedata.category(c) != "Mn")


def _fallback_reply(user_text: str) -> str:
    n = _normalize(user_text)

    if any(k in n for k in ("compra", "comprar", "checkout", "carrinho")):
        return (
            "Para comprar na TechTrade:\n"
            "1) Faça login na sua conta.\n"
            "2) Acesse Produtos e escolha o item.\n"
            "3) Clique em Comprar e preencha o endereço no checkout.\n"
            "4) Escolha Pix (10% de desconto), cartão ou boleto.\n"
            "5) Com Pix, escaneie o QR Code na tela e confirme com \"Já realizei o pagamento\"."
        )
    if any(k in n for k in ("pedido", "rastre", "status", "verificar", "acompanh")):
        return (
            "Para ver seus pedidos: entre logado e abra Meus Pedidos no menu.\n"
            "Lá você consulta status, pagamento e entrega. Para um pedido específico, envie o número para "
            "suporte@techtrade.com ou ligue (11) 96358-6157."
        )
    if any(k in n for k in ("pagamento", "cartao", "cartão", "pix", "boleto", "pagar")):
        return (
            "Aceitamos Pix (10% off no checkout), cartão e boleto.\n"
            "No Pix, exibimos QR Code e código copia e cola; após pagar no banco, clique em "
            "\"Já realizei o pagamento\". Dúvidas na cobrança: suporte@techtrade.com com comprovante."
        )
    if any(k in n for k in ("contato", "falar", "telefone", "email", "suporte", "whatsapp")):
        return (
            "Canais de contato:\n"
            "• E-mail: suporte@techtrade.com\n"
            "• Telefone: (11) 96358-6157\n"
            "• Chat no site (seg–sex, 8h–18h)\n"
            "• Seção Ajuda na página inicial"
        )
    if any(k in n for k in ("login", "conta", "cadastr", "senha", "perfil")):
        return (
            "Use Login no topo do site. Esqueceu a senha? Clique em \"Esqueci minha senha\".\n"
            "Depois de logado: Minha Conta (dados) e Meus Pedidos (compras)."
        )
    if "entrega" in n or "frete" in n:
        return (
            "Entregamos para todo o Brasil; o prazo varia por região e transportadora. "
            "Acompanhe em Meus Pedidos ou envie o número do pedido para suporte@techtrade.com."
        )
    if any(k in n for k in ("garantia", "troca", "devolu")):
        return (
            "Há política de garantia e devolução. Para abrir solicitação, informe o número do pedido em "
            "suporte@techtrade.com ou (11) 96358-6157."
        )
    if any(k in n for k in ("produto", "preco", "preço", "catalogo", "catálogo")):
        return (
            "Navegue em Produtos no menu. Use busca e filtros por categoria. "
            "Itens verificados pela administradora estão liberados para compra com documentação fiscal conferida."
        )
    if "horario" in n or "horário" in n or "atendimento" in n:
        return (
            "Atendimento humano: segunda a sexta, 8h às 18h. "
            "Fora desse horário, use este chat ou suporte@techtrade.com."
        )
    return (
        "Posso ajudar com: como comprar, ver pedidos, pagamentos, entregas, garantia e contato.\n"
        "Ex.: \"Como compro um produto?\" ou \"Como ver meu pedido?\".\n"
        "Atendimento humano: suporte@techtrade.com ou (11) 96358-6157."
    )


def _sanitize_history(raw: Any, max_turns: int = 12) -> list[dict[str, str]]:
    if not isinstance(raw, list):
        return []
    out: list[dict[str, str]] = []
    for item in raw[-max_turns:]:
        if not isinstance(item, dict):
            continue
        role = item.get("role")
        content = (item.get("content") or "").strip()
        if role in ("user", "assistant") and content:
            out.append({"role": role, "content": content[:4000]})
    return out


def _openai_reply(user_message: str, history: list[dict[str, str]], api_key: str) -> str:
    model = (os.environ.get("OPENAI_CHAT_MODEL") or "gpt-4o-mini").strip()
    messages = [{"role": "system", "content": _SYSTEM_PROMPT}]
    messages.extend(history)
    messages.append({"role": "user", "content": user_message})

    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": 600,
        "temperature": 0.65,
    }
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        _OPENAI_URL,
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"OpenAI HTTP {e.code}: {err_body[:500]}") from e

    try:
        return (data["choices"][0]["message"]["content"] or "").strip()
    except (KeyError, IndexError, TypeError) as e:
        raise RuntimeError("Resposta inesperada da API.") from e


@rotas_produto.post("/techtrade/chat_suporte")
def chat_suporte_ia():
    data = request.get_json(silent=True) or {}
    message = (data.get("message") or "").strip()
    if not message:
        return jsonify({"erro": "Envie uma mensagem."}), 400
    if len(message) > 2000:
        return jsonify({"erro": "Mensagem muito longa."}), 400

    history = _sanitize_history(data.get("history"))

    api_key = (os.environ.get("OPENAI_API_KEY") or "").strip()
    if api_key:
        try:
            reply = _openai_reply(message, history, api_key)
            if not reply:
                reply = _fallback_reply(message)
            return jsonify({"reply": reply, "provider": "openai"})
        except Exception:
            reply = _fallback_reply(message)
            return jsonify(
                {
                    "reply": reply,
                    "provider": "fallback",
                    "aviso": "Não foi possível contatar a IA no momento; resposta automática simplificada.",
                }
            )

    reply = _fallback_reply(message)
    return jsonify(
        {
            "reply": reply,
            "provider": "fallback",
            "aviso": "Configure a variável de ambiente OPENAI_API_KEY para ativar respostas com IA.",
        }
    )