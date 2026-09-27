# PladixAgentIA_CLI 🚀

Um ambiente de desenvolvimento integrado (IDE) completo via linha de comando (CLI) com integração direta e nativa ao **DeepSeek Web (`chat.deepseek.com`)**, suporte a **múltiplos agentes autônomos**, **pensamento profundo (Deep Think)** em tempo real, **memória persistente**, **gerenciamento de sessões** e resolução ultra-rápida do algoritmo **Proof of Work (DeepSeekHashV1)**.

---

### 👤 Créditos, Contato e Repositório
* **Desenvolvido por:** `PladixOficial`
* **GitHub:** [github.com/pladix](https://github.com/pladix)
* **Repositório do Projeto:** [github.com/pladix/PladixAgentIA_CLI](https://github.com/pladix/PladixAgentIA_CLI)
* **Canal / Contato Telegram:** [t.me/pladixoficial](https://t.me/pladixoficial)

---

## ⚡ Recursos Principais

1. **Desenvolvimento Autônomo e Focado em Projetos**:
   - Isolamento total na pasta selecionada pelo usuário (`/workspace` ou seleção interativa ao iniciar um projeto).
   - Suporte nativo a qualquer stack: **PHP**, **Node.js/TypeScript**, **Python**, **HTML/CSS/JS**, etc.
2. **Edição Cirúrgica de Código**:
   - Não reescreve arquivos inteiros nem destrói código funcional existente.
   - Aplica alterações pontuais e cirúrgicas apenas nas partes que precisam de ajustes, respeitando indentação e arquitetura.
3. **Roteiro e Checklist de Execução em Tempo Real**:
   - Cria um roadmap passo a passo e atualiza o checklist ao vivo no terminal CLI (`[ ]`, `[▶]`, `[✓]`).
4. **Ciclo de Auto-Fix Inteligente (estilo Lovable / Devin)**:
   - Valida a sintaxe do código (`php -l`, `py_compile`, `node --check`, etc.) e a execução de comandos.
   - Se ocorrer qualquer erro ou falha de compilação, o agente detecta automaticamente o traceback, formula o patch cirúrgico e corrige sem intervenção manual.
5. **Changelog e Diffs Unificados**:
   - Registra cada pasta criada, arquivo novo, trecho cirúrgico modificado e comando executado com visualização de diff unificado (`/changelog`).
6. **Integração Real com DeepSeek Web**:
   - Conexão direta com os endpoints oficiais (`/api/v0/chat/create_pow_challenge`, `/api/v0/chat_session/create`, `/api/v0/chat/completion`).
   - Autenticação real com Bearer Token e Cookies da sua conta.
7. **Motor PoW de Alta Performance (DeepSeekHashV1)**:
   - Implementação JIT de Keccak-236 (23 rodadas) compilada em código de máquina nativo com LLVM (Numba).
   - Resolve o desafio criptográfico de até 144.000 iterações em aproximadamente **100 milissegundos**.
8. **Pensamento Profundo (Deep Think) em Tempo Real**:
   - Exibe o fluxo de raciocínio interno do modelo (`THINK` fragment) em tempo real em um painel estilizado com contagem de tempo antes da resposta final.
9. **Sistema Multi-Agente & Pipeline Colaborativo**:
   - Sessões independentes no DeepSeek para cada perfil:
     - 🏗️ **Architect**: Planejamento de arquitetura, estruturação de módulos e contratos.
     - 💻 **Coder**: Desenvolvimento e geração de código funcional e de alta qualidade.
     - 🔍 **Reviewer**: Auditoria de segurança, boas práticas e detecção de bugs.
     - 🧪 **Tester**: Criação de suítes de testes unitários e casos de borda.
     - ⚡ **Debugger**: Diagnóstico de erros de compilação/execução.

---

## 🛠️ Instalação

Clone o repositório ou navegue até a pasta do projeto e instale as dependências:

```bash
pip install -r requirements.txt
```

---

## 🚀 Como Executar

### Opção 1: Inicializador Automático (Recomendado no Windows)
Basta dar um duplo clique no arquivo [`iniciar_cli.bat`](file:///c:/Users/luking/Desktop/DeepSeek_IDE_Auto/iniciar_cli.bat) ou executar no terminal:

```cmd
iniciar_cli.bat
```

> **O que o script faz automaticamente:**
> 1. Detecta se o Python está instalado (caso contrário, tenta instalar via `winget` ou orienta a instalação).
> 2. Configura e isola o ambiente virtual (`.venv`).
> 3. Instala/atualiza todas as dependências (`requirements.txt`).
> 4. Inicia o PladixAgentIA_CLI instantaneamente.

### Opção 2: Execução Direta via Python

```bash
pip install -r requirements.txt
python main.py
```

Na primeira execução, o sistema solicitará o seu **Bearer Token** da conta DeepSeek.

### 🔑 Como obter o Token DeepSeek:
1. Abra o navegador e acesse [https://chat.deepseek.com](https://chat.deepseek.com) logado na sua conta.
2. Abra as Ferramentas do Desenvolvedor (`F12`) e vá até a aba **Rede (Network)**.
3. Envie qualquer mensagem simples ou atualize a página.
4. Clique em uma requisição para `completion` ou `create_pow_challenge`.
5. Na seção **Headers**, copie o valor do cabeçalho `authorization` (sem a palavra `Bearer`, ou com ela - o sistema detecta automaticamente).
6. Dentro do CLI, digite `/login` e cole o token.

---

## 📋 Lista de Comandos Disponíveis

| Comando | Descrição |
| :--- | :--- |
| `/help` | Exibe a lista completa de comandos e ajuda |
| `/workspace <pasta>` | Seleciona ou cria uma pasta isolada para o projeto |
| `/build <tarefa>` | Modo Agente Autônomo (Cria pastas, arquivos, checklist e testes) |
| `/fix <problema>` | Auto-Fix cirúrgico (Corrige bugs sem quebrar o resto do código) |
| `/changelog` | Exibe o resumo detalhado de alterações e diffs cirúrgicos |
| `/login` ou `/token` | Configura ou atualiza o Bearer Token e Cookies da sua conta |
| `/status` | Exibe o status da conta, workspace e sessões |
| `/new [título]` | Cria uma nova sessão (chat) no DeepSeek Web |
| `/sessions` | Lista todas as sessões recentes da conta |
| `/switch <id>` | Alterna para uma sessão existente |
| `/think [on\|off]` | Liga ou desliga o Pensamento Profundo (Deep Think) |
| `/search [on\|off]` | Liga ou desliga a pesquisa na Web |
| `/agents` | Exibe o painel de status de todos os agentes autônomos |
| `/agent <nome> <tarefa>` | Envia uma tarefa para um agente específico (ex: `/agent architect planejar API`) |
| `/pipeline <tarefa>` | Executa o fluxo colaborativo completo (Architect ➔ Coder ➔ Reviewer ➔ Tester) |
| `/parallel` | Executa múltiplos agentes simultaneamente em sessões paralelas |
| `/ls [caminho]` | Lista os arquivos e diretórios do workspace atual |
| `/cat <arquivo>` | Exibe o conteúdo de um arquivo com Syntax Highlighting |
| `/run <comando>` | Executa comandos no shell do sistema operacional |
| `/remember <nota>` | Grava uma memória persistente sobre o projeto |
| `/memory` | Exibe todas as memórias salvas do projeto |
| `/clear` | Limpa a tela do terminal |
| `/exit` | Encerra a aplicação |

---

## 🔒 Arquitetura de Pastas

```
DeepSeek_IDE_Auto/
├── deepseek_cli/
│   ├── config.py       # Gerenciamento de credenciais e cabeçalhos
│   ├── pow_solver.py   # Solver JIT Keccak-236 (DeepSeekHashV1)
│   ├── client.py       # Cliente HTTP assíncrono com SSE
│   ├── memory.py       # Sistema de memória contextual persistente
│   ├── tools.py        # Ferramentas cirúrgicas, changelog e syntax check
│   ├── engine.py       # Motor de execução autônoma, checklist e auto-fix
│   ├── agents.py       # Orquestrador multi-agente e papéis
│   ├── ui.py           # Interface visual Rich com banners e painéis
│   └── cli.py          # REPL interativo e loop de comandos
├── main.py             # Ponto de entrada
├── iniciar_cli.bat     # Inicializador automático para Windows
├── requirements.txt    # Dependências do projeto
└── README.md           # Este arquivo
```

---

Desenvolvido com excelência por **PladixOficial** • [t.me/pladixoficial](https://t.me/pladixoficial)

