"""
PladixAgentIA_CLI - Interactive Command Line Interface
Main event loop, command dispatcher, and real-time streaming engine.

Desenvolvido por PladixOficial
Telegram: t.me/pladixoficial
"""

import os
import sys
import asyncio
from typing import Optional

from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.styles import Style
from prompt_toolkit.key_binding import KeyBindings
from rich.live import Live
from rich.panel import Panel
from rich.text import Text
from rich.spinner import Spinner
from rich.console import Group
from rich import box

from .config import Config
from .client import DeepSeekClient, StreamChunk
from .tools import IDETools
from .memory import MemoryManager
from .agents import AgentOrchestrator
from .engine import ProjectEngine
from .ui import (
    console,
    print_banner,
    print_help,
    print_sessions_table,
    print_agents_dashboard,
    render_code_file,
    print_markdown
)
from rich.markdown import Markdown

COMMANDS = [
    "/help", "/login", "/token", "/status", "/new", "/sessions", "/switch",
    "/workspace", "/project", "/build", "/fix", "/changelog",
    "/think", "/search", "/agents", "/agent", "/pipeline", "/parallel",
    "/ls", "/cat", "/run", "/memory", "/remember", "/clear", "/exit", "/paste", "/file", "/pladix"
]


class DeepSeekCLI:
    def __init__(self):
        self.config = Config()
        self.tools = IDETools()
        self.client = DeepSeekClient(self.config)
        self.memory = MemoryManager(str(self.tools.workspace))
        self.orchestrator = AgentOrchestrator(self.client, self.memory, self.tools)
        self.engine = ProjectEngine(self.client, self.tools, self.memory)
        self.parent_message_id: Optional[int] = None
        self.pladix_mode = False
        try:
            kb = KeyBindings()
            @kb.add('enter')
            def _(event):
                event.current_buffer.validate_and_handle()

            self.prompt_session = PromptSession(
                completer=WordCompleter(COMMANDS, ignore_case=True),
                style=Style.from_dict({
                    'prompt': '#00afff bold',
                }),
                multiline=True,
                key_bindings=kb
            )
        except Exception:
            self.prompt_session = None

    def print_welcome(self):
        os.system('cls' if os.name == 'nt' else 'clear')
        print_banner(
            workspace=str(self.tools.workspace),
            authenticated=self.config.is_authenticated(),
            active_session=self.config.active_session_id
        )

    async def run(self):
        self.print_welcome()

        # If not authenticated, prompt user
        if not self.config.is_authenticated():
            console.print("[bold yellow]⚡ Configuração inicial necessária: Você precisa fornecer o Bearer Token da sua conta DeepSeek.[/bold yellow]")
            console.print("[dim]Abra o navegador em https://chat.deepseek.com, inspecione a aba Rede (Network), copie o Bearer Token do cabeçalho Authorization ou execute /login.[/dim]\n")

        while True:
            try:
                prompt_label = f"DeepSeek [{self.config.active_session_id[:8] if self.config.active_session_id else 'sem sessão'}] ❯ "
                if self.prompt_session:
                    user_input = await self.prompt_session.prompt_async(prompt_label)
                else:
                    loop = asyncio.get_running_loop()
                    user_input = await loop.run_in_executor(None, input, prompt_label)
                text = user_input.strip()

                if not text:
                    continue

                if text.startswith("/"):
                    await self.handle_command(text)
                else:
                    await self.handle_chat(text)

            except (KeyboardInterrupt, EOFError):
                console.print("\n[yellow]Encerrando PladixAgentIA_CLI... Até mais![/yellow]")
                break
            except Exception as e:
                console.print(f"[bold red]Erro inesperado:[/bold red] {e}")

    async def handle_command(self, cmd_line: str):
        parts = cmd_line.split(" ", 1)
        cmd = parts[0].lower()
        arg = parts[1].strip() if len(parts) > 1 else ""

        if cmd in ("/exit", "/quit"):
            sys.exit(0)

        elif cmd == "/help":
            print_help()

        elif cmd == "/clear":
            self.print_welcome()

        elif cmd == "/pladix":
            self.pladix_mode = not getattr(self, "pladix_mode", False)
            if self.pladix_mode:
                console.print("\n[bold magenta]🔥 MODO SUPREMO PLADIX CODER ATIVADO! 🔥[/bold magenta]")
                console.print("[dim]A partir de agora, tudo que for colado, digitado ou enviado via /file será processado diretamente pelo Especialista em APIs/CHKs.[/dim]\n")
            else:
                console.print("\n[bold yellow]Modo Pladix Coder DESATIVADO. Voltando ao fluxo de chat padrão.[/bold yellow]\n")

        elif cmd == "/file":
            if not arg:
                console.print("[yellow]Uso: /file <caminho_do_arquivo>[/yellow]")
                return
            
            filepath = os.path.abspath(os.path.join(str(self.tools.workspace), arg))
            if not os.path.isfile(filepath):
                console.print(f"[red]Arquivo não encontrado: {filepath}[/red]")
                return
            
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                if content:
                    console.print(f"[cyan]Arquivo '{arg}' lido com sucesso ({len(content)} caracteres). Iniciando trabalhos...[/cyan]")
                    await self.handle_chat(content)
                else:
                    console.print("[yellow]O arquivo está vazio.[/yellow]")
            except Exception as e:
                console.print(f"[bold red]Erro ao ler o arquivo:[/bold red] {e}")

        elif cmd == "/paste":
            console.print("[cyan]Modo COLAR ativado. Cole seu texto (Ctrl+V).[/cyan]")
            console.print("[cyan]Digite [bold]/end[/bold] em uma nova linha para finalizar e enviar.[/cyan]")
            lines = []
            while True:
                try:
                    line = await self.prompt_session.prompt_async("... ") if getattr(self, 'prompt_session', None) else input("... ")
                    if line.strip() == "/end":
                        break
                    lines.append(line)
                except EOFError:
                    break
                except KeyboardInterrupt:
                    lines = []
                    break
            full_text = "\n".join(lines).strip()
            if full_text:
                await self.handle_chat(full_text)

        elif cmd in ("/login", "/token"):
            token = console.input("[bold cyan]Cole o seu Bearer Token do DeepSeek: [/bold cyan]").strip()
            cookie = console.input("[bold cyan]Cole os Cookies (opcional, pressione Enter se não tiver): [/bold cyan]").strip()
            if token:
                self.config.set_auth(token, cookie if cookie else None)
                console.print("[bold green]✓ Credenciais salvas com sucesso![/bold green]")
            else:
                console.print("[red]Token não pode ser vazio.[/red]")

        elif cmd == "/status":
            self.print_welcome()

        elif cmd == "/new":
            title = arg or "Novo Chat IDE"
            with console.status("[bold cyan]Criando nova sessão no DeepSeek Web...[/bold cyan]", spinner="dots"):
                try:
                    sess = await self.client.create_chat_session(agent="chat")
                    sid = sess["id"]
                    self.config.active_session_id = sid
                    self.config.save()
                    self.parent_message_id = None
                    self.memory.record_session(sid, title, "user")
                    console.print(f"[bold green]✓ Nova sessão criada e ativada:[/bold green] [cyan]{sid}[/cyan]")
                except Exception as e:
                    console.print(f"[bold red]Erro ao criar sessão:[/bold red] {e}")

        elif cmd == "/sessions":
            with console.status("[bold cyan]Buscando sessões no DeepSeek...[/bold cyan]", spinner="dots"):
                sessions = await self.client.list_chat_sessions()
            if sessions:
                print_sessions_table(sessions, self.config.active_session_id)
            else:
                # Show locally remembered sessions if remote list failed
                loc = [{"id": k, "title": v.get("title"), "agent": v.get("agent")} for k, v in self.memory.sessions.items()]
                if loc:
                    print_sessions_table(loc, self.config.active_session_id)
                else:
                    console.print("[yellow]Nenhuma sessão encontrada. Crie uma com /new.[/yellow]")

        elif cmd == "/switch":
            if not arg:
                console.print("[yellow]Uso: /switch <session_id>[/yellow]")
                return
            self.config.active_session_id = arg
            self.config.save()
            sess_info = self.memory.get_session_info(arg)
            self.parent_message_id = sess_info.get("last_message_id") if sess_info else None
            console.print(f"[bold green]✓ Sessão ativa alterada para:[/bold green] [cyan]{arg}[/cyan]")

        elif cmd == "/think":
            if arg.lower() in ("off", "false", "0"):
                self.config.thinking_enabled = False
                console.print("[yellow]Pensamento Profundo (Deep Think) DESATIVADO.[/yellow]")
            else:
                self.config.thinking_enabled = True
                console.print("[green]Pensamento Profundo (Deep Think) ATIVADO.[/green]")
            self.config.save()

        elif cmd == "/search":
            if arg.lower() in ("off", "false", "0"):
                self.config.search_enabled = False
                console.print("[yellow]Busca na web DESATIVADA.[/yellow]")
            else:
                self.config.search_enabled = True
                console.print("[green]Busca na web ATIVADA.[/green]")
            self.config.save()

        elif cmd == "/agents":
            print_agents_dashboard(self.orchestrator.agents)

        elif cmd == "/agent":
            if not arg:
                console.print("[yellow]Uso: /agent <role> <tarefa>[/yellow]")
                console.print(f"[dim]Roles disponíveis: {', '.join(self.orchestrator.agents.keys())}[/dim]")
                return
            
            subparts = arg.split(" ", 1)
            role_name = subparts[0].lower()
            task = subparts[1] if len(subparts) > 1 else ""

            if not task:
                console.print(f"[yellow]Por favor, informe a tarefa para o agente {role_name}.[/yellow]")
                return

            agent = self.orchestrator.get_agent(role_name)
            if not agent:
                console.print(f"[red]Agente '{role_name}' não encontrado.[/red]")
                return

            await self.execute_agent_task(agent, task)

        elif cmd == "/pipeline":
            if not arg:
                console.print("[yellow]Uso: /pipeline <tarefa complexa de programação>[/yellow]")
                return
            await self.execute_pipeline(arg)

        elif cmd == "/parallel":
            await self.execute_parallel_flow()

        elif cmd == "/ls":
            res = self.tools.list_files(arg or ".")
            if "error" in res:
                console.print(f"[red]{res['error']}[/red]")
            else:
                items = res.get("items", [])
                console.print(f"[bold cyan]Arquivos em {self.tools.workspace}:[/bold cyan]")
                for item in items:
                    icon = "📁" if item["type"] == "dir" else "📄"
                    size_str = f" ({item['size']} B)" if item["type"] == "file" else ""
                    console.print(f"  {icon} [white]{item['path']}[/white][dim]{size_str}[/dim]")

        elif cmd == "/cat":
            if not arg:
                console.print("[yellow]Uso: /cat <caminho_do_arquivo>[/yellow]")
                return
            res = self.tools.read_file(arg)
            if "error" in res:
                console.print(f"[red]{res['error']}[/red]")
            else:
                render_code_file(res["path"], res["content"])

        elif cmd == "/run":
            if not arg:
                console.print("[yellow]Uso: /run <comando>[/yellow]")
                return
            with console.status(f"[bold cyan]Executando: {arg}...[/bold cyan]", spinner="dots"):
                res = self.tools.execute_command(arg)
            if "error" in res:
                console.print(f"[red]{res['error']}[/red]")
            else:
                code_color = "green" if res["returncode"] == 0 else "red"
                console.print(f"[{code_color}]Return code: {res['returncode']}[/{code_color}]")
                if res["stdout"]:
                    console.print(Panel(res["stdout"], title="[green]STDOUT[/green]", border_style="green"))
                if res["stderr"]:
                    console.print(Panel(res["stderr"], title="[red]STDERR[/red]", border_style="red"))

        elif cmd in ("/workspace", "/project"):
            if not arg:
                console.print(f"[bold cyan]Pasta atual do Workspace:[/bold cyan] [yellow]{self.tools.workspace}[/yellow]")
                new_path = console.input("[bold cyan]Digite o caminho da pasta para o projeto (ou Enter para manter): [/bold cyan]").strip()
                if not new_path:
                    return
                arg = new_path
            res = self.tools.set_workspace(arg, create_if_missing=True)
            if res.get("success"):
                self.memory = MemoryManager(str(self.tools.workspace))
                self.orchestrator.memory = self.memory
                self.engine.memory = self.memory
                console.print(f"[bold green]✓ Pasta do projeto selecionada com sucesso:[/bold green] [yellow]{self.tools.workspace}[/yellow]")
            else:
                console.print(f"[bold red]Erro ao definir pasta: {res.get('error')}[/bold red]")

        elif cmd == "/changelog":
            summary = self.tools.changelog.get_summary()
            console.print(Panel(summary, title="[bold cyan]📋 Changelog de Modificações do Projeto[/bold cyan]", border_style="cyan"))

        elif cmd == "/build":
            if not arg:
                console.print("[yellow]Uso: /build <o que deseja que o agente autônomo desenvolva>[/yellow]")
                return
            await self.execute_autonomous_task(arg)

        elif cmd == "/fix":
            if not arg:
                console.print("[yellow]Uso: /fix <descrição do bug ou erro que precisa de correção cirúrgica>[/yellow]")
                return
            await self.execute_autonomous_task(f"CORREÇÃO DE BUG CIRÚRGICA: {arg}")

        elif cmd == "/remember":
            if not arg:
                console.print("[yellow]Uso: /remember <fato importante sobre o projeto>[/yellow]")
                return
            self.memory.add_note(arg)
            console.print(f"[bold green]✓ Memória salva:[/bold green] {arg}")

        elif cmd == "/memory":
            notes = self.memory.get_notes()
            if not notes:
                console.print("[dim]Nenhuma memória gravada ainda. Use /remember para adicionar.[/dim]")
            else:
                console.print("[bold cyan]Memórias do Projeto:[/bold cyan]")
                for n in notes:
                    console.print(f"  • [yellow][{n['timestamp']}][/yellow] [white]{n['content']}[/white]")

        else:
            console.print(f"[red]Comando desconhecido: {cmd}. Digite /help para a lista de comandos.[/red]")

    async def execute_autonomous_task(self, prompt: str):
        if not self.config.is_authenticated():
            console.print("[bold red]Você precisa autenticar o DeepSeek primeiro.[/bold red]")
            console.print("Use [bold cyan]/login[/bold cyan] ou [bold cyan]/token[/bold cyan] para configurar sua credencial.")
            return

        # Check and select project folder automatically to avoid blocking paste streams
        console.print(f"[bold cyan]Pasta do projeto:[/bold cyan] [yellow]{self.tools.workspace}[/yellow]")
        console.print("[dim](Use o comando /workspace se desejar alterar o diretório de trabalho)[/dim]")
        
        # Ensure Memory components are initialized
        self.memory = MemoryManager(str(self.tools.workspace))
        self.orchestrator.memory = self.memory
        self.engine.memory = self.memory

        # Ensure active session
        if not self.config.active_session_id:
            with console.status("[bold cyan]Iniciando sessão do DeepSeek...[/bold cyan]", spinner="dots"):
                try:
                    sess = await self.client.create_chat_session(agent="chat")
                    self.config.active_session_id = sess["id"]
                    self.config.save()
                    self.parent_message_id = None
                except Exception as e:
                    console.print(f"[bold red]Erro ao criar sessão:[/bold red] {e}")
                    return

        session_id = self.config.active_session_id
        await self.engine.run_autonomous_task(prompt, session_id=session_id)

    async def handle_chat(self, prompt: str):
        if getattr(self, "pladix_mode", False):
            agent = self.orchestrator.get_agent("pladix_coder")
            if agent:
                await self.execute_agent_task(agent, prompt)
                return

        # Auto-detect if this is a project development / code generation instruction
        project_keywords = [
            "crie", "criar", "desenvolva", "desenvolver", "monte", "implemente",
            "fazer", "faça", "construa", "corrija", "arrume", "adicione", "altere",
            "edite", "projeto", "arquivo", "pasta", "php", "python", "node", "nodejs",
            "html", "css", "javascript", "typescript", "api", "crud", "app", "site"
        ]
        prompt_lower = prompt.lower()
        if any(kw in prompt_lower for kw in project_keywords):
            await self.execute_autonomous_task(prompt)
            return

        if not self.config.is_authenticated():
            console.print("[bold red]Você precisa autenticar o DeepSeek primeiro.[/bold red]")
            console.print("Use [bold cyan]/login[/bold cyan] ou [bold cyan]/token[/bold cyan] para configurar sua credencial.")
            return

        if not self.config.active_session_id:
            with console.status("[bold cyan]Iniciando nova sessão no DeepSeek...[/bold cyan]", spinner="dots"):
                try:
                    sess = await self.client.create_chat_session(agent="chat")
                    self.config.active_session_id = sess["id"]
                    self.config.save()
                    self.parent_message_id = None
                except Exception as e:
                    console.print(f"[bold red]Erro ao criar sessão:[/bold red] {e}")
                    return

        session_id = self.config.active_session_id
        console.print(f"\n[bold green]Enviando para o DeepSeek (Sessão: {session_id[:8]})...[/bold green]")

        thought_text = ""
        response_text = ""
        tokens_count = 0
        elapsed_sec = None

        with console.status("[bold cyan]Resolvendo PoW DeepSeekHashV1 via Numba JIT...[/bold cyan]", spinner="dots"):
            pass

        try:
            with Live(console=console, refresh_per_second=10) as live:
                def update_display():
                    elements = []
                    if self.config.thinking_enabled and thought_text:
                        time_str = f" ({elapsed_sec:.1f}s)" if elapsed_sec else ""
                        elements.append(
                            Panel(
                                Text(thought_text, style="dim cyan"),
                                title=f"[bold cyan]🧠 Pensamento Profundo{time_str}[/bold cyan]",
                                border_style="cyan",
                                box=box.ROUNDED
                            )
                        )
                    if response_text:
                        elements.append(
                            Panel(
                                Markdown(response_text),
                                title="[bold green]DeepSeek AI[/bold green]",
                                border_style="green",
                                box=box.ROUNDED
                            )
                        )
                    if not elements:
                        elements.append(Text("Aguardando resposta do servidor...", style="dim"))
                    live.update(Group(*elements))

                async for chunk in self.client.chat_completion(
                    session_id=session_id,
                    prompt=prompt,
                    parent_message_id=self.parent_message_id,
                    thinking_enabled=self.config.thinking_enabled,
                    search_enabled=self.config.search_enabled
                ):
                    if chunk.chunk_type == "ready":
                        if chunk.message_id:
                            self.parent_message_id = chunk.message_id
                    elif chunk.chunk_type == "think":
                        thought_text += chunk.content
                        update_display()
                    elif chunk.chunk_type == "think_elapsed":
                        elapsed_sec = chunk.elapsed_secs
                        update_display()
                    elif chunk.chunk_type == "response":
                        response_text += chunk.content
                        update_display()
                    elif chunk.chunk_type == "tokens":
                        tokens_count = chunk.accumulated_tokens
                    elif chunk.chunk_type == "finish":
                        if chunk.message_id:
                            self.parent_message_id = chunk.message_id
                            self.memory.update_session_msg_id(session_id, self.parent_message_id)
                        update_display()
                    elif chunk.chunk_type == "error":
                        console.print(f"[bold red]Erro da API:[/bold red] {chunk.error}")
                        return

            console.print(f"[dim]Tokens acumulados: {tokens_count} | Mensagem ID: {self.parent_message_id}[/dim]\n")

        except Exception as e:
            console.print(f"[bold red]Erro na comunicação:[/bold red] {e}")

    async def execute_agent_task(self, agent, task: str):
        console.print(f"\n[bold magenta]Executando com o Agente {agent.role.icon} {agent.role.name}...[/bold magenta]")
        
        with console.status(f"[bold cyan]Inicializando sessão dedicada do agente {agent.role.name}...[/bold cyan]", spinner="dots"):
            await agent.init_session()

        thought_text = ""
        response_text = ""

        with Live(console=console, refresh_per_second=10) as live:
            def on_chunk(agent_name, chunk: StreamChunk):
                nonlocal thought_text, response_text
                elements = []
                if chunk.chunk_type == "think":
                    thought_text += chunk.content
                elif chunk.chunk_type == "response":
                    response_text += chunk.content

                if thought_text:
                    elements.append(
                        Panel(
                            Text(thought_text, style="dim cyan"),
                            title=f"[bold cyan]🧠 Pensamento do {agent.role.name}[/bold cyan]",
                            border_style="cyan"
                        )
                    )
                if response_text:
                    elements.append(
                        Panel(
                            Markdown(response_text),
                            title=f"[bold magenta]{agent.role.icon} {agent.role.name}[/bold magenta]",
                            border_style="magenta"
                        )
                    )
                if elements:
                    live.update(Group(*elements))

            try:
                await agent.execute_task(task, on_chunk=on_chunk)
            except Exception as e:
                console.print(f"[bold red]Erro na execução do agente:[/bold red] {e}")

    async def execute_pipeline(self, task: str):
        console.print(f"\n[bold cyan]══ INICIANDO PIPELINE COLABORATIVO DE DESENVOLVIMENTO ══[/bold cyan]")
        console.print(f"[white]Tarefa Principal: {task}[/white]\n")

        # Step 1: Architect
        console.print("[bold yellow]▶ ETAPA 1/4: Planejamento Arquitetural (Architect)[/bold yellow]")
        architect = self.orchestrator.get_agent("architect")
        plan = await architect.execute_task(
            f"Elabore uma arquitetura e plano passo a passo para: {task}"
        )
        console.print(Panel(Markdown(plan), title="[bold yellow]Plano do Arquiteto[/bold yellow]", border_style="yellow"))

        # Step 2: Coder
        console.print("\n[bold green]▶ ETAPA 2/4: Implementação de Código (Coder)[/bold green]")
        coder = self.orchestrator.get_agent("coder")
        code = await coder.execute_task(
            f"Com base neste plano:\n{plan}\n\nImplemente a solução completa em código limpo e funcional:"
        )
        console.print(Panel(Markdown(code), title="[bold green]Código do Desenvolvedor[/bold green]", border_style="green"))

        # Step 3: Reviewer
        console.print("\n[bold cyan]▶ ETAPA 3/4: Auditoria de Segurança e Qualidade (Reviewer)[/bold cyan]")
        reviewer = self.orchestrator.get_agent("reviewer")
        review = await reviewer.execute_task(
            f"Revise este código, avaliando vulnerabilidades, performance e boas práticas:\n\n{code}"
        )
        console.print(Panel(Markdown(review), title="[bold cyan]Auditoria do Reviewer[/bold cyan]", border_style="cyan"))

        # Step 4: Tester
        console.print("\n[bold magenta]▶ ETAPA 4/4: Suíte de Testes Automatizados (Tester)[/bold magenta]")
        tester = self.orchestrator.get_agent("tester")
        tests = await tester.execute_task(
            f"Crie os testes unitários completos e assertivos para este código:\n\n{code}"
        )
        console.print(Panel(Markdown(tests), title="[bold magenta]Testes de QA[/bold magenta]", border_style="magenta"))

        console.print("\n[bold green]✓ Pipeline concluído com sucesso![/bold green]\n")

    async def execute_parallel_flow(self):
        console.print("\n[bold cyan]Execução Simultânea de Múltiplos Agentes em Paralelo[/bold cyan]")
        task1 = console.input("[yellow]Tarefa para o Architect (ex: modelar banco de dados): [/yellow]").strip()
        task2 = console.input("[green]Tarefa para o Coder (ex: criar classe de utilitários): [/green]").strip()

        agent_tasks = {}
        if task1:
            agent_tasks["architect"] = task1
        if task2:
            agent_tasks["coder"] = task2

        if not agent_tasks:
            console.print("[red]Nenhuma tarefa informada.[/red]")
            return

        with console.status("[bold cyan]Executando agentes simultaneamente em sessões DeepSeek paralelas...[/bold cyan]", spinner="dots"):
            results = await self.orchestrator.run_parallel_tasks(agent_tasks)

        for role_id, res in results.items():
            agent = self.orchestrator.get_agent(role_id)
            name = agent.role.name if agent else role_id
            console.print(Panel(Markdown(res), title=f"[bold green]Resultado - {name}[/bold green]", border_style="green"))


def main():
    cli = DeepSeekCLI()
    asyncio.run(cli.run())


if __name__ == "__main__":
    main()

