"""Section 4: Gradio user interface. Presentation only: all logic lives in `service.Service`.

Layout: chat (history of the last 3 rounds lives in the browser session via gr.State), answer language, collapsible
sources under every answer, and a collapsed "under the hood" area (search mode, rewritten query, top hits with scores).
"""
from __future__ import annotations

import logging
import os

import gradio as gr

from .generate import Turn
from .service import Reply, Service, example_reply, load_examples

log = logging.getLogger("regulatory_helper")

# --------------------------------------------------------------------------
# texts (the interface follows the answer language)
# --------------------------------------------------------------------------

T = {
    "de": {
        "title": "# Regulatory Copilot\nFragen zu MDR, DSGVO und EU AI Act – Antworten nur aus den Originaltexten, jede Aussage mit Quelle.",
        "notices": (
            "⚠️ **Keine Rechtsberatung.** Die Antworten können unvollständig oder falsch sein.  \n"
            "📚 **Quellen:** MDR (EU) 2017/745, DSGVO (EU) 2016/679, AI Act (EU) 2024/1689, jeweils englische Fassung von "
            "[EUR-Lex](https://eur-lex.europa.eu). **IEC 62304 ist nicht enthalten** (kostenpflichtige Norm).  \n"
            "🔒 **Fragen werden nicht gespeichert.** Der Verlauf (letzte 3 Runden) lebt nur in deinem Browser-Tab; Neuladen löscht ihn.  \n"
            "⏳ Nach längerer Inaktivität braucht der Start etwas Zeit (Kaltstart)."
        ),
        "chat": "Gespräch", "box": "Deine Frage", "ph": "z. B. Ist meine App ein Medizinprodukt?", "send": "Fragen",
        "new": "Neue Sitzung", "lang": "Antwortsprache", "examples": "Beispielfragen (kostenlos, vorab berechnet)",
        "hood": "Blick unter die Haube", "mode": "Suchmodus", "query": "Umformulierte Suchanfrage (englisch)",
        "hits": "Gefundene Textstellen (Top 6)", "cols": ["#", "ID", "Fundstelle", "Score", "Kosinus"],
        "sources": "Quellen", "none": "Keine Quellen.", "hood_empty": "–",
    },
    "en": {
        "title": "# Regulatory Copilot\nQuestions about the MDR, GDPR and EU AI Act – answers only from the original texts, every statement with a source.",
        "notices": (
            "⚠️ **No legal advice.** Answers may be incomplete or wrong.  \n"
            "📚 **Sources:** MDR (EU) 2017/745, GDPR (EU) 2016/679, AI Act (EU) 2024/1689, English versions from "
            "[EUR-Lex](https://eur-lex.europa.eu). **IEC 62304 is not included** (paid standard).  \n"
            "🔒 **Questions are not stored.** The history (last 3 rounds) lives only in your browser tab; reloading clears it.  \n"
            "⏳ After a period of inactivity the start takes a moment (cold start)."
        ),
        "chat": "Conversation", "box": "Your question", "ph": "e.g. Is my app a medical device?", "send": "Ask",
        "new": "New session", "lang": "Answer language", "examples": "Example questions (free, precomputed)",
        "hood": "Under the hood", "mode": "Search mode", "query": "Rewritten search query (English)",
        "hits": "Retrieved passages (top 6)", "cols": ["#", "ID", "Citation", "Score", "Cosine"],
        "sources": "Sources", "none": "No sources.", "hood_empty": "–",
    },
}


def format_sources(reply: Reply, lang: str) -> str:
    """Markdown with the English original quotes. Shown inside a collapsible message."""
    return "\n\n".join(
        f"**[{s['id']}]** {s['citation']}\n\n> " + s["quote"].replace("\n", "\n> ") for s in reply.sources
    )


def messages_for(question: str, reply: Reply, lang: str) -> list[gr.ChatMessage]:
    out = [gr.ChatMessage(role="user", content=question), gr.ChatMessage(role="assistant", content=reply.text)]
    if reply.sources:
        out.append(
            gr.ChatMessage(
                role="assistant", content=format_sources(reply, lang),
                metadata={"title": f"{T[lang]['sources']} ({len(reply.sources)})", "status": "done"},
            )
        )
    return out


def hood_view(reply: Reply | None, lang: str):
    if reply is None or not reply.hits:
        return T[lang]["hood_empty"], []
    rows = [[h["rank"], h["id"], h["citation"], h["score"], h["cosine"]] for h in reply.hits]
    return reply.search_query or T[lang]["hood_empty"], rows


def visitor_id(request: gr.Request | None) -> str:
    """Address (or session) of the caller; only ever hashed in memory by the limiter."""
    if request is None:
        return "local"
    fwd = request.headers.get("x-forwarded-for") if request.headers else None
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else (request.session_hash or "unknown")


# --------------------------------------------------------------------------
# app
# --------------------------------------------------------------------------


def build_demo(service: Service | None = None) -> gr.Blocks:
    service = service or Service()
    examples = load_examples()

    with gr.Blocks(title="Regulatory Copilot", analytics_enabled=False) as demo:
        history = gr.State([])  # list[Turn], browser session only
        title = gr.Markdown(T["de"]["title"])
        notices = gr.Markdown(T["de"]["notices"])
        lang = gr.Radio([("Deutsch", "de"), ("English", "en")], value="de", label=T["de"]["lang"])
        chat = gr.Chatbot(label=T["de"]["chat"], height=480)
        with gr.Row():
            box = gr.Textbox(label=T["de"]["box"], placeholder=T["de"]["ph"], scale=5, lines=1, max_lines=4)
            send = gr.Button(T["de"]["send"], variant="primary", scale=1)
        new = gr.Button(T["de"]["new"], size="sm")
        ex_label = gr.Markdown(f"**{T['de']['examples']}**", visible=bool(examples))
        ex_buttons = [gr.Button(e["question"]["de"], size="sm", visible=True) for e in examples]
        with gr.Accordion(T["de"]["hood"], open=False) as hood:
            mode = gr.Radio(["hybrid", "bm25", "vector"], value="hybrid", label=T["de"]["mode"])
            query_box = gr.Textbox(label=T["de"]["query"], interactive=False)
            hits_df = gr.Dataframe(headers=T["de"]["cols"], label=T["de"]["hits"], interactive=False, wrap=True)

        def ask(question, hist, lang_v, mode_v, chat_v, request: gr.Request):
            reply = service.ask(question, hist, lang_v, mode_v, visitor_id(request))
            return finish(question, reply, hist, lang_v, chat_v)

        def finish(question, reply, hist, lang_v, chat_v):
            chat_v = (chat_v or []) + messages_for(question, reply, lang_v)
            if reply.counted:
                hist = (hist + [Turn(question, reply.text)])[-service.cfg.max_history_turns:]
            q, rows = hood_view(reply, lang_v)
            return chat_v, hist, "", q, rows

        def ask_example(idx, hist, lang_v, chat_v):
            ex = examples[idx]
            return finish(ex["question"][lang_v], example_reply(ex, lang_v), hist, lang_v, chat_v)

        def reset(lang_v):
            return [], [], "", T[lang_v]["hood_empty"], []

        def switch_lang(lang_v):
            t = T[lang_v]
            ups = [
                t["title"], t["notices"], gr.update(label=t["lang"]), gr.update(label=t["chat"]),
                gr.update(label=t["box"], placeholder=t["ph"]), gr.update(value=t["send"]), gr.update(value=t["new"]),
                f"**{t['examples']}**", gr.update(label=t["hood"]), gr.update(label=t["mode"]), gr.update(label=t["query"]),
                gr.update(label=t["hits"], headers=t["cols"]),
            ]
            return ups + [gr.update(value=e["question"][lang_v]) for e in examples]

        io = dict(inputs=[box, history, lang, mode, chat], outputs=[chat, history, box, query_box, hits_df])
        box.submit(ask, **io)
        send.click(ask, **io)
        for i, b in enumerate(ex_buttons):
            b.click(lambda h, l, c, i=i: ask_example(i, h, l, c), [history, lang, chat], [chat, history, box, query_box, hits_df])
        new.click(reset, [lang], [chat, history, box, query_box, hits_df])
        lang.change(
            switch_lang, [lang],
            [title, notices, lang, chat, box, send, new, ex_label, hood, mode, query_box, hits_df] + ex_buttons,
        )
    return demo


def launch() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)  # request lines are harmless, but noise
    service = Service()
    service.warm_up()
    demo = build_demo(service)
    demo.queue(default_concurrency_limit=4, max_size=20)
    demo.launch(server_name=os.environ.get("GRADIO_SERVER_NAME", "0.0.0.0" if os.environ.get("SPACE_ID") else "127.0.0.1"))
