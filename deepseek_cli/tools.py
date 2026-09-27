"""
IDE Programming Tools & Surgical File Manipulation
Provides filesystem, terminal, git, workspace inspection, and targeted code editing capabilities.

Desenvolvido por PladixOficial
Telegram: t.me/pladixoficial
"""

import os
import sys
import difflib
import subprocess
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime


class ChangelogEntry:
    def __init__(self, action: str, target: str, details: str = "", diff: str = ""):
        self.timestamp = datetime.now().strftime("%H:%M:%S")
        self.action = action  # "CREATE", "EDIT", "MKDIR", "COMMAND", "FIX"
        self.target = target
        self.details = details
        self.diff = diff


class ChangelogTracker:
    def __init__(self):
        self.entries: List[ChangelogEntry] = []

    def record(self, action: str, target: str, details: str = "", diff: str = ""):
        self.entries.append(ChangelogEntry(action, target, details, diff))

    def clear(self):
        self.entries.clear()

    def get_summary(self) -> str:
        if not self.entries:
            return "Nenhuma modificação registrada nesta sessão."

        lines = [
            "### 📋 REGISTRO DE ALTERAÇÕES (CHANGELOG)",
            f"*Data/Hora:* {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "| Horário | Ação | Arquivo / Alvo | Detalhes |",
            "| :--- | :--- | :--- | :--- |"
        ]

        for e in self.entries:
            icon = {
                "CREATE": "✨ Novo",
                "EDIT": "📝 Editado",
                "MKDIR": "📁 Pasta",
                "COMMAND": "⚡ Executado",
                "FIX": "🛠️ Corrigido"
            }.get(e.action, e.action)
            lines.append(f"| {e.timestamp} | {icon} | `{e.target}` | {e.details} |")

        diffs = [e for e in self.entries if e.diff]
        if diffs:
            lines.append("\n#### 🔍 Diferenças Cirúrgicas Aplicadas (Diffs):")
            for d in diffs:
                lines.append(f"\n**Arquivo:** `{d.target}`\n```diff\n{d.diff}\n```")

        return "\n".join(lines)


import shutil

def detect_php_binary(custom_path: Optional[str] = None) -> Optional[str]:
    """
    Detects PHP executable across standard Windows installation paths (XAMPP, Laragon, PHP root, PATH).
    """
    if custom_path and os.path.isfile(custom_path):
        return custom_path

    candidates = [
        r"C:\xampp\php\php.exe",
        r"D:\xampp\php\php.exe",
        r"E:\xampp\php\php.exe",
        r"C:\php\php.exe",
        r"D:\php\php.exe",
        r"C:\Program Files\PHP\php.exe",
        r"C:\Program Files (x86)\PHP\php.exe",
    ]

    # Laragon dynamic search
    if os.path.exists(r"C:\laragon\bin\php"):
        for root, dirs, files in os.walk(r"C:\laragon\bin\php"):
            if "php.exe" in files:
                candidates.insert(0, os.path.join(root, "php.exe"))
                break

    for cand in candidates:
        if os.path.isfile(cand):
            return cand

    # Check system PATH
    found = shutil.which("php")
    if found:
        return found

    return None


class IDETools:
    def __init__(self, workspace_path: Optional[str] = None, php_path: Optional[str] = None):
        self.workspace = Path(workspace_path or os.getcwd()).resolve()
        self.changelog = ChangelogTracker()
        self.php_binary = detect_php_binary(php_path)
        self.python_binary = sys.executable

        # Automatically add PHP directory to environment PATH so child processes run cleanly
        if self.php_binary:
            php_dir = os.path.dirname(self.php_binary)
            cur_path = os.environ.get("PATH", "")
            if php_dir.lower() not in cur_path.lower():
                os.environ["PATH"] = php_dir + os.pathsep + cur_path

    def set_php_path(self, path: str):
        if path and os.path.isfile(path):
            self.php_binary = path
            php_dir = os.path.dirname(path)
            cur_path = os.environ.get("PATH", "")
            if php_dir.lower() not in cur_path.lower():
                os.environ["PATH"] = php_dir + os.pathsep + cur_path
            return True
        return False

    def set_workspace(self, path: str, create_if_missing: bool = True) -> Dict[str, Any]:
        p = Path(path).resolve()
        if not p.exists():
            if create_if_missing:
                try:
                    p.mkdir(parents=True, exist_ok=True)
                except Exception as e:
                    return {"success": False, "error": f"Não foi possível criar a pasta: {e}"}
            else:
                return {"success": False, "error": f"Diretório não encontrado: {path}"}

        self.workspace = p
        os.chdir(str(p))
        return {"success": True, "workspace": str(self.workspace)}

    def create_directory(self, rel_path: str) -> Dict[str, Any]:
        target = (self.workspace / rel_path).resolve()
        try:
            target.mkdir(parents=True, exist_ok=True)
            self.changelog.record("MKDIR", rel_path, "Diretório estruturado com sucesso")
            return {"success": True, "path": str(target.relative_to(self.workspace))}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def list_files(self, rel_path: str = ".", max_depth: int = 3) -> Dict[str, Any]:
        target = (self.workspace / rel_path).resolve()
        if not target.exists():
            return {"error": f"Caminho não existe: {rel_path}"}

        items = []
        try:
            for root, dirs, files in os.walk(target):
                rel_root = Path(root).relative_to(target)
                depth = len(rel_root.parts)
                if depth > max_depth:
                    continue
                # Skip hidden directories like .git, node_modules, __pycache__, .venv
                dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ("node_modules", "__pycache__", "vendor")]
                for d in dirs:
                    p = Path(root) / d
                    items.append({
                        "name": d,
                        "type": "dir",
                        "path": str(p.relative_to(self.workspace)).replace("\\", "/")
                    })
                for f in files:
                    if f.startswith("."):
                        continue
                    p = Path(root) / f
                    items.append({
                        "name": f,
                        "type": "file",
                        "size": p.stat().st_size,
                        "path": str(p.relative_to(self.workspace)).replace("\\", "/")
                    })
        except Exception as e:
            return {"error": str(e)}

        return {"workspace": str(self.workspace), "items": items}

    def read_file(self, rel_path: str, start_line: Optional[int] = None, end_line: Optional[int] = None) -> Dict[str, Any]:
        target = (self.workspace / rel_path).resolve()
        if not target.exists():
            return {"error": f"Arquivo não encontrado: {rel_path}"}
        if target.is_dir():
            return {"error": f"{rel_path} é um diretório, não um arquivo"}

        try:
            with open(target, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()

            total_lines = len(lines)
            s = (start_line - 1) if (start_line and start_line > 0) else 0
            e = end_line if (end_line and end_line <= total_lines) else total_lines

            content = "".join(lines[s:e])
            return {
                "path": str(target.relative_to(self.workspace)).replace("\\", "/"),
                "total_lines": total_lines,
                "start_line": s + 1,
                "end_line": e,
                "content": content
            }
        except Exception as ex:
            return {"error": str(ex)}

    def write_file(self, rel_path: str, content: str, overwrite: bool = True) -> Dict[str, Any]:
        target = (self.workspace / rel_path).resolve()
        file_existed = target.exists()

        if file_existed and not overwrite:
            return {"success": False, "error": f"Arquivo já existe e overwrite=False: {rel_path}"}

        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            old_content = ""
            if file_existed:
                try:
                    with open(target, "r", encoding="utf-8", errors="replace") as fp:
                        old_content = fp.read()
                except Exception:
                    pass

            with open(target, "w", encoding="utf-8") as f:
                f.write(content)

            diff_str = ""
            if file_existed and old_content:
                diff_lines = list(difflib.unified_diff(
                    old_content.splitlines(keepends=True),
                    content.splitlines(keepends=True),
                    fromfile=f"a/{rel_path}",
                    tofile=f"b/{rel_path}",
                    n=2
                ))
                diff_str = "".join(diff_lines[:40])

            action = "EDIT" if file_existed else "CREATE"
            details = f"{len(content.splitlines())} linhas escritas ({len(content.encode('utf-8'))} bytes)"
            self.changelog.record(action, rel_path, details, diff_str)

            return {
                "success": True,
                "path": str(target.relative_to(self.workspace)).replace("\\", "/"),
                "action": action,
                "bytes_written": len(content.encode("utf-8")),
                "lines": len(content.splitlines())
            }
        except Exception as ex:
            return {"success": False, "error": str(ex)}

    def edit_file_block(self, rel_path: str, target_block: str, replacement_block: str) -> Dict[str, Any]:
        """
        Surgically replaces a specific block of text/code in a file without altering the rest.
        """
        target = (self.workspace / rel_path).resolve()
        if not target.exists():
            return {"success": False, "error": f"Arquivo não encontrado para edição: {rel_path}"}

        try:
            with open(target, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()

            normalized_target = target_block.replace("\r\n", "\n")
            normalized_content = content.replace("\r\n", "\n")

            occurrences = normalized_content.count(normalized_target)
            if occurrences == 0:
                # Try trimmed line match
                trimmed_target = "\n".join(line.strip() for line in normalized_target.splitlines() if line.strip())
                trimmed_content = "\n".join(line.strip() for line in normalized_content.splitlines() if line.strip())
                if trimmed_target in trimmed_content:
                    return {"success": False, "error": f"Bloco alvo encontrado com variações de indentação/espaçamento. Forneça linhas de contexto exatas."}
                return {"success": False, "error": f"O bloco especificado não foi encontrado no arquivo {rel_path}."}

            if occurrences > 1:
                return {
                    "success": False,
                    "error": f"O bloco especificado ocorre {occurrences} vezes no arquivo. Forneça linhas adicionais de contexto antes ou depois para torná-lo único."
                }

            normalized_replacement = replacement_block.replace("\r\n", "\n")
            new_content = normalized_content.replace(normalized_target, normalized_replacement, 1)

            diff_lines = list(difflib.unified_diff(
                normalized_content.splitlines(keepends=True),
                new_content.splitlines(keepends=True),
                fromfile=f"a/{rel_path}",
                tofile=f"b/{rel_path}",
                n=3
            ))
            diff_str = "".join(diff_lines[:40])

            with open(target, "w", encoding="utf-8") as f:
                f.write(new_content)

            self.changelog.record("EDIT", rel_path, "Ajuste cirúrgico pontual aplicado", diff_str)

            return {
                "success": True,
                "path": str(target.relative_to(self.workspace)).replace("\\", "/"),
                "diff": diff_str
            }

        except Exception as ex:
            return {"success": False, "error": str(ex)}

    def execute_command(self, command: str, timeout: int = 60) -> Dict[str, Any]:
        try:
            proc = subprocess.run(
                command,
                shell=True,
                cwd=str(self.workspace),
                capture_output=True,
                text=True,
                timeout=timeout
            )
            stdout = proc.stdout.strip()
            stderr = proc.stderr.strip()
            success = (proc.returncode == 0)

            detail = f"exit {proc.returncode}"
            if not success:
                detail += f" - {stderr[:80]}"

            self.changelog.record("COMMAND", command, detail)

            return {
                "command": command,
                "returncode": proc.returncode,
                "stdout": stdout,
                "stderr": stderr,
                "success": success
            }
        except subprocess.TimeoutExpired:
            self.changelog.record("COMMAND", command, f"Timeout após {timeout}s")
            return {"success": False, "error": f"Comando expirou após {timeout} segundos"}
        except Exception as ex:
            return {"success": False, "error": str(ex)}

    def check_syntax(self, rel_path: str) -> Dict[str, Any]:
        """
        Validates syntax of modified file depending on extension.
        """
        target = (self.workspace / rel_path).resolve()
        if not target.exists():
            return {"valid": False, "error": "Arquivo não existe"}

        ext = target.suffix.lower()

        # Python
        if ext == ".py":
            cmd = f'"{sys.executable}" -m py_compile "{target}"'
            res = self.execute_command(cmd)
            if not res.get("success"):
                return {"valid": False, "language": "Python", "error": res.get("stderr") or res.get("stdout")}
            return {"valid": True, "language": "Python"}

        # JSON
        elif ext == ".json":
            try:
                with open(target, "r", encoding="utf-8") as fp:
                    json.load(fp)
                return {"valid": True, "language": "JSON"}
            except Exception as e:
                return {"valid": False, "language": "JSON", "error": str(e)}

        # Node / JS
        elif ext in (".js", ".mjs"):
            res = self.execute_command(f'node --check "{target}"')
            if "node" not in res.get("stderr", "").lower() and res.get("returncode") != 0:
                return {"valid": False, "language": "JavaScript", "error": res.get("stderr")}
            return {"valid": True, "language": "JavaScript"}

        # PHP
        elif ext == ".php":
            php_bin = self.php_binary or "php"
            res = self.execute_command(f'"{php_bin}" -l "{target}"')
            if res.get("returncode") == 0 and "No syntax errors" in res.get("stdout", ""):
                return {"valid": True, "language": "PHP"}
            elif res.get("returncode") != 0:
                err_text = res.get("stderr") or res.get("stdout") or ""
                # Se php não estiver instalado, não acusar erro fatal no código
                if "não é reconhecido" in err_text or "not recognized" in err_text:
                    return {
                        "valid": True,
                        "language": "PHP",
                        "warning": "Interpretador PHP não configurado para testes de sintaxe locais."
                    }
                return {"valid": False, "language": "PHP", "error": err_text}

        return {"valid": True, "language": "Other"}

    def execute_script(self, rel_path: str, args: str = "") -> Dict[str, Any]:
        """
        Executes a script (PHP or Python) directly and returns output logs.
        """
        target = (self.workspace / rel_path).resolve()
        if not target.exists():
            return {"success": False, "error": f"Arquivo não encontrado: {rel_path}"}
        ext = target.suffix.lower()
        if ext == ".php":
            bin_cmd = self.php_binary or "php"
            cmd = f'"{bin_cmd}" "{target}" {args}'.strip()
        elif ext == ".py":
            cmd = f'"{sys.executable}" "{target}" {args}'.strip()
        else:
            return {"success": False, "error": f"Execução direta não suportada para arquivos {ext}"}
        
        return self.execute_command(cmd, timeout=30)


    def get_workspace_summary(self) -> str:
        files_by_ext = {}
        total_files = 0
        total_dirs = 0

        for root, dirs, files in os.walk(self.workspace):
            dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ("node_modules", "vendor", "__pycache__", ".venv")]
            total_dirs += len(dirs)
            for f in files:
                if f.startswith("."):
                    continue
                total_files += 1
                ext = Path(f).suffix.lower() or "sem extensão"
                files_by_ext[ext] = files_by_ext.get(ext, 0) + 1

        summary = [
            f"Diretório Raiz: {self.workspace}",
            f"Total de Arquivos: {total_files} | Pastas: {total_dirs}",
            "Linguagens/Extensões: " + ", ".join(f"{ext} ({cnt})" for ext, cnt in sorted(files_by_ext.items(), key=lambda x: -x[1])[:8])
        ]
        return "\n".join(summary)
