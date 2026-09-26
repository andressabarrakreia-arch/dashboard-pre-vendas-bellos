import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(
    page_title="Dashboard de Pré-Vendas | Belloscar",
    page_icon="📊",
    layout="wide"
)

# Estilo visual moderno e limpo
st.markdown("""
    <style>
    .main {
        background-color: #f8f9fa;
    }
    .metric-card {
        background-color: white;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        text-align: center;
    }
    </style>
""", unsafe_allow_html=True)

st.title("📊 Dashboard de Pré-Vendas & Atendimento")
st.markdown("Análise completa de leads, canais, agendamentos e visitas com deduplicação inteligente por telefone.")

# Upload do arquivo ou uso do arquivo padrão caso já esteja na pasta
@st.cache_data
def load_data(uploaded_file):
    if uploaded_file is not None:
        df = pd.read_csv(uploaded_file)
    else:
        try:
            df = pd.read_csv("leads-recebidos-26-09-2026-14_40.csv")
        except:
            return None
    return df

uploaded_file = st.sidebar.file_uploader("📂 Envie seu relatório CSV atualizado", type=["csv"])
df_raw = load_data(uploaded_file)

if df_raw is None:
    st.info("👋 Por favor, faça o upload do arquivo CSV do seu relatório para gerar o dashboard.")
else:
    # Pré-processamento e limpeza
    df = df_raw.copy()
    
    # Normalizar telefones para deduplicação
    df['Celular_Limpo'] = df['Celular'].fillna('').astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
    df['Telefone_Limpo'] = df['Telefone'].fillna('').astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
    df['Contato_Tel'] = df['Celular_Limpo'].mask(df['Celular_Limpo'] == '', df['Telefone_Limpo'])
    df['Contato_Tel'] = df['Contato_Tel'].replace(['nan', 'None', ''], pd.NA)

    # Sidebar - Filtros
    st.sidebar.header("🔍 Filtros de Análise")
    
    # Checkbox para deduplicação
    remover_duplicados = st.sidebar.checkbox("Remover Contatos Dupliqués (por Telefone)", value=True)
    
    if remover_duplicados:
        # Mantém o primeiro registro de cada telefone válido, e preserva os sem telefone (NA)
        df_validos = df.dropna(subset=['Contato_Tel']).drop_duplicates(subset=['Contato_Tel'], keep='first')
        df_sem_tel = df[df['Contato_Tel'].isna()]
        df = pd.concat([df_validos, df_sem_tel]).reset_index(drop=True)
        st.sidebar.success(f"Deduplicação ativa: {len(df_raw)} ➔ {len(df)} leads únicos.")
    else:
        st.sidebar.info(f"Exibindo todos os {len(df)} registros (sem deduplicação).")

    # Filtro de Responsável / Atendente
    responsaveis = sorted(df['Responsável'].dropna().unique().tolist())
    sel_responsavel = st.sidebar.multiselect("Filtrar por Atendente/Responsável", responsaveis, default=[])
    if sel_responsavel:
        df = df[df['Responsável'].isin(sel_responsavel)]

    # Filtro de Canal / Origem
    origens = sorted(df['Origem'].dropna().unique().tolist())
    sel_origem = st.sidebar.multiselect("Filtrar por Canal (Origem)", origens, default=[])
    if sel_origem:
        df = df[df['Origem'].isin(sel_origem)]

    # Filtro de Status
    status_list = sorted(df['Status'].dropna().unique().tolist())
    sel_status = st.sidebar.multiselect("Filtrar por Status", status_list, default=[])
    if sel_status:
        df = df[df['Status'].isin(sel_status)]

    # Métricas Principais (KPIs)
    total_leads = len(df)
    agendados_count = df[df['Status'].str.contains('Agendado', case=False, na=False) | (df['Visita'] == 'Sim')].shape[0]
    visitas_count = df[df['Visita'].str.upper() == 'SIM'].shape[0]
    
    taxa_conversao_visita = (visitas_count / total_leads * 100) if total_leads > 0 else 0

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f"""<div class="metric-card"><h3>Total de Leads</h3><h1>{total_leads}</h1></div>""", unsafe_allow_html=True)
    with col2:
        st.markdown(f"""<div class="metric-card"><h3>Agendamentos</h3><h1>{agendados_count}</h1></div>""", unsafe_allow_html=True)
    with col3:
        st.markdown(f"""<div class="metric-card"><h3>Visitas Realizadas</h3><h1>{visitas_count}</h1></div>""", unsafe_allow_html=True)
    with col4:
        st.markdown(f"""<div class="metric-card"><h3>Taxa de Visita</h3><h1>{taxa_conversao_visita:.1f}%</h1></div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Gráficos Linha 1: Canais e Status
    col_g1, col_g2 = st.columns(2)

    with col_g1:
        st.subheader("📢 Leads por Canal (Origem)")
        origem_counts = df['Origem'].value_counts().reset_index()
        origem_counts.columns = ['Origem', 'Total']
        fig_origem = px.bar(origem_counts.head(10), x='Total', y='Origem', orientation='h', 
                             color='Total', color_continuous_scale='Blues', text='Total')
        fig_origem.update_layout(yaxis={'categoryorder':'total ascending'}, margin=dict(t=10, b=10, l=10, r=10), height=350)
        st.plotly_chart(fig_origem, use_container_width=True)

    with col_g2:
        st.subheader("🎯 Distribuição por Status")
        status_counts = df['Status'].value_counts().reset_index()
        status_counts.columns = ['Status', 'Total']
        fig_status = px.pie(status_counts, names='Status', values='Total', hole=0.4, color_discrete_sequence=px.colors.qualitative.Pastel)
        fig_status.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=350)
        st.plotly_chart(fig_status, use_container_width=True)

    # Gráficos Linha 2: Desempenho por Atendente
    st.subheader("👥 Desempenho por Atendente / Responsável")
    
    # Agrupar por atendente: Total de leads, Agendados e Visitas
    atendente_df = df.groupby('Responsável').agg(
        Total_Leads=('ID', 'count'),
        Visitas=('Visita', lambda x: (x.str.upper() == 'SIM').sum()),
        Agendados=('Status', lambda x: x.str.contains('Agendado', case=False, na=False).sum())
    ).reset_index()
    
    atendente_df['Taxa_Conversao'] = (atendente_df['Visitas'] / atendente_df['Total_Leads'] * 100).round(1)
    atendente_df = atendente_df.sort_values(by='Total_Leads', ascending=False)

    fig_atendente = px.bar(atendente_df, x='Responsável', y=['Total_Leads', 'Visitas'], 
                           barmode='group', title="Leads vs Visitas por Atendente",
                           color_discrete_sequence=['#1f77b4', '#2ca02c'])
    fig_atendente.update_layout(xaxis_tickangle=-45, height=400, margin=dict(t=30, b=50, l=10, r=10))
    st.plotly_chart(fig_atendente, use_container_width=True)

    # Tabela detalhada por Atendente
    with st.expander("📋 Ver Tabela Detalhada de Performance por Atendente"):
        st.dataframe(atendente_df.rename(columns={
            'Responsável': 'Atendente',
            'Total_Leads': 'Total de Leads',
            'Visitas': 'Visitas Realizadas',
            'Agendados': 'Agendados',
            'Taxa_Conversao': 'Taxa de Conversão (%)'
        }), use_container_width=True)

    # Visualização da Base de Dados Tratada
    with st.expander("🔍 Ver Base de Dados Filtrada e Deduplicada"):
        st.dataframe(df[['ID', 'Criado em', 'Responsável', 'Status', 'Visita', 'Origem', 'Cliente', 'Celular', 'Contato_Tel']], use_container_width=True)
