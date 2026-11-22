"""Interface Web Demonstrativa em Streamlit para o Assistente de Atendimento ao Cliente com IA."""

import sys
from pathlib import Path

# Adiciona raiz do projeto ao sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import streamlit as st
import streamlit.components.v1 as components
from src.config import GEMINI_API_KEY
from src.evaluator import PromptEvaluator
from src.generator import ContentGenerator
from src.llm_client import (
    LLMClient,
    LLMError,
    MissingAPIKeyError,
    AuthenticationError,
    RateLimitError,
    ModelUnavailableError,
    ServiceUnavailableError,
)
from src.models import ContentType, PromptVersion
from src.storage import StorageManager

st.set_page_config(
    page_title="Assistente de Atendimento ao Cliente com IA",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)


def render_mermaid(code: str):
    """Renderiza diagrama Mermaid utilizando componente HTML seguro."""
    html = f"""
    <div class="mermaid" style="display: flex; justify-content: center; background: #ffffff; padding: 15px; border-radius: 8px;">
        {code}
    </div>
    <script type="module">
        import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
        mermaid.initialize({{ startOnLoad: true, theme: 'default' }});
    </script>
    """
    components.html(html, height=380, scrolling=True)


@st.cache_resource
def get_services(mock_mode: bool):
    llm = LLMClient(mock_mode=mock_mode)
    storage = StorageManager()
    generator = ContentGenerator(llm_client=llm, storage_manager=storage)
    evaluator = PromptEvaluator(generator=generator, storage=storage)
    return generator, evaluator, storage


def main():
    st.title("🤖 Assistente de Atendimento ao Cliente com IA")
    st.caption("Engenharia de Prompt, Adaptação a Perfis, Cache Determinístico e Avaliação por Rubrica Oficial")

    # Sidebar - Configurações e Perfil
    st.sidebar.header("⚙️ Configurações da Sessão")
    mock_mode = st.sidebar.checkbox("Modo Mock (Offline / Sem Cota)", value=True)
    use_cache = st.sidebar.checkbox("Habilitar Cache Determinístico", value=True)

    if not mock_mode and (not GEMINI_API_KEY or GEMINI_API_KEY == "sua_chave_aqui"):
        st.sidebar.warning(
            "⚠️ **Chave GEMINI_API_KEY não configurada no .env.** "
            "Configure sua chave para chamadas reais ou ative o **Modo Mock (Offline)**."
        )

    generator, evaluator, storage = get_services(mock_mode=mock_mode)
    profiles = generator.get_available_profiles()
    profile_options = {p.name: p.id for p in profiles}

    selected_profile_name = st.sidebar.selectbox("Selecione a Persona / Perfil do Cliente:", list(profile_options.keys()))
    selected_profile_id = profile_options[selected_profile_name]
    profile = generator.load_profile(selected_profile_id)

    # Detalhes do Perfil Selecionado
    with st.sidebar.expander("👤 Detalhes da Persona Selecionada", expanded=True):
        st.markdown(f"**Nível Técnico:** `{profile.technical_level}`")
        st.markdown(f"**Estado Emocional:** `{profile.tone_mood}`")
        st.markdown(f"**Preferência:** {profile.communication_preference}")
        st.markdown(f"**Diretriz:** {profile.guidance}")
        st.markdown("**Restrições:**")
        for c in profile.constraints:
            st.markdown(f"- *{c}*")

    selected_version_str = st.sidebar.radio("Versão de Prompt Padrão:", ["v2 (Aprimorado)", "v1 (Baseline)"])
    selected_version = PromptVersion.V2 if "v2" in selected_version_str else PromptVersion.V1

    # Abas Principais
    tab_generate, tab_compare, tab_history = st.tabs([
        "📝 Atendimento Multiconteúdo",
        "⚖️ Comparador de Prompts (Rubrica Oficial)",
        "📜 Histórico & Auditoria",
    ])

    # ABA 1: Atendimento Multiconteúdo
    with tab_generate:
        st.subheader("Geração dos Quatro Conteúdos de Atendimento")
        default_messages = {
            "iniciante": "Meu roteador está com uma luz vermelha piscando e a internet sumiu. Não entendo nada de rede, tenho medo de mexer e quebrar algo. Me ajude por favor!",
            "apressado": "Estou em reunião de diretoria e o painel de relatórios travou no carregamento com erro 504. Preciso de solução em 2 minutos.",
            "tecnico": "O endpoint de autenticação OAuth2 está retornando 401 Unauthorized após refresh de token via CLI. Logs indicam token_expired imediatamente.",
            "irritado": "É a terceira vez que ligo! O suporte de vocês disse que tinha resolvido meu acesso e continuo bloqueado. Vou cancelar o contrato hoje!",
        }
        initial_text = default_messages.get(selected_profile_id, "Preciso de ajuda com o sistema.")
        customer_msg = st.text_area("Mensagem / Relato do Cliente:", value=initial_text, height=100)

        col1, col2 = st.columns([1, 4])
        with col1:
            btn_generate = st.button("🚀 Gerar Conteúdos", type="primary", use_container_width=True)

        if btn_generate:
            try:
                with st.spinner("Gerando os 4 conteúdos adaptados ao perfil..."):
                    results = generator.generate_all(
                        profile_id=selected_profile_id,
                        customer_message=customer_msg,
                        prompt_version=selected_version,
                        use_cache=use_cache,
                    )

                st.success("Conteúdos gerados com sucesso!")

                sub_tab1, sub_tab2, sub_tab3, sub_tab4 = st.tabs([
                    "🩺 Diagnóstico",
                    "📋 Passo a Passo",
                    "❓ Perguntas de Esclarecimento",
                    "🔀 Fluxograma",
                ])

                with sub_tab1:
                    rec = results[ContentType.DIAGNOSTICO]
                    st.caption(f"Status: {'🟢 Cache Hit' if rec.cached else '🟡 Nova Chamada'} | Latência: {rec.latency_ms}ms")
                    st.markdown(rec.output_text)

                with sub_tab2:
                    rec = results[ContentType.PASSO_A_PASSO]
                    st.caption(f"Status: {'🟢 Cache Hit' if rec.cached else '🟡 Nova Chamada'} | Latência: {rec.latency_ms}ms")
                    st.markdown(rec.output_text)

                with sub_tab3:
                    rec = results[ContentType.PERGUNTAS_ESCLARECIMENTO]
                    st.caption(f"Status: {'🟢 Cache Hit' if rec.cached else '🟡 Nova Chamada'} | Latência: {rec.latency_ms}ms")
                    st.markdown(rec.output_text)

                with sub_tab4:
                    rec = results[ContentType.FLUXOGRAMA]
                    st.caption(f"Status: {'🟢 Cache Hit' if rec.cached else '🟡 Nova Chamada'} | Latência: {rec.latency_ms}ms")
                    st.markdown(rec.output_text)
                    if "```mermaid" in rec.output_text:
                        try:
                            code = rec.output_text.split("```mermaid")[1].split("```")[0].strip()
                            st.markdown("**Visualização Gráfica do Fluxograma:**")
                            render_mermaid(code)
                        except Exception:
                            pass
            except MissingAPIKeyError as e:
                st.error(f"🔑 **Chave Ausente:** {e}")
            except AuthenticationError as e:
                st.error(f"🚫 **Erro de Autenticação:** {e}")
            except RateLimitError as e:
                st.warning(f"⏳ **Limite Excedido:** {e}")
            except (ModelUnavailableError, ServiceUnavailableError, LLMError) as e:
                st.error(f"⚠️ **Erro LLM:** {e}")
            except Exception as e:
                st.error(f"❌ **Erro Inesperado:** {e}")

    # ABA 2: Comparador de Prompts (Rubrica Oficial)
    with tab_compare:
        st.subheader("Avaliação e Comparação v1 vs v2 pela Rubrica Oficial")
        st.info("A rubrica oficial avalia exatamente três dimensões (notas de 1 a 5 com justificativas): **Clareza**, **Adequação ao nível do cliente** e **Acionabilidade**.")

        comp_type_str = st.selectbox(
            "Tipo de Conteúdo para Comparar:",
            [c.value for c in ContentType],
            index=0,
        )
        comp_content_type = ContentType(comp_type_str)

        btn_compare = st.button("⚖️ Executar Comparação de Versões", type="primary")
        if btn_compare:
            try:
                with st.spinner("Executando versões v1 e v2 e calculando pontuações da rubrica..."):
                    comparison = evaluator.compare(
                        content_type=comp_content_type,
                        profile_id=selected_profile_id,
                        customer_message=customer_msg,
                        use_cache=use_cache,
                    )

                # Resumo e Métricas
                col_m1, col_m2, col_m3 = st.columns(3)
                with col_m1:
                    st.metric("Média v1 (Baseline)", f"{comparison.v1_average} / 5.0")
                with col_m2:
                    st.metric("Média v2 (Aprimorado)", f"{comparison.v2_average} / 5.0", delta=round(comparison.v2_average - comparison.v1_average, 2))
                with col_m3:
                    st.metric("Versão Vencedora", comparison.winner.upper())

                st.markdown(f"**Veredito Analítico:** {comparison.summary}")

                # Tabela de Rubrica
                st.markdown("### Notas por Critério Oficial")
                crit_rows = []
                labels = {
                    "clareza": "1. Clareza",
                    "adequacao_nivel_cliente": "2. Adequação ao nível do cliente",
                    "acionabilidade": "3. Acionabilidade",
                }
                for k, label in labels.items():
                    s1 = comparison.v1_scores[k]
                    s2 = comparison.v2_scores[k]
                    crit_rows.append({
                        "Critério Oficial": label,
                        "Nota v1": f"{s1.score}/5",
                        "Justificativa v1": s1.justification,
                        "Nota v2": f"{s2.score}/5",
                        "Justificativa v2": s2.justification,
                    })
                st.dataframe(crit_rows, use_container_width=True)

                # Visualização Lado a Lado
                st.markdown("### Saídas Geradas Lado a Lado")
                col_v1, col_v2 = st.columns(2)
                with col_v1:
                    st.markdown("#### Versão v1 (Baseline)")
                    st.text_area("Saída v1", value=comparison.v1_output, height=350, disabled=True)
                with col_v2:
                    st.markdown("#### Versão v2 (Aprimorada)")
                    st.text_area("Saída v2", value=comparison.v2_output, height=350, disabled=True)

            except MissingAPIKeyError as e:
                st.error(f"🔑 **Chave Ausente:** {e}")
            except AuthenticationError as e:
                st.error(f"🚫 **Erro de Autenticação:** {e}")
            except RateLimitError as e:
                st.warning(f"⏳ **Limite Excedido:** {e}")
            except (ModelUnavailableError, ServiceUnavailableError, LLMError) as e:
                st.error(f"⚠️ **Erro LLM:** {e}")
            except Exception as e:
                st.error(f"❌ **Erro Inesperado:** {e}")

    # ABA 3: Histórico e Auditoria
    with tab_history:
        st.subheader("Auditoria de Execuções e Comparações Persistidas")
        hist_tab1, hist_tab2 = st.tabs(["Execuções Salvas (JSON)", "Comparações Salvas (JSON)"])

        with hist_tab1:
            runs = storage.list_runs(limit=30)
            if runs:
                runs_data = [{
                    "ID": r.id[:8],
                    "Timestamp": r.timestamp[:19],
                    "Conteúdo": r.content_type.value,
                    "Perfil": r.profile_id,
                    "Versão": r.prompt_version.value,
                    "Cache?": "SIM" if r.cached else "NÃO",
                    "Latência": f"{r.latency_ms}ms",
                } for r in runs]
                st.dataframe(runs_data, use_container_width=True)
            else:
                st.info("Nenhuma execução registrada até o momento.")

        with hist_tab2:
            comps = storage.list_comparisons(limit=30)
            if comps:
                comps_data = [{
                    "ID": c.id[:8],
                    "Timestamp": c.timestamp[:19],
                    "Conteúdo": c.content_type.value,
                    "Perfil": c.profile_id,
                    "Média v1": c.v1_average,
                    "Média v2": c.v2_average,
                    "Vencedor": c.winner.upper(),
                } for c in comps]
                st.dataframe(comps_data, use_container_width=True)
            else:
                st.info("Nenhuma comparação registrada até o momento.")


if __name__ == "__main__":
    main()
