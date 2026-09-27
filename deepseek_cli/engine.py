"""
Autonomous Agentic Execution Engine
Orchestrates live checklists, surgical file editing, tool call parsing, and auto-fix loop.

Desenvolvido por PladixOficial
Telegram: t.me/pladixoficial
"""

import re
import asyncio
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field

from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.live import Live
from rich.console import Group
from rich import box

from .client import DeepSeekClient, StreamChunk
from .tools import IDETools
from .memory import MemoryManager
from .ui import console


@dataclass
class ChecklistItem:
    text: str
    status: str = "pending"  # "pending", "in_progress", "done", "error"


class ProjectEngine:
    def __init__(self, client: DeepSeekClient, tools: IDETools, memory: MemoryManager):
        self.client = client
        self.tools = tools
        self.memory = memory
        self.checklist: List[ChecklistItem] = []

    def get_system_instructions(self) -> str:
        return (
            "Você é um Engenheiro de Software Sênior e Agente Autônomo de Desenvolvimento.\n"
            "Desenvolvido por PladixOficial (t.me/pladixoficial).\n\n"
            "### REGRAS FUNDAMENTAIS DE EXECUÇÃO:\n"
            "1. Todas as suas ações ocorrem EXCLUSIVAMENTE dentro da pasta selecionada do projeto.\n"
            "2. NUNCA quebre ou apague código funcional existente. Ao modificar arquivos existentes, faça alterações CIRÚRGICAS e pontuais.\n"
            "3. Sempre inicie tarefas complexas definindo um Checklist/Roteiro estruturado de passos.\n"
            "4. Utilize as tags estruturadas abaixo para que o ambiente execute suas ações automaticamente no sistema operacional:\n\n"
            "### FORMATO DAS FERRAMENTAS (TOOL CALLS):\n\n"
            "Para criar pastas:\n"
            "<tool_call>\n"
            "<action>create_dir</action>\n"
            "<path>caminho/da/pasta</path>\n"
            "</tool_call>\n\n"
            "Para criar um arquivo novo completo:\n"
            "<tool_call>\n"
            "<action>create_file</action>\n"
            "<path>caminho/do/arquivo.ext</path>\n"
            "<content>\n"
            "...codigo completo aqui...\n"
            "</content>\n"
            "</tool_call>\n\n"
            "Para editar um arquivo existente de forma CIRÚRGICA (substituir apenas o trecho necessário):\n"
            "<tool_call>\n"
            "<action>edit_file</action>\n"
            "<path>caminho/do/arquivo.ext</path>\n"
            "<target>\n"
            "...trecho exato antigo a ser substituido com 1 ou 2 linhas de contexto...\n"
            "</target>\n"
            "<replacement>\n"
            "...novo trecho corrigido...\n"
            "</replacement>\n"
            "</tool_call>\n\n"
            "Para executar comandos shell de teste, build ou instalação de dependências:\n"
            "<tool_call>\n"
            "<action>run_command</action>\n"
            "<command>npm install express</command>\n"
            "</tool_call>\n\n"
            "Para atualizar o Checklist de progresso:\n"
            "<checklist>\n"
            "<item status=\"done\">1. Planejamento da arquitetura</item>\n"
            "<item status=\"in_progress\">2. Criando modelos e estrutura de pastas</item>\n"
            "<item status=\"pending\">3. Implementar rotas e lógica</item>\n"
            "<item status=\"pending\">4. Testar e validar código</item>\n"
            "</checklist>\n\n"
            "Respeite padrões de arquitetura limpa, organize pastas adequadamente para a linguagem (PHP, Python, Node.js, HTML/CSS, etc.) e valide antes de concluir."
        )

    def parse_checklist(self, text: str) -> bool:
        match = re.search(r"<checklist>(.*?)</checklist>", text, re.DOTALL | re.IGNORECASE)
        if not match:
            return False

        items_raw = re.findall(r'<item status=["\'](.*?)["\']>(.*?)</item>', match.group(1), re.DOTALL | re.IGNORECASE)
        if items_raw:
            self.checklist = [ChecklistItem(text=t.strip(), status=s.strip().lower()) for s, t in items_raw]
            return True
        return False

    def parse_tool_calls(self, text: str) -> List[Dict[str, str]]:
        calls = []
        matches = re.finditer(r"<tool_call>(.*?)</tool_call>", text, re.DOTALL | re.IGNORECASE)
        for m in matches:
            block = m.group(1)
            action_m = re.search(r"<action>(.*?)</action>", block, re.DOTALL | re.IGNORECASE)
            if not action_m:
                continue
            action = action_m.group(1).strip().lower()

            call_dict = {"action": action}

            path_m = re.search(r"<path>(.*?)</path>", block, re.DOTALL | re.IGNORECASE)
            if path_m:
                call_dict["path"] = path_m.group(1).strip()

            content_m = re.search(r"<content>(.*?)</content>", block, re.DOTALL | re.IGNORECASE)
            if content_m:
                call_dict["content"] = content_m.group(1).strip("\r\n")

            target_m = re.search(r"<target>(.*?)</target>", block, re.DOTALL | re.IGNORECASE)
            if target_m:
                call_dict["target"] = target_m.group(1).strip("\r\n")

            repl_m = re.search(r"<replacement>(.*?)</replacement>", block, re.DOTALL | re.IGNORECASE)
            if repl_m:
                call_dict["replacement"] = repl_m.group(1).strip("\r\n")

            cmd_m = re.search(r"<command>(.*?)</command>", block, re.DOTALL | re.IGNORECASE)
            if cmd_m:
                call_dict["command"] = cmd_m.group(1).strip()

            calls.append(call_dict)
        return calls

    def render_checklist_panel(self) -> Panel:
        table = Table(box=box.SIMPLE_HEAD, expand=True, show_header=False)
        table.add_column("Status", width=6)
        table.add_column("Tarefa", style="white")

        for item in self.checklist:
            if item.status == "done":
                st = "[bold green]✓[/bold green]"
                txt = f"[strike dim green]{item.text}[/strike dim green]"
            elif item.status == "in_progress":
                st = "[bold yellow]▶[/bold yellow]"
                txt = f"[bold yellow]{item.text}[/bold yellow]"
            elif item.status == "error":
                st = "[bold red]✗[/bold red]"
                txt = f"[bold red]{item.text}[/bold red]"
            else:
                st = "[bright_black]○[/bright_black]"
                txt = f"[dim]{item.text}[/dim]"
            table.add_row(st, txt)

        return Panel(table, title="[bold cyan]📋 Roteiro de Execução & Checklist[/bold cyan]", border_style="cyan")

    async def execute_tool_call(self, call: Dict[str, str]) -> Dict[str, Any]:
        action = call.get("action")
        
        if action == "create_dir":
            p = call.get("path", "")
            return self.tools.create_directory(p)

        elif action == "create_file":
            p = call.get("path", "")
            c = call.get("content", "")
            res = self.tools.write_file(p, c, overwrite=True)
            # Run immediate syntax verification
            syntax = self.tools.check_syntax(p)
            res["syntax"] = syntax
            return res

        elif action == "edit_file":
            p = call.get("path", "")
            tgt = call.get("target", "")
            repl = call.get("replacement", "")
            res = self.tools.edit_file_block(p, tgt, repl)
            if res.get("success"):
                syntax = self.tools.check_syntax(p)
                res["syntax"] = syntax
            return res

        elif action == "run_command":
            cmd = call.get("command", "")
            return self.tools.execute_command(cmd)

        return {"success": False, "error": f"Ação desconhecida: {action}"}

    async def run_autonomous_task(
        self,
        user_prompt: str,
        session_id: str,
        max_auto_fix_loops: int = 3
    ) -> Dict[str, Any]:
        """
        Executes a task with autonomous tool calls, live checklist, and auto-fix loop.
        """
        self.checklist.clear()
        self.tools.changelog.clear()

        # Step 1: Initial Prompt with System Engine Context
        ws_info = self.tools.get_workspace_summary()
        prompt_with_ctx = (
            f"{self.get_system_instructions()}\n\n"
            f"### CONTEXTO DA PASTA ATUAL DO PROJETO:\n{ws_info}\n\n"
            f"### SOLICITAÇÃO DO USUÁRIO:\n{user_prompt}"
        )

        full_response = ""
        current_session = session_id
        parent_msg_id = None

        console.print(f"\n[bold cyan]🚀 Iniciando Agente de Engenharia Autônomo na pasta:[/bold cyan] [yellow]{self.tools.workspace}[/yellow]\n")

        # Main agent execution loop (up to max_auto_fix_loops)
        for loop_idx in range(max_auto_fix_loops + 1):
            thought_text = ""
            response_text = ""

            with Live(console=console, refresh_per_second=8) as live:
                def update_view():
                    elems = []
                    if self.checklist:
                        elems.append(self.render_checklist_panel())
                    if thought_text:
                        elems.append(
                            Panel(
                                Text(thought_text, style="dim cyan"),
                                title="[bold cyan]🧠 Raciocínio Profundo[/bold cyan]",
                                border_style="cyan"
                            )
                        )
                    if response_text:
                        # Clean out raw tags for neat markdown view
                        clean_text = re.sub(r"<tool_call>.*?</tool_call>", "[dim]⚙️ [Executando Ferramenta...][/dim]", response_text, flags=re.DOTALL)
                        elems.append(
                            Panel(
                                clean_text,
                                title=f"[bold green]DeepSeek Agent (Etapa {loop_idx + 1})[/bold green]",
                                border_style="green"
                            )
                        )
                    if not elems:
                        elems.append(Text("Aguardando resposta do DeepSeek...", style="dim"))
                    live.update(Group(*elems))

                async for chunk in self.client.chat_completion(
                    session_id=current_session,
                    prompt=prompt_with_ctx if loop_idx == 0 else prompt_with_ctx,
                    parent_message_id=parent_msg_id,
                    thinking_enabled=True
                ):
                    if chunk.chunk_type == "ready":
                        if chunk.message_id:
                            parent_msg_id = chunk.message_id
                    elif chunk.chunk_type == "think":
                        thought_text += chunk.content
                        update_view()
                    elif chunk.chunk_type == "response":
                        response_text += chunk.content
                        # Live parse checklist as it streams
                        self.parse_checklist(response_text)
                        update_view()
                    elif chunk.chunk_type == "finish":
                        if chunk.message_id:
                            parent_msg_id = chunk.message_id
                        update_view()

            full_response = response_text
            self.parse_checklist(full_response)

            # Step 2: Parse and Execute Tools
            tool_calls = self.parse_tool_calls(full_response)
            if not tool_calls:
                # No more tools called, task finished!
                break

            console.print(f"\n[bold yellow]⚡ Executando {len(tool_calls)} ações detectadas...[/bold yellow]")
            errors_detected = []

            for call in tool_calls:
                act = call.get("action")
                path = call.get("path") or call.get("command") or ""
                console.print(f"  [cyan]• Ação:[/cyan] [bold]{act}[/bold] ➔ [white]{path}[/white]")
                
                result = await self.execute_tool_call(call)

                # Check for errors in file write / surgical edit
                if not result.get("success", True):
                    err_msg = result.get("error", "Erro desconhecido")
                    console.print(f"    [red]✗ Falha:[/red] {err_msg}")
                    errors_detected.append(f"Ação {act} em '{path}' falhou: {err_msg}")
                else:
                    console.print(f"    [green]✓ Concluído com sucesso[/green]")

                # Check for syntax error
                syntax = result.get("syntax", {})
                if syntax and not syntax.get("valid", True):
                    syntax_err = syntax.get("error", "Erro de sintaxe")
                    console.print(f"    [red]✗ Erro de Sintaxe ({syntax.get('language')}):[/red] {syntax_err}")
                    errors_detected.append(f"Arquivo '{path}' contém erro de sintaxe ({syntax.get('language')}): {syntax_err}")

                # Check for command execution errors
                if act == "run_command" and not result.get("success"):
                    stderr = result.get("stderr") or result.get("stdout") or "Comando encerrou com falha"
                    console.print(f"    [red]✗ Erro no comando:[/red] {stderr[:200]}")
                    errors_detected.append(f"Comando '{path}' falhou com código {result.get('returncode')}: {stderr}")

            # Step 3: Auto-Fix Loop
            if errors_detected:
                if loop_idx < max_auto_fix_loops:
                    console.print(f"\n[bold red]🛠️ DETECTADO ERRO NA EXECUÇÃO. ACIONANDO MODO AUTO-FIX (Tentativa {loop_idx + 1}/{max_auto_fix_loops})...[/bold red]")
                    error_summary = "\n".join(f"- {e}" for e in errors_detected)
                    prompt_with_ctx = (
                        f"Ocorreram os seguintes erros na execução das ferramentas:\n{error_summary}\n\n"
                        f"Por favor, analise a causa raiz e corrija o código de forma cirúrgica utilizando <tool_call><action>edit_file</action>... ou <tool_call><action>create_file</action>...\n"
                        f"Não repita o mesmo erro."
                    )
                    continue
                else:
                    console.print("[bold red]Limite de tentativas do Auto-Fix atingido. Intervenção manual pode ser necessária.[/bold red]")
                    break
            else:
                # All tools succeeded cleanly!
                break

        # Output Final Checklist & Changelog
        if self.checklist:
            for item in self.checklist:
                item.status = "done"  # mark all as completed
            console.print(self.render_checklist_panel())

        changelog_md = self.tools.changelog.get_summary()
        console.print(Panel(changelog_md, title="[bold green]📋 Resumo de Entregas & Changelog[/bold green]", border_style="green"))

        return {
            "response": full_response,
            "checklist": self.checklist,
            "changelog": changelog_md
        }
