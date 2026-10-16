import hashlib
from html import escape

import streamlit as st

from gemini_api import GenealogyResult, analyze_transcription, image_analise


def _friendly_error_message(error: Exception) -> str:
    """Translate common Gemini availability and quota errors for the user."""
    message = str(error)
    normalized = message.lower()

    if "quota" in normalized:
        return (
            "A cota do Gemini para este projeto foi atingida. Aguarde a reposição "
            "da cota ou confira os limites do projeto no Google AI Studio."
        )
    if any(
        code in normalized
        for code in ("429", "too_many_requests", "rate_limit_exceeded")
    ):
        return (
            "O Gemini recebeu solicitações demais em pouco tempo. Aguarde alguns "
            "minutos antes de tentar novamente."
        )
    if "503" in normalized or "service_unavailable" in normalized:
        return "O Gemini está temporariamente sobrecarregado. Aguarde um pouco e tente novamente."
    return f"Não foi possível analisar o documento: {message}"


def _person_initials(name: str) -> str:
    parts = name.split()
    if not parts:
        return "?"
    return (parts[0][0] + (parts[-1][0] if len(parts) > 1 else "")).upper()


def _render_genealogy_result(result: GenealogyResult) -> None:
    st.markdown("### Identificação do documento")
    document_columns = st.columns(2)
    with document_columns[0]:
        st.markdown("**Tipo de documento**")
        st.write(result.document_type or "Não identificado")
    with document_columns[1]:
        st.markdown("**Evento principal**")
        st.write(result.main_event or "Não identificado")

    st.markdown("### Pessoas identificadas")
    if result.people:
        for start in range(0, len(result.people), 3):
            people = result.people[start : start + 3]
            columns = st.columns(len(people))
            for person, column in zip(people, columns):
                with column:
                    with st.container(border=True):
                        name = person.name or "Nome não identificado"
                        role = person.role or "Papel não identificado"
                        avatar = escape(_person_initials(name))
                        safe_name = escape(name)
                        safe_role = escape(role)
                        st.markdown(
                            "<div style='display:flex;flex-direction:column;"
                            "align-items:center;text-align:center;gap:0.55rem;"
                            "padding:0.5rem 0 0.85rem;'>"
                            "<div style='width:3.5rem;height:3.5rem;border-radius:50%;"
                            "display:flex;align-items:center;justify-content:center;"
                            "background:rgba(37,183,200,0.16);"
                            "border:2px solid rgba(37,183,200,0.55);"
                            "color:#167d8a;font-size:1.15rem;font-weight:700;'>"
                            f"{avatar}</div>"
                            "<div style='font-size:1.08rem;font-weight:700;"
                            "line-height:1.3;overflow-wrap:anywhere;'>"
                            f"{safe_name}</div>"
                            "<span style='display:inline-block;padding:0.22rem 0.7rem;"
                            "border-radius:999px;background:rgba(37,183,200,0.14);"
                            "color:#167d8a;font-size:0.84rem;font-weight:600;'>"
                            f"{safe_role}</span></div>",
                            unsafe_allow_html=True,
                        )
                        if person.information:
                            st.markdown("**Informações identificadas**")
                            for detail in person.information:
                                st.markdown(f"- {escape(detail)}")
                        if person.evidence:
                            with st.expander("Ver trecho de apoio"):
                                st.write(person.evidence)
    else:
        st.info("Nenhuma pessoa foi identificada na transcrição.")

    st.markdown("### Relações mencionadas")
    if result.relationships:
        for relationship in result.relationships:
            st.write(
                f"{relationship.source_person} — {relationship.relationship} — "
                f"{relationship.target_person} ({relationship.status})"
            )
            if relationship.evidence:
                st.caption(f'Trecho de apoio: “{relationship.evidence}”')
            if relationship.status == "hipotese" and relationship.rationale:
                st.caption(f"Hipótese, não confirmada: {relationship.rationale}")
    else:
        st.info("Nenhuma relação familiar foi identificada.")

    date_column, locality_column = st.columns(2)
    with date_column:
        st.markdown("### Datas")
        if result.dates:
            for item in result.dates:
                st.write(f"**{item.value}** — {item.context}" if item.context else item.value)
                if item.evidence:
                    st.caption(f'Trecho: “{item.evidence}”')
        else:
            st.write("Nenhuma data identificada.")
    with locality_column:
        st.markdown("### Localidades")
        if result.localities:
            for item in result.localities:
                st.write(f"**{item.value}** — {item.context}" if item.context else item.value)
                if item.evidence:
                    st.caption(f'Trecho: “{item.evidence}”')
        else:
            st.write("Nenhuma localidade identificada.")

    if result.other_information:
        with st.expander("Outras informações do documento"):
            for item in result.other_information:
                st.write(f"**{item.value}** — {item.context}" if item.context else item.value)
                if item.evidence:
                    st.caption(f'Trecho: “{item.evidence}”')

    st.markdown("### Contextualização")
    st.write(result.contextualization or "Não foi gerada uma contextualização.")


st.title("Scriptum", text_alignment="center")

uploaded_image = st.file_uploader(
    "Envie a imagem do documento",
    type=["png", "jpg", "jpeg"],
)

option = st.selectbox(
    "Selecione o que deseja analisar",
    ["Transcrição", "Correções", "Trechos incertos", "Análise genealógica"],
)

if uploaded_image is not None:
    image_bytes = uploaded_image.getvalue()
    mime_type = uploaded_image.type or "application/octet-stream"
    image_hash = hashlib.sha256(image_bytes).hexdigest()
    st.image(image_bytes, caption="Imagem enviada", width="stretch")

    button_label = (
        "Gerar análise genealógica"
        if option == "Análise genealógica"
        else "Analisar documento"
    )
    if st.button(button_label, type="primary"):
        progress_bar = st.progress(0, text="Preparando a análise...")
        st.caption("O avanço é aproximado; o Gemini não informa uma porcentagem exata.")

        def show_progress(value: float, message: str, start: float = 0, span: float = 1):
            percent = min(99, int((start + value * span) * 100))
            progress_bar.progress(percent, text=message)

        try:
            saved_result = st.session_state.get("scriptum_result")
            has_cached_transcription = (
                saved_result is not None
                and saved_result.get("image_hash") == image_hash
                and saved_result.get("transcription") is not None
            )
            if has_cached_transcription:
                transcription = saved_result["transcription"]
                show_progress(
                    0.1 if option == "Análise genealógica" else 0.7,
                    "Usando a transcrição já analisada...",
                )
            else:
                progress_callback = show_progress
                if option == "Análise genealógica":
                    progress_callback = lambda value, message: show_progress(
                        value, message, start=0, span=0.55
                    )
                transcription = image_analise(
                    image_bytes,
                    mime_type,
                    on_progress=progress_callback,
                )

            if option == "Análise genealógica":
                analysis_start = 0.1 if has_cached_transcription else 0.55
                analysis_span = 0.88 if has_cached_transcription else 0.43
                genealogy = analyze_transcription(
                    transcription.transcription,
                    on_progress=lambda value, message: show_progress(
                        value, message, start=analysis_start, span=analysis_span
                    ),
                )
            else:
                genealogy = (
                    saved_result.get("genealogy") if has_cached_transcription else None
                )

            progress_bar.progress(100, text="Análise concluída.")

            st.session_state["scriptum_result"] = {
                "image_hash": image_hash,
                "transcription": transcription,
                "genealogy": genealogy,
            }
        except Exception as exc:
            progress_bar.empty()
            st.error(_friendly_error_message(exc))
else:
    st.info("Envie uma imagem para começar.")

saved_result = st.session_state.get("scriptum_result")
if (
    saved_result
    and uploaded_image is not None
    and saved_result.get("image_hash") == image_hash
    and saved_result.get("transcription") is not None
):
    st.subheader(option)
    if option == "Transcrição":
        st.markdown(saved_result["transcription"].transcription)
    elif option == "Correções":
        st.markdown("**Transcrição revisada**")
        st.markdown(saved_result["transcription"].revised_transcription)
        st.markdown("**Correções realizadas**")
        corrections = saved_result["transcription"].corrections.strip()
        st.markdown(corrections or "Nenhuma correção foi realizada ou sugerida.")
    elif option == "Trechos incertos":
        uncertain_excerpts = saved_result["transcription"].uncertain_excerpts
        if isinstance(uncertain_excerpts, list):
            if uncertain_excerpts:
                for item in uncertain_excerpts:
                    st.markdown(f"**Trecho:** {item.excerpt}")
                    if item.alternatives:
                        st.write("Leituras possíveis: " + " / ".join(item.alternatives))
                    st.caption(f"Confiança estimada pela IA: {item.confidence}")
                    if item.context:
                        st.caption(f"Contexto: {item.context}")
            else:
                st.markdown("Nenhum trecho foi marcado como incerto.")
        else:
            # Older session results stored uncertain excerpts as plain text.
            st.markdown(
                uncertain_excerpts.strip()
                or "Nenhum trecho foi marcado como incerto."
            )
    else:
        genealogy = saved_result.get("genealogy")
        st.markdown("### Transcrição literal")
        st.markdown(saved_result["transcription"].transcription)
        if isinstance(genealogy, GenealogyResult):
            _render_genealogy_result(genealogy)
        elif genealogy:
            # Preserve genealogy results created by earlier versions of the app.
            st.markdown(genealogy)
        else:
            st.info("Clique em “Gerar análise genealógica” para analisar a transcrição.")
