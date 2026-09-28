"""Site com chatbot assistente geral (Flask + Anthropic).

Rodar localmente:
    pip install -r requirements.txt
    export ANTHROPIC_API_KEY="sua-chave"    # Windows: set ANTHROPIC_API_KEY=sua-chave
    python app.py                            # abra http://localhost:5000

Em produção use um servidor WSGI, ex.: gunicorn app:app
"""

import os

import anthropic
from flask import Flask, jsonify, request

MODELO = "claude-sonnet-5"
SISTEMA = (
    "Você é o Polar, um urso polar simpático, calorosinho e bem-humorado que atua "
    "como assistente geral. Use de vez em quando, com leveza, referências a gelo, "
    "neve e ao Ártico (e um emoji ocasional como ❄️), sem atrapalhar a utilidade. "
    "As respostas continuam sempre corretas, claras e diretas. "
    "Responda no idioma do usuário (padrão: português do Brasil), em texto simples."
)
MAX_MENSAGENS = 30
MAX_CARACTERES = 4000

app = Flask(__name__)
cliente = anthropic.Anthropic()  # lê ANTHROPIC_API_KEY do ambiente

PAGINA = """<!DOCTYPE html>
<html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Polar</title>
<style>
*{box-sizing:border-box}
body{margin:0;height:100dvh;display:flex;flex-direction:column;background:#faf9f7;color:#1f1e1c;font:16px/1.5 system-ui,sans-serif}
header{padding:12px 16px;border-bottom:1px solid #e6e3de;font-weight:600;display:flex;justify-content:space-between}
header button{background:none;border:1px solid #ddd;border-radius:8px;padding:4px 10px;color:#777;cursor:pointer}
#log{flex:1;overflow-y:auto;padding:16px;display:flex;flex-direction:column;gap:10px;max-width:800px;width:100%;margin:0 auto}
.m{max-width:85%;padding:10px 14px;border-radius:16px;white-space:pre-wrap;word-wrap:break-word}
.u{align-self:flex-end;background:#3b82c4;color:#fff;border-bottom-right-radius:4px}
.b{align-self:flex-start;background:#fff;border:1px solid #e6e3de;border-bottom-left-radius:4px}
.e{color:#c0392b}
form{display:flex;gap:8px;padding:12px;border-top:1px solid #e6e3de;max-width:800px;width:100%;margin:0 auto}
textarea{flex:1;resize:none;border:1px solid #ddd;border-radius:12px;padding:10px 12px;font:inherit}
button.env{background:#3b82c4;color:#fff;border:0;border-radius:12px;padding:0 18px;font-weight:600;cursor:pointer}
button.env:disabled{opacity:.5}
</style></head><body>
<header><span>&#128059;&#8205;&#10052;&#65039; Polar</span><button id="limpar" type="button">Limpar</button></header>
<div id="log"><div class="m b">Oi, eu sou o Polar, o urso polar mais prestativo do Ártico! ❄️ Como posso ajudar?</div></div>
<form id="f"><textarea id="t" rows="1" placeholder="Converse com o Polar" autofocus></textarea>
<button class="env" id="s">Enviar</button></form>
<script>
const log=document.getElementById("log"),t=document.getElementById("t"),s=document.getElementById("s");
let hist=[];
function add(c,x){const d=document.createElement("div");d.className="m "+c;d.textContent=x;log.appendChild(d);log.scrollTop=log.scrollHeight;return d}
document.getElementById("f").onsubmit=async e=>{
  e.preventDefault();const txt=t.value.trim();if(!txt||s.disabled)return;
  add("u",txt);t.value="";hist.push({role:"user",content:txt});
  s.disabled=true;const out=add("b","...");
  try{
    const r=await fetch("/chat",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({mensagens:hist})});
    const j=await r.json();
    if(!r.ok)throw new Error(j.erro||"Erro");
    out.textContent=j.resposta;hist.push({role:"assistant",content:j.resposta});
  }catch(err){hist.pop();out.classList.add("e");out.textContent="Não consegui responder agora. Tente novamente."}
  s.disabled=false;t.focus();
};
t.addEventListener("keydown",e=>{if(e.key==="Enter"&&!e.shiftKey){e.preventDefault();document.getElementById("f").requestSubmit()}});
document.getElementById("limpar").onclick=()=>{hist=[];log.innerHTML='<div class="m b">Novo gelo, nova conversa! ❄️ Pode falar.</div>'};
</script></body></html>"""


@app.get("/")
def inicio():
    return PAGINA


@app.post("/chat")
def chat():
    dados = request.get_json(silent=True) or {}
    mensagens = dados.get("mensagens")
    if not isinstance(mensagens, list) or not mensagens:
        return jsonify(erro="Mensagens inválidas."), 400

    limpas = []
    for m in mensagens[-MAX_MENSAGENS:]:
        if (
            isinstance(m, dict)
            and m.get("role") in ("user", "assistant")
            and isinstance(m.get("content"), str)
            and m["content"].strip()
        ):
            limpas.append({"role": m["role"], "content": m["content"][:MAX_CARACTERES]})
    while limpas and limpas[0]["role"] != "user":
        limpas.pop(0)
    if not limpas or limpas[-1]["role"] != "user":
        return jsonify(erro="Mensagens inválidas."), 400

    try:
        resposta = cliente.messages.create(
            model=MODELO, max_tokens=1024, system=SISTEMA, messages=limpas
        )
        return jsonify(resposta=resposta.content[0].text)
    except anthropic.APIError:
        return jsonify(erro="Falha ao consultar a IA."), 502


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
