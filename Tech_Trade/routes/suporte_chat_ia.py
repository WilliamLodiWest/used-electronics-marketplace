"""Chat de suporte com respostas via OpenAI quando OPENAI_API_KEY está definida."""
import json
import os
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
Responda sempre em português do Brasil, de forma clara, cordial e objetiva (2 a 6 frases na maioria dos casos).

Informações oficiais do site (use quando fizer sentido):
- Missão: conectar clientes a tecnologia com preços justos; vendedores verificados.
- Entregas para todo o Brasil; prazos dependem da transportadora e da região — não invente prazos exatos.
- Pagamentos: cartão, Pix e boleto; transações protegidas.
- Garantia e devolução: existe política da loja; para casos específicos oriente o cliente a falar com o suporte.
- Suporte humano: e-mail suporte@techtrade.com; telefone (11) 4004-1234; chat no site seg–sex 8h–18h.
- Endereço institucional: USCS, São Caetano do Sul (SP).
- Para comprar, o cliente costuma precisar estar logado na conta.

Regras:
- Não invente números de pedido, status de entrega ou dados de contas.
- Se o usuário pedir status de um pedido específico que você não tem, diga que não tem acesso aos sistemas internos e que ele pode usar a área do cliente ou escrever para suporte@techtrade.com com o número do pedido.
- Não finja ser humano; você é um assistente automatizado da TechTrade."""


def _fallback_reply(user_text: str) -> str:
    normalized = user_text.lower()
    if "entrega" in normalized or "frete" in normalized or "rastre" in normalized:
        return (
            "Fazemos entregas para todo o Brasil. O prazo varia conforme a região e a transportadora. "
            "Para rastrear um pedido, use sua área logada no site ou envie o número do pedido para "
            "suporte@techtrade.com."
        )
    if "pagamento" in normalized or "cartão" in normalized or "cartao" in normalized or "pix" in normalized or "boleto" in normalized:
        return (
            "Aceitamos cartão, Pix e boleto. Os pagamentos são processados com segurança. "
            "Se alguma cobrança parecer incorreta, fale com suporte@techtrade.com com o comprovante."
        )
    if "garantia" in normalized or "troca" in normalized or "devolu" in normalized:
        return (
            "Nossos produtos seguem política de garantia e devolução da TechTrade. "
            "Para abrir solicitação com seu pedido em mãos, use o suporte por e-mail ou telefone (11) 4004-1234."
        )
    if "produto" in normalized or "preço" in normalized or "preco" in normalized:
        return (
            "Você pode navegar em Produtos na TechTrade e filtrar por categoria ou busca. "
            "Se quiser algo específico, diga categoria e faixa de preço que te oriento nos próximos passos."
        )
    if "horário" in normalized or "horario" in normalized or "atendimento" in normalized:
        return (
            "O chat humano no site funciona de segunda a sexta, das 8h às 18h. "
            "Fora desse horário você pode usar este assistente ou o e-mail suporte@techtrade.com."
        )
    return (
        "Obrigado pela mensagem! Posso ajudar com entregas, pagamentos, garantia, produtos ou uso do site. "
        "Se precisar de algo muito específico (ex.: um pedido seu), envie os detalhes para suporte@techtrade.com."
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