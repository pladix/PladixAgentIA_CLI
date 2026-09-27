"""
Multi-Agent Orchestrator for PladixAgentIA_CLI
Allows multiple agents to work concurrently with different contexts and sessions.

Desenvolvido por PladixOficial
Telegram: t.me/pladixoficial
"""

import asyncio
from typing import Dict, Any, List, Optional, Callable, AsyncGenerator
from dataclasses import dataclass, field

from .client import DeepSeekClient, StreamChunk
from .memory import MemoryManager
from .tools import IDETools
from .mentoria_pladix import MENTORIA_PLADIX_PROMPT


@dataclass
class AgentRole:
    name: str
    icon: str
    description: str
    system_prompt: str


DEFAULT_ROLES = {
    "architect": AgentRole(
        name="Architect",
        icon="🏗️",
        description="Especialista em arquitetura de software, design patterns e planejamento estrutural.",
        system_prompt=(
            "Você é o Arquiteto de Software Líder. Seu papel é estruturar sistemas, "
            "definir padrões de projeto, planejar divisão de arquivos, dependências e fluxo de dados. "
            "Forneça planos claros, estruturados e especificações de código."
        )
    ),
    "coder": AgentRole(
        name="Coder",
        icon="💻",
        description="Desenvolvedor sênior focado em implementação de código limpo, eficiente e moderno.",
        system_prompt=(
            "Você é o Desenvolvedor Sênior. Seu papel é implementar código de alta performance, "
            "escrever funções completas sem placeholders, seguir as melhores práticas e estruturar arquivos funcionais."
        )
    ),
    "reviewer": AgentRole(
        name="Reviewer",
        icon="🔍",
        description="Auditor de código focado em segurança, performance e detecção de bugs.",
        system_prompt=(
            "Você é o Code Reviewer e Especialista em Segurança. Seu papel é inspecionar o código, "
            "identificar possíveis falhas de segurança, gargalos de performance, edge cases e recomendar melhorias pontuais."
        )
    ),
    "tester": AgentRole(
        name="Tester",
        icon="🧪",
        description="Engenheiro de QA focado em testes unitários, testes de integração e validação.",
        system_prompt=(
            "Você é o Engenheiro de Testes de Software (QA). Seu papel é escrever testes unitários completos, "
            "cobertura de casos extremos e garantir que o software seja robusto e confiável."
        )
    ),
    "debugger": AgentRole(
        name="Debugger",
        icon="⚡",
        description="Especialista em análise de falhas, tracebacks e resolução rápida de bugs.",
        system_prompt=(
            "Você é o Especialista em Debugging. Seu papel é analisar mensagens de erro, tracebacks "
            "e saídas de terminal, identificando a causa raiz e fornecendo o patch exato de correção."
        )
    ),
    "pladix_coder": AgentRole(
        name="PladixOficial Coder PHP",
        icon="🔥",
        description="Especialista Supremo em PHP, API Development e CHKs. Treinado por mentoria PladixOficial.",
        system_prompt=MENTORIA_PLADIX_PROMPT
    )
}


class Agent:
    def __init__(
        self,
        role_id: str,
        role: AgentRole,
        client: DeepSeekClient,
        memory: MemoryManager,
        tools: IDETools,
        session_id: Optional[str] = None
    ):
        self.role_id = role_id
        self.role = role
        self.client = client
        self.memory = memory
        self.tools = tools
        self.session_id = session_id
        self.last_message_id: Optional[int] = None
        self.status: str = "Pronto"
        self.last_thought: str = ""
        self.last_response: str = ""
        self.history: List[Dict[str, Any]] = []

    async def init_session(self) -> str:
        if not self.session_id:
            sess = await self.client.create_chat_session(agent="chat")
            self.session_id = sess["id"]
            self.memory.record_session(
                session_id=self.session_id,
                title=f"Agent {self.role.name}",
                agent_name=self.role.name,
                last_msg_id=None
            )
        return self.session_id

    async def execute_task(
        self,
        task: str,
        include_workspace_context: bool = True,
        thinking_enabled: bool = True,
        on_chunk: Optional[Callable[[str, StreamChunk], None]] = None
    ) -> str:
        """
        Executes a task with this agent, using its dedicated DeepSeek session.
        """
        if not self.session_id:
            await self.init_session()

        self.status = "Pensando..."
        
        # Build prompt with role context and memory
        prompt_parts = []
        
        # If first message in session, inject system persona
        if self.last_message_id is None:
            sys_ctx = self.memory.build_system_context(self.role.name, self.role.system_prompt)
            prompt_parts.append(sys_ctx)
            prompt_parts.append("\n" + "="*40 + "\n")

        if include_workspace_context:
            ws_summary = self.tools.get_workspace_summary()
            prompt_parts.append(f"### CONTEXTO DO WORKSPACE:\n{ws_summary}\n")

        prompt_parts.append(f"### TAREFA DO USUÁRIO:\n{task}")
        full_prompt = "\n".join(prompt_parts)

        thought_chunks = []
        response_chunks = []

        try:
            async for chunk in self.client.chat_completion(
                session_id=self.session_id,
                prompt=full_prompt,
                parent_message_id=self.last_message_id,
                thinking_enabled=thinking_enabled
            ):
                if chunk.chunk_type == "ready":
                    if chunk.message_id:
                        self.last_message_id = chunk.message_id
                elif chunk.chunk_type == "think":
                    thought_chunks.append(chunk.content)
                    self.status = "Pensamento Profundo..."
                elif chunk.chunk_type == "response":
                    response_chunks.append(chunk.content)
                    self.status = "Respondendo..."
                elif chunk.chunk_type == "finish":
                    if chunk.message_id:
                        self.last_message_id = chunk.message_id
                        self.memory.update_session_msg_id(self.session_id, self.last_message_id)

                if on_chunk:
                    on_chunk(self.role.name, chunk)

            self.last_thought = "".join(thought_chunks)
            self.last_response = "".join(response_chunks)
            self.status = "Concluído"

            self.history.append({
                "task": task,
                "thought": self.last_thought,
                "response": self.last_response
            })
            return self.last_response

        except Exception as e:
            self.status = f"Erro: {e}"
            raise e


class AgentOrchestrator:
    def __init__(self, client: DeepSeekClient, memory: MemoryManager, tools: IDETools):
        self.client = client
        self.memory = memory
        self.tools = tools
        self.agents: Dict[str, Agent] = {}
        self._setup_default_agents()

    def _setup_default_agents(self):
        for role_id, role in DEFAULT_ROLES.items():
            self.agents[role_id] = Agent(
                role_id=role_id,
                role=role,
                client=self.client,
                memory=self.memory,
                tools=self.tools
            )

    def get_agent(self, role_id: str) -> Optional[Agent]:
        return self.agents.get(role_id.lower())

    def create_custom_agent(self, name: str, description: str, system_prompt: str, icon: str = "🤖") -> Agent:
        role_id = name.lower().replace(" ", "_")
        role = AgentRole(name=name, icon=icon, description=description, system_prompt=system_prompt)
        agent = Agent(role_id=role_id, role=role, client=self.client, memory=self.memory, tools=self.tools)
        self.agents[role_id] = agent
        return agent

    async def run_parallel_tasks(
        self,
        agent_tasks: Dict[str, str],
        on_chunk: Optional[Callable[[str, StreamChunk], None]] = None
    ) -> Dict[str, str]:
        """
        Runs multiple agent tasks simultaneously across different sessions.
        """
        tasks = []
        agent_keys = []

        for role_id, task in agent_tasks.items():
            agent = self.get_agent(role_id)
            if agent:
                agent_keys.append(role_id)
                tasks.append(agent.execute_task(task, on_chunk=on_chunk))

        results = await asyncio.gather(*tasks, return_exceptions=True)
        out = {}
        for role_id, res in zip(agent_keys, results):
            out[role_id] = str(res)
        return out

