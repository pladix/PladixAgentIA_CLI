"""
Memory Management & Context Engine
Desenvolvido por PladixOficial
Telegram: t.me/pladixoficial
"""

import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

MEMORY_DIR = Path.home() / ".deepseek_ide"
MEMORY_FILE = MEMORY_DIR / "project_memory.json"


class MemoryManager:
    def __init__(self, workspace_path: str):
        self.workspace_path = workspace_path
        MEMORY_DIR.mkdir(parents=True, exist_ok=True)
        self.notes: List[Dict[str, Any]] = []
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self.project_context: Dict[str, Any] = {
            "tech_stack": [],
            "architecture_notes": [],
            "custom_instructions": []
        }
        self.load()

    def _get_key(self) -> str:
        return str(Path(self.workspace_path).resolve())

    def load(self) -> None:
        if MEMORY_FILE.exists():
            try:
                with open(MEMORY_FILE, "r", encoding="utf-8") as f:
                    all_data = json.load(f)
                    ws_data = all_data.get(self._get_key(), {})
                    self.notes = ws_data.get("notes", [])
                    self.sessions = ws_data.get("sessions", {})
                    self.project_context = ws_data.get("project_context", self.project_context)
            except Exception:
                pass

    def save(self) -> None:
        all_data = {}
        if MEMORY_FILE.exists():
            try:
                with open(MEMORY_FILE, "r", encoding="utf-8") as f:
                    all_data = json.load(f)
            except Exception:
                all_data = {}

        all_data[self._get_key()] = {
            "notes": self.notes,
            "sessions": self.sessions,
            "project_context": self.project_context,
            "last_updated": datetime.now().isoformat()
        }

        with open(MEMORY_FILE, "w", encoding="utf-8") as f:
            json.dump(all_data, f, indent=2, ensure_ascii=False)

    def add_note(self, content: str, category: str = "general") -> None:
        self.notes.append({
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "category": category,
            "content": content
        })
        self.save()

    def get_notes(self) -> List[Dict[str, Any]]:
        return self.notes

    def clear_notes(self) -> None:
        self.notes.clear()
        self.save()

    def record_session(self, session_id: str, title: str, agent_name: str, last_msg_id: Optional[int] = None) -> None:
        self.sessions[session_id] = {
            "title": title,
            "agent": agent_name,
            "last_message_id": last_msg_id,
            "updated_at": datetime.now().isoformat()
        }
        self.save()

    def update_session_msg_id(self, session_id: str, last_msg_id: int) -> None:
        if session_id in self.sessions:
            self.sessions[session_id]["last_message_id"] = last_msg_id
            self.sessions[session_id]["updated_at"] = datetime.now().isoformat()
            self.save()

    def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        return self.sessions.get(session_id)

    def build_system_context(self, agent_role: str, agent_description: str) -> str:
        """
        Builds a rich context header including role, guidelines, and memory.
        """
        lines = [
            f"### IDENTIDADE DO AGENTE: {agent_role.upper()}",
            agent_description,
            "",
            "### DIRETRIZES DO DESENVOLVEDOR",
            "- Desenvolvido por: PladixOficial (t.me/pladixoficial)",
            "- Você atua como um assistente de engenharia de software de ponta dentro de um ambiente IDE CLI.",
            "- Escreva código limpo, moderno, robusto e livre de erros.",
            "- Quando instruído a criar ou modificar arquivos, produza código completo e pronto para execução.",
            "- Forneça explicações técnicas concisas e diretas.",
        ]

        if self.notes:
            lines.append("\n### MEMÓRIA DE LONGO PRAZO DO PROJETO:")
            for n in self.notes[-8:]:  # last 8 notes
                lines.append(f"- [{n['category']}] {n['content']}")

        return "\n".join(lines)
