"""Paragu-Auditor — Streamlit UI.

Chat + red flags dashboard. All in one file for the MVP.
"""
from paragu_auditor.agent.chat import chat
from paragu_auditor.agent.tools import get_all_releases
from paragu_auditor.red_flags.runner import run_all_flags_on_dataset, summarize_flag_results
import streamlit as st

st.title("🇵🇾 Paragu-Auditor")
st.caption("Auditor del Gasto Público — Dirección Nacional de Contrataciones Públicas de Paraguay")

tab1, tab2 = st.tabs(["💬 Consulta", "📊 Banderas Rojas"])

with tab1:
    st.markdown("""
    Preguntá en español sobre los datos de contratación pública de Paraguay.
    *Ejemplos:*
    - *"Mostrame los contratos con un solo oferente"*
    - *"Verificá el contrato ocds-03ad3f-193399"*
    - *"Resumen de contrataciones en 2024 por entidad"*
    - *"Búsqueda por RUC 80012345-6"*
    """)

    if "messages" not in st.session_state:
        st.session_state.messages = []

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input("Escribí tu consulta..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Consultando..."):
                response = chat(prompt, use_llm=False)
            st.markdown(response)
        st.session_state.messages.append({"role": "assistant", "content": response})

with tab2:
    st.subheader("Banderas Rojas en el Dataset")
    releases = get_all_releases()
    st.metric("Total contratos", len(releases))

    if st.button("Ejecutar banderas rojas ahora"):
        with st.spinner("Evaluando..."):
            results = run_all_flags_on_dataset(releases)
            summary = summarize_flag_results(results)

            col1, col2 = st.columns(2)
            with col1:
                for fid in ["R003", "R018"]:
                    if fid in summary:
                        s = summary[fid]
                        st.metric(
                            f"{fid} — {s.get('flagged', 0)} activadas",
                            f"{s['total']} evaluados",
                            delta=f"{s['flagged']} flags"
                        )
            with col2:
                st.metric("Total banderas activadas", summary["total_flagged"])

            st.dataframe(
                [
                    {"OCID": r.ocid, "Título": r.tender.title or "(sin título)",
                     "Modalidad": r.tender.procurement_method, "Entidad": r.tender.procuring_entity_name}
                    for r in releases
                ],
                use_container_width=True,
                hide_index=True,
            )
