"""
Rich Terminal User Interface & Visual Components
Desenvolvido por PladixOficial
Telegram: t.me/pladixoficial
"""

import sys
from typing import List, Dict, Any, Optional
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.markdown import Markdown
from rich.syntax import Syntax
from rich.text import Text
from rich.tree import Tree
from rich import box

console = Console(legacy_windows=False)

BANNER_ART = r"""[bold cyan]
  ██████╗ ███████╗███████╗██████╗ ███████╗███████╗███████╗██╗  ██╗
  ██╔══██╗██╔════╝██╔════╝██╔══██╗██╔════╝██╔════╝██╔════╝██║ ██╔╝
  ██║  ██║█████╗  █████╗  ██████╔╝███████╗█████╗  █████╗  █████╔╝ 
  ██║  ██║██╔══╝  ██╔══╝  ██╔═══╝ ╚════██║██╔══╝  ██╔══╝  ██╔═██╗ 
  ██████╔╝███████╗███████╗██║     ███████║███████╗███████╗██║  ██╗
  ╚═════╝ ╚══════╝╚══════╝╚═╝     ╚══════╝╚══════╝╚══════╝╚═╝  ╚═╝
                [bold magenta]CLI IDE • PladixAgentIA_CLI • DEEP THINK[/bold magenta]
[/bold cyan]"""


def print_banner(workspace: str, authenticated: bool, active_session: Optional[str] = None):
    console.print(BANNER_ART)
    
    dev_info = Text.assemble(
        ("⚡ Desenvolvido por: ", "bold yellow"),
        ("PladixOficial", "bold white on dark_blue"),
        ("  |  Telegram: ", "bold green"),
        ("t.me/pladixoficial", "underline bold cyan")
    )
    console.print(Panel(dev_info, box=box.ROUNDED, border_style="cyan"))

    status_table = Table(show_header=False, box=box.SIMPLE, expand=True)
    status_table.add_column("Key", style="bold bright_black", width=18)
    status_table.add_column("Value", style="bold white")

    auth_status = "[green]✓ Autenticado (DeepSeek Real Web)[/green]" if authenticated else "[red]✗ Não Autenticado (Use /login ou /token)[/red]"
    status_table.add_row("Status da Conta:", auth_status)
    status_table.add_row("Workspace Ativo:", f"[cyan]{workspace}[/cyan]")
    status_table.add_row("Sessão Atual:", f"[yellow]{active_session or 'Nenhuma selecionada (crie com /new)'}[/yellow]")
    status_table.add_row("PoW Engine:", "[bold green]Numba JIT Keccak-236 (Ativo / Sub-100ms)[/bold green]")

    console.print(Panel(status_table, title="[bold]Informações do Sistema[/bold]", border_style="bright_blue"))
    console.print("[bright_black]Digite [bold cyan]/help[/bold cyan] para ver a lista de comandos ou envie uma mensagem direta.[/bright_black]\n")


def print_help():
    table = Table(title="[bold cyan]COMANDOS DO PladixAgentIA_CLI[/bold cyan]", box=box.ROUNDED, border_style="cyan")
    table.add_column("Comando", style="bold yellow", width=22)
    table.add_column("Descrição", style="white")

    table.add_row("[bold]/workspace <pasta>[/bold]", "Selecionar ou criar uma pasta dedicada para o projeto")
    table.add_row("[bold]/build <tarefa>[/bold]", "Modo Agente Autônomo (Cria pastas, arquivos, checklist e testes)")
    table.add_row("[bold]/fix <problema>[/bold]", "Modo Auto-Fix cirúrgico (Corrige bugs sem quebrar o resto do código)")
    table.add_row("[bold]/changelog[/bold]", "Exibir o resumo detalhado de todas as alterações feitas (diffs)")
    table.add_row("[bold]/login[/bold] ou [bold]/token[/bold]", "Configurar Token Bearer e Cookies da conta DeepSeek")
    table.add_row("[bold]/status[/bold]", "Verificar status da conta, workspace e configurações")
    table.add_row("[bold]/new [título][/bold]", "Criar uma nova sessão (chat) no DeepSeek")
    table.add_row("[bold]/sessions[/bold]", "Listar sessões recentes e alternar entre elas")
    table.add_row("[bold]/switch <id>[/bold]", "Mudar para uma sessão específica")
    table.add_row("[bold]/think [on|off][/bold]", "Ativar ou desativar o Pensamento Profundo (Deep Think)")
    table.add_row("[bold]/search [on|off][/bold]", "Ativar ou desativar a busca na web em tempo real")
    table.add_row("[bold]/agents[/bold]", "Abrir painel de múltiplos agentes (Architect, Coder, Reviewer, Tester)")
    table.add_row("[bold]/agent <nome> <tarefa>[/bold]", "Executar tarefa com um agente específico em sua própria sessão")
    table.add_row("[bold]/pipeline <tarefa>[/bold]", "Executar pipeline colaborativo completo (Architect -> Coder -> Reviewer -> Tester)")
    table.add_row("[bold]/parallel[/bold]", "Executar agentes simultaneamente com diferentes tarefas")
    table.add_row("[bold]/ls [caminho][/bold]", "Listar arquivos do workspace selecionado")
    table.add_row("[bold]/cat <arquivo>[/bold]", "Exibir conteúdo de um arquivo com syntax highlighting")
    table.add_row("[bold]/run <comando>[/bold]", "Executar comando shell no workspace")
    table.add_row("[bold]/memory[/bold]", "Ver e gerenciar memórias do projeto")
    table.add_row("[bold]/remember <nota>[/bold]", "Gravar uma memória permanente sobre o projeto")
    table.add_row("[bold]/clear[/bold]", "Limpar a tela do terminal")
    table.add_row("[bold]/exit[/bold]", "Sair da aplicação")

    console.print(table)
    console.print("\n[dim]Desenvolvido por PladixOficial • t.me/pladixoficial[/dim]\n")


def print_sessions_table(sessions: List[Dict[str, Any]], active_id: Optional[str] = None):
    table = Table(title="[bold cyan]SESSÕES DEEPSEEK RECENTES[/bold cyan]", box=box.ROUNDED)
    table.add_column("Ativa", style="bold green", width=6)
    table.add_column("ID da Sessão", style="yellow", width=38)
    table.add_column("Título", style="bold white")
    table.add_column("Agente", style="cyan", width=12)

    for s in sessions:
        sid = s.get("id", "")
        title = s.get("title") or "Sem Título"
        agent = s.get("agent", "chat")
        is_active = "[green]▶ ATIVA[/green]" if sid == active_id else ""
        table.add_row(is_active, sid, title, agent)

    console.print(table)


def print_agents_dashboard(agents: Dict[str, Any]):
    table = Table(title="[bold magenta]PAINEL DE AGENTES AUTÔNOMOS[/bold magenta]", box=box.ROUNDED, border_style="magenta")
    table.add_column("Agente", style="bold yellow", width=16)
    table.add_column("Função", style="white", width=30)
    table.add_column("Sessão DeepSeek", style="bright_black", width=38)
    table.add_column("Status", style="bold green", width=18)

    for role_id, agent in agents.items():
        sess_str = agent.session_id or "[dim]Não iniciada[/dim]"
        status_color = "green" if agent.status in ("Pronto", "Concluído") else "yellow"
        table.add_row(
            f"{agent.role.icon} {agent.role.name}",
            agent.role.description[:28] + "...",
            sess_str,
            f"[{status_color}]{agent.status}[/{status_color}]"
        )

    console.print(table)


def render_code_file(path: str, content: str):
    ext = path.split(".")[-1] if "." in path else "text"
    syntax = Syntax(content, ext, theme="monokai", line_numbers=True)
    console.print(Panel(syntax, title=f"[bold cyan]Arquivo: {path}[/bold cyan]", border_style="cyan"))


def print_markdown(content: str):
    md = Markdown(content)
    console.print(md)

