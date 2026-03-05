# AI-Agent-Financial-Analyst
AI agent specializing in financial transactions.
# Sistema de Análise Financeira com Plutus, LangGraph e Dash

Este projeto fornece uma interface web para análise inteligente de movimentações financeiras em planilhas Excel, utilizando agentes de IA.

## Requisitos Prévios

1. **Ollama Instalado**: Certifique-se de que o Ollama está rodando em sua máquina.
2. **Modelo Plutus**: Baixe o modelo específico de finanças executando:
   ```bash
   ollama pull 0xroyce/plutus
   ```

## Como Executar

1. Instale as dependências Python:
   ```bash
   pip install dash pandas plotly openpyxl langgraph langchain-ollama langchain-core
   ```

2. Execute a aplicação:
   ```bash
   python app.py
   ```

3. Acesse no navegador: `http://localhost:8050`

## Funcionalidades

- **Upload Múltiplo**: Arraste várias planilhas Excel simultaneamente.
- **Consolidação Automática**: O sistema une os dados de todos os arquivos.
- **Agente Analista (LangGraph + Plutus)**: Analisa tendências, anomalias e fornece recomendações.
- **Agente Visualizador**: Sugere e gera gráficos interativos com Plotly baseados nos insights da análise.

## Estrutura do Código

- `app.py`: Interface Dash e callbacks.
- `agents.py`: Definição do grafo de agentes e integração com o Ollama.
- `movimentacao_teste.xlsx`: Planilha de exemplo gerada para testes iniciais.

## Nova Funcionalidade: Download de PDF
- Após a análise ser concluída, um botão verde **"Download Relatório PDF"** aparecerá.
- O PDF conterá o texto detalhado gerado pelo modelo Plutus.
- Dependência adicional: `fpdf2` (incluída no comando de instalação atualizado).
