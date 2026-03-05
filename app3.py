import streamlit as st
import pandas as pd
import plotly.express as px
import seaborn as sns
import matplotlib.pyplot as plt
from typing import TypedDict, Any, List
from io import BytesIO
from fpdf import FPDF
import tempfile
import os

# --- LangChain & Ollama Imports ---
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, END

# --- INITIAL CONFIGURATION ---
st.set_page_config(page_title="Forensic Agent - Plutus Engine", layout="wide")

# --- AGENT STATE DEFINITION ---
class AgentState(TypedDict):
    raw_df: pd.DataFrame
    processed_df: pd.DataFrame
    stats_summary: str
    analysis_text: str
    plotly_fig: Any
    seaborn_plot_path: str
    pdf_buffer: BytesIO

# --- NODE 1: DATA PROCESSING ---
def node_process_data(state: AgentState):
    df = state['raw_df'].copy()
    
    # Cleaning numeric columns
    df['Credit'] = pd.to_numeric(df['Credit'], errors='coerce').fillna(0)
    df['Debit'] = pd.to_numeric(df['Debit'], errors='coerce').fillna(0)
    
    # 1. Concatenation (Requirement: EFH1 + EFH2)
    df['Entity_ID'] = df['EFH1'].astype(str) + "_" + df['EFH2'].astype(str)
    
    # 2. Volume and Difference (Requirement: Credit vs Debit)
    df['Total_Volume'] = df['Credit'].abs() + df['Debit'].abs()
    df['Net_Flow'] = df['Credit'] - df['Debit']
    
    # Statistical Summary
    stats_desc = df[['Credit', 'Debit', 'Total_Volume', 'Net_Flow']].describe().to_string()
    
    # Top 10 entities grouping
    grouped_df = df.groupby('Entity_ID')[['Credit', 'Debit', 'Total_Volume']].sum().sort_values(by='Total_Volume', ascending=False).head(10)
    
    summary = f"GLOBAL STATISTICS:\n{stats_desc}\n\nTOP 10 ENTITIES BY VOLUME:\n{grouped_df.to_string()}"
    
    return {
        "processed_df": df,
        "stats_summary": summary
    }

# --- NODE 2: VISUALIZATION (Plotly Bar Chart & Seaborn) ---
def node_generate_plots(state: AgentState):
    df = state['processed_df']
    
    # Grouping for the Bar Chart
    top_10 = df.groupby('Entity_ID')['Total_Volume'].sum().sort_values(ascending=False).head(10).reset_index()
    
    # 1. Plotly Interactive Bar Chart
    fig = px.bar(
        top_10, 
        x='Entity_ID', 
        y='Total_Volume',
        color='Total_Volume',
        title="Top 10 Entities by Total Volume (Interactive)",
        template="plotly_dark",
        color_continuous_scale='Viridis'
    )
    
    # 2. Seaborn Static Plot for PDF
    plt.figure(figsize=(10, 6))
    sns.set_theme(style="whitegrid")
    sns.barplot(data=top_10, x='Total_Volume', y='Entity_ID', palette='magma')
    plt.title('Top 10 Entities by Volume (Forensic View)')
    
    temp_img = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    plt.savefig(temp_img.name, bbox_inches='tight')
    plt.close()

    return {
        "plotly_fig": fig,
        "seaborn_plot_path": temp_img.name
    }

# --- NODE 3: FORENSIC ANALYSIS (PLUTUS ENGINE) ---
def node_analyze_fraud(state: AgentState):
    stats = state['stats_summary']
    
    llm = ChatOllama(
        model="0xroyce/plutus", 
        temperature=0.1,
        base_url="http://localhost:11434"
    )
    
    prompt = ChatPromptTemplate.from_template("""
    You are a Senior Forensic Auditor. Analyze the following financial patterns:
    {stats}

    Provide a report with:
    1. Predictive Analysis of flows.
    2. Red Flags for Money Laundering or Fraud.
    3. At least 10 lines of detailed technical comments and recommendations.
    
    Respond in ENGLISH.
    """)
    
    try:
        chain = prompt | llm
        response = chain.invoke({"stats": stats})
        return {"analysis_text": response.content}
    except Exception as e:
        return {"analysis_text": f"Error connecting to Plutus Engine: {str(e)}"}

# --- NODE 4: PDF GENERATION (FPDF2 MODERN SYNTAX) ---
def node_create_pdf(state: AgentState):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)
    
    def clean(t): return t.encode('latin-1', 'replace').decode('latin-1')

    # Header
    pdf.set_font("Helvetica", style='B', size=16)
    pdf.cell(w=0, h=10, text="Forensic Financial Report - Plutus AI", new_x="LMARGIN", new_y="NEXT", align='C')
    pdf.ln(10)
    
    # AI Analysis
    pdf.set_font("Helvetica", style='B', size=12)
    pdf.cell(w=0, h=10, text="1. Forensic AI Analysis", new_x="LMARGIN", new_y="NEXT", align='L')
    pdf.set_font("Helvetica", size=10)
    analysis = state.get('analysis_text', '').replace('**', '').replace('##', '')
    pdf.multi_cell(w=0, h=6, text=clean(analysis), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(10)
    
    # Statistics
    pdf.set_font("Helvetica", style='B', size=12)
    pdf.cell(w=0, h=10, text="2. Statistical Summary", new_x="LMARGIN", new_y="NEXT", align='L')
    pdf.set_font("Courier", size=8)
    pdf.multi_cell(w=0, h=5, text=clean(state['stats_summary']), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(10)

    # Chart
    img_path = state.get('seaborn_plot_path')
    if img_path and os.path.exists(img_path):
        pdf.add_page()
        pdf.set_font("Helvetica", style='B', size=12)
        pdf.cell(w=0, h=10, text="3. Volume Visualization", new_x="LMARGIN", new_y="NEXT", align='L')
        pdf.image(img_path, x=10, w=190)

    # Saving to Disk then reading to avoid Bytearray encoding issues
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_pdf:
            tmp_path = tmp_pdf.name
        
        pdf.output(tmp_path)
        
        with open(tmp_path, "rb") as f:
            pdf_bytes = f.read()
            
        os.remove(tmp_path)
        if img_path and os.path.exists(img_path): os.remove(img_path)
        
        return {"pdf_buffer": BytesIO(pdf_bytes)}
    except Exception as e:
        return {"pdf_buffer": BytesIO(f"PDF Error: {str(e)}".encode())}

# --- LANGGRAPH FLOW ---
def build_agent():
    workflow = StateGraph(AgentState)
    workflow.add_node("process", node_process_data)
    workflow.add_node("visualize", node_generate_plots)
    workflow.add_node("analyze", node_analyze_fraud)
    workflow.add_node("report", node_create_pdf)
    
    workflow.set_entry_point("process")
    workflow.add_edge("process", "visualize")
    workflow.add_edge("visualize", "analyze")
    workflow.add_edge("analyze", "report")
    workflow.add_edge("report", END)
    
    return workflow.compile()

# --- STREAMLIT UI ---
def main():
    st.title("🕵️‍♂️ Forensic Agent (Ollama: Plutus)")
    
    uploaded_files = st.file_uploader("Upload Excel Files", type=['xlsx'], accept_multiple_files=True)
    
    if uploaded_files and st.button("Run Plutus Engine"):
        with st.spinner("Analyzing financial patterns..."):
            try:
                dfs = [pd.read_excel(f) for f in uploaded_files]
                combined_df = pd.concat(dfs, ignore_index=True)
                
                agent = build_agent()
                result = agent.invoke({"raw_df": combined_df})
                
                tab1, tab2, tab3 = st.tabs(["📊 Analytics", "🧠 AI Report", "📋 Source Data"])
                
                with tab1:
                    st.plotly_chart(result['plotly_fig'], use_container_width=True)
                
                with tab2:
                    st.markdown(result['analysis_text'])
                    st.download_button(
                        "📥 Download PDF Report",
                        data=result['pdf_buffer'],
                        file_name="forensic_report.pdf",
                        mime="application/pdf"
                    )
                
                with tab3:
                    st.dataframe(result['processed_df'])
                    
            except Exception as e:
                st.error(f"Error: {e}")

if __name__ == "__main__":
    main()