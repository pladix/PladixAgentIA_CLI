import os
import sys
import json
import asyncio
import re
import time
import shutil
from pathlib import Path
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
import webview
import threading

# Import engine logic
ROOT_PROJECT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(ROOT_PROJECT_PATH)

from deepseek_cli.config import Config
from deepseek_cli.client import DeepSeekClient
from deepseek_cli.tools import IDETools, detect_php_binary
from deepseek_cli.memory import MemoryManager
from deepseek_cli.agents import AgentOrchestrator, DEFAULT_ROLES
from deepseek_cli.mentoria_pladix import MENTORIA_PLADIX_PROMPT
from deepseek_cli.engine import ProjectEngine

app = FastAPI(title="PladixAgentIA GUI Server")

# Mount static files
static_dir = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")

config = Config()
tools = IDETools(php_path=config.php_path)
client = DeepSeekClient(config)
memory = MemoryManager(str(tools.workspace))
orchestrator = AgentOrchestrator(client, memory, tools)
project_engine = ProjectEngine(client, tools, memory)

# Save detected PHP to config if not saved yet
if tools.php_binary and not config.php_path:
    config.php_path = tools.php_binary
    config.save()

pladix_mode = True
current_role = "pladix_coder"

INTERNAL_IGNORE_DIRS = {'.git', '__pycache__', 'node_modules', '.venv', 'vendor', 'deepseek_cli', 'deepseek_gui'}
INTERNAL_IGNORE_FILES = {'iniciar_cli.bat', 'iniciar_gui.bat', 'main.py', 'README.md', 'requirements.txt'}

@app.get("/")
async def get():
    with open(os.path.join(static_dir, "index.html"), "r", encoding="utf-8") as f:
        return HTMLResponse(f.read())

def get_file_tree(workspace: str) -> List[Dict[str, Any]]:
    items = []
    ws_path = os.path.abspath(workspace)
    is_root = (ws_path == ROOT_PROJECT_PATH)

    try:
        for entry in os.scandir(ws_path):
            name = entry.name
            if name.startswith('.'):
                continue
            if is_root and name in INTERNAL_IGNORE_DIRS:
                continue
            if is_root and name in INTERNAL_IGNORE_FILES:
                continue

            full_path = entry.path.replace('\\', '/')
            rel_path = os.path.relpath(entry.path, ws_path).replace('\\', '/')

            if entry.is_dir():
                child_count = 0
                try:
                    child_count = len([x for x in os.listdir(entry.path) if not x.startswith('.')])
                except Exception:
                    pass
                items.append({
                    "name": name,
                    "rel_path": rel_path,
                    "path": full_path,
                    "is_dir": True,
                    "ext": "folder",
                    "size": 0,
                    "count": child_count
                })
            else:
                ext = os.path.splitext(name)[1].lower()
                try:
                    size = entry.stat().st_size
                except Exception:
                    size = 0
                items.append({
                    "name": name,
                    "rel_path": rel_path,
                    "path": full_path,
                    "is_dir": False,
                    "ext": ext,
                    "size": size,
                    "count": 0
                })
    except Exception as e:
        print(f"Erro ao listar workspace: {e}")

    # Ordena: pastas primeiro, depois arquivos alfabeticamente
    items.sort(key=lambda x: (0 if x["is_dir"] else 1, x["name"].lower()))
    return items

def get_language_from_ext(ext: str) -> str:
    mapping = {
        '.py': 'python',
        '.js': 'javascript',
        '.ts': 'typescript',
        '.html': 'html',
        '.css': 'css',
        '.php': 'php',
        '.json': 'json',
        '.md': 'markdown',
        '.txt': 'plaintext',
        '.bat': 'bat',
        '.sh': 'shell',
        '.sql': 'sql',
        '.xml': 'xml',
        '.yml': 'yaml',
        '.yaml': 'yaml'
    }
    return mapping.get(ext.lower(), 'plaintext')

def get_php_version_info(php_path: Optional[str]) -> str:
    if not php_path or not os.path.isfile(php_path):
        return "PHP não configurado"
    try:
        import subprocess
        res = subprocess.run([php_path, "-v"], capture_output=True, text=True, timeout=5)
        if res.returncode == 0 and res.stdout:
            first_line = res.stdout.splitlines()[0]
            if "XAMPP" in php_path.upper():
                return f"{first_line} (XAMPP)"
            return first_line
    except Exception:
        pass
    return "PHP Detectado"

def choose_directory_native(initial_dir: str = "") -> str:
    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        root.withdraw()
        root.wm_attributes("-topmost", 1)
        folder = filedialog.askdirectory(
            initialdir=initial_dir or str(tools.workspace),
            title="PladixAgentIA - Selecione a Pasta de Trabalho (Workspace)"
        )
        root.destroy()
        return folder
    except Exception as e:
        print(f"Erro no seletor de pasta: {e}")
        return ""

def choose_file_native(initial_dir: str = "") -> Dict[str, Any]:
    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        root.withdraw()
        root.wm_attributes("-topmost", 1)
        filepath = filedialog.askopenfilename(
            initialdir=initial_dir or str(tools.workspace),
            title="PladixAgentIA - Selecione o Arquivo (.txt, .log, scripts)",
            filetypes=[
                ("Arquivos de Texto e Códigos", "*.txt;*.log;*.php;*.py;*.json;*.html;*.css;*.js;*.md;*.bat"),
                ("Arquivos TXT", "*.txt"),
                ("Scripts PHP", "*.php"),
                ("Todos os Arquivos", "*.*")
            ]
        )
        root.destroy()
        if filepath and os.path.exists(filepath):
            with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            return {
                "name": os.path.basename(filepath),
                "path": filepath.replace('\\', '/'),
                "content": content,
                "size": len(content.encode('utf-8'))
            }
        return {}
    except Exception as e:
        print(f"Erro no seletor de arquivo: {e}")
        return {}

def open_in_system_explorer(folder_path: str):
    try:
        os.startfile(folder_path)
    except Exception as e:
        print(f"Erro ao abrir explorer: {e}")

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    global pladix_mode, current_role, memory, project_engine
    prompt_task: Optional[asyncio.Task] = None
    cancel_event = asyncio.Event()

    async def safe_send(payload: Any) -> bool:
        try:
            if websocket.client_state != WebSocketState.CONNECTED:
                cancel_event.set()
                return False
            text = payload if isinstance(payload, str) else json.dumps(payload)
            await websocket.send_text(text)
            return True
        except (WebSocketDisconnect, RuntimeError, Exception):
            cancel_event.set()
            return False

    async def send_workspace_info():
        ws_str = str(tools.workspace)
        conteudo_path = os.path.join(ws_str, "conteudo.txt")
        has_conteudo = os.path.exists(conteudo_path)
        is_root = (os.path.abspath(ws_str) == ROOT_PROJECT_PATH)

        php_info = get_php_version_info(tools.php_binary)

        await safe_send({
            'type': 'workspace_info',
            'workspace': ws_str,
            'name': os.path.basename(ws_str) or ws_str,
            'summary': tools.get_workspace_summary(),
            'has_conteudo_txt': has_conteudo,
            'is_root': is_root,
            'pladix_mode': pladix_mode,
            'current_role': current_role,
            'php_detected': bool(tools.php_binary),
            'php_path': tools.php_binary or '',
            'php_info': php_info,
            'is_authenticated': config.is_authenticated(),
            'roles': [
                {"id": k, "name": v.name, "icon": v.icon, "description": v.description}
                for k, v in DEFAULT_ROLES.items()
            ]
        })

    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            m_type = msg.get('type')
            
            if m_type == 'init':
                tree = get_file_tree(str(tools.workspace))
                await send_workspace_info()
                await websocket.send_text(json.dumps({'type': 'file_tree', 'tree': tree}))
                
            elif m_type == 'refresh_files':
                tree = get_file_tree(str(tools.workspace))
                await send_workspace_info()
                await websocket.send_text(json.dumps({'type': 'file_tree', 'tree': tree}))

            elif m_type == 'browse_workspace':
                chosen = await asyncio.to_thread(choose_directory_native, str(tools.workspace))
                if chosen:
                    tools.set_workspace(chosen)
                    memory = MemoryManager(str(tools.workspace))
                    project_engine.memory = memory
                    project_engine.tools = tools
                    tree = get_file_tree(str(tools.workspace))
                    await send_workspace_info()
                    await websocket.send_text(json.dumps({'type': 'file_tree', 'tree': tree}))
                    await websocket.send_text(json.dumps({
                        'type': 'system_msg',
                        'content': f"Workspace alterado para: {tools.workspace}"
                    }))

            elif m_type == 'set_workspace':
                path = msg.get('path', '').strip()
                if path:
                    res = tools.set_workspace(path, create_if_missing=True)
                    if res.get("success"):
                        memory = MemoryManager(str(tools.workspace))
                        project_engine.memory = memory
                        project_engine.tools = tools
                        tree = get_file_tree(str(tools.workspace))
                        await send_workspace_info()
                        await websocket.send_text(json.dumps({'type': 'file_tree', 'tree': tree}))
                        await websocket.send_text(json.dumps({
                            'type': 'system_msg',
                            'content': f"Workspace definido com sucesso: {tools.workspace}"
                        }))
                    else:
                        await websocket.send_text(json.dumps({
                            'type': 'system_msg',
                            'content': f"Erro ao definir workspace: {res.get('error')}"
                        }))

            elif m_type == 'create_workspace_folder':
                folder_name = msg.get('folder_name', '').strip()
                if folder_name:
                    res = tools.create_directory(folder_name)
                    if res.get("success"):
                        if msg.get('switch_to', False):
                            new_ws = (tools.workspace / folder_name).resolve()
                            tools.set_workspace(str(new_ws))
                            memory = MemoryManager(str(tools.workspace))
                            project_engine.memory = memory
                            project_engine.tools = tools
                        tree = get_file_tree(str(tools.workspace))
                        await send_workspace_info()
                        await websocket.send_text(json.dumps({'type': 'file_tree', 'tree': tree}))
                        await websocket.send_text(json.dumps({
                            'type': 'system_msg',
                            'content': f"Pasta criada: {folder_name} (Workspace: {tools.workspace})"
                        }))
                    else:
                        await websocket.send_text(json.dumps({
                            'type': 'system_msg',
                            'content': f"Erro ao criar pasta: {res.get('error')}"
                        }))

            elif m_type == 'copy_conteudo_to_workspace':
                # Copia conteudo.txt da raiz para a pasta atual se não existir
                root_conteudo = os.path.join(ROOT_PROJECT_PATH, "conteudo.txt")
                target_conteudo = os.path.join(str(tools.workspace), "conteudo.txt")
                if os.path.exists(root_conteudo) and not os.path.exists(target_conteudo):
                    shutil.copy2(root_conteudo, target_conteudo)
                    tree = get_file_tree(str(tools.workspace))
                    await send_workspace_info()
                    await websocket.send_text(json.dumps({'type': 'file_tree', 'tree': tree}))
                    await websocket.send_text(json.dumps({
                        'type': 'system_msg',
                        'content': f"Arquivo conteudo.txt copiado com sucesso para {tools.workspace}"
                    }))

            elif m_type == 'open_in_explorer':
                await asyncio.to_thread(open_in_system_explorer, str(tools.workspace))

            elif m_type == 'browse_file':
                file_info = await asyncio.to_thread(choose_file_native, str(tools.workspace))
                if file_info:
                    await websocket.send_text(json.dumps({
                        'type': 'file_attached',
                        'name': file_info['name'],
                        'path': file_info['path'],
                        'content': file_info['content'],
                        'size': file_info['size']
                    }))
                    await websocket.send_text(json.dumps({
                        'type': 'system_msg',
                        'content': f"Arquivo anexado: {file_info['name']} ({file_info['size']} bytes)"
                    }))

            elif m_type == 'read_workspace_file':
                fname = msg.get('filename', 'conteudo.txt')
                target = (tools.workspace / fname).resolve()
                if not target.exists() and os.path.exists(os.path.join(ROOT_PROJECT_PATH, fname)):
                    target = Path(os.path.join(ROOT_PROJECT_PATH, fname))

                if target.exists() and target.is_file():
                    try:
                        with open(target, 'r', encoding='utf-8', errors='replace') as fp:
                            txt_content = fp.read()
                        await websocket.send_text(json.dumps({
                            'type': 'file_attached',
                            'name': target.name,
                            'path': str(target).replace('\\', '/'),
                            'content': txt_content,
                            'size': len(txt_content.encode('utf-8'))
                        }))
                        await websocket.send_text(json.dumps({
                            'type': 'system_msg',
                            'content': f"Conteúdo de '{target.name}' carregado ({len(txt_content.splitlines())} linhas)."
                        }))
                    except Exception as ex:
                        await websocket.send_text(json.dumps({
                            'type': 'system_msg',
                            'content': f"Erro ao ler '{target.name}': {ex}"
                        }))
                else:
                    await websocket.send_text(json.dumps({
                        'type': 'system_msg',
                        'content': f"Arquivo '{fname}' não encontrado no workspace atual."
                    }))

            elif m_type == 'create_file':
                filename = msg.get('filename', '').strip()
                file_content = msg.get('content', '')
                if filename:
                    res = tools.write_file(filename, file_content, overwrite=True)
                    if res.get("success"):
                        tree = get_file_tree(str(tools.workspace))
                        await websocket.send_text(json.dumps({'type': 'file_tree', 'tree': tree}))
                        ext = os.path.splitext(filename)[1].lower()
                        full_p = str((tools.workspace / filename).resolve()).replace('\\', '/')
                        await websocket.send_text(json.dumps({
                            'type': 'file_content',
                            'path': full_p,
                            'rel_path': filename,
                            'content': file_content,
                            'language': get_language_from_ext(ext)
                        }))
                        await websocket.send_text(json.dumps({
                            'type': 'system_msg',
                            'content': f"Arquivo '{filename}' criado e aberto no editor."
                        }))

            elif m_type == 'delete_file':
                target_path = msg.get('path', '')
                if target_path:
                    try:
                        p = Path(target_path).resolve()
                        if p.exists():
                            if p.is_dir():
                                shutil.rmtree(p)
                            else:
                                p.unlink()
                            tree = get_file_tree(str(tools.workspace))
                            await websocket.send_text(json.dumps({'type': 'file_tree', 'tree': tree}))
                            await websocket.send_text(json.dumps({
                                'type': 'system_msg',
                                'content': f"Excluído com sucesso: {p.name}"
                            }))
                    except Exception as e:
                        await websocket.send_text(json.dumps({
                            'type': 'system_msg',
                            'content': f"Erro ao excluir: {e}"
                        }))

            elif m_type == 'save_file':
                file_path = msg.get('path', '')
                content = msg.get('content', '')
                try:
                    if os.path.isabs(file_path):
                        target = Path(file_path).resolve()
                        rel = os.path.relpath(target, tools.workspace)
                    else:
                        rel = file_path
                        target = (tools.workspace / rel).resolve()

                    res = tools.write_file(rel, content, overwrite=True)
                    if res.get("success"):
                        syntax = tools.check_syntax(rel)
                        await websocket.send_text(json.dumps({
                            'type': 'file_saved',
                            'path': file_path,
                            'syntax': syntax
                        }))
                        tree = get_file_tree(str(tools.workspace))
                        await websocket.send_text(json.dumps({'type': 'file_tree', 'tree': tree}))
                    else:
                        await websocket.send_text(json.dumps({
                            'type': 'system_msg',
                            'content': f"Erro ao salvar arquivo: {res.get('error')}"
                        }))
                except Exception as e:
                    await websocket.send_text(json.dumps({
                        'type': 'system_msg',
                        'content': f"Erro ao salvar: {e}"
                    }))

            elif m_type == 'check_syntax':
                file_path = msg.get('path', '')
                if os.path.isabs(file_path):
                    rel = os.path.relpath(file_path, tools.workspace)
                else:
                    rel = file_path
                syntax = tools.check_syntax(rel)
                await websocket.send_text(json.dumps({
                    'type': 'syntax_result',
                    'path': file_path,
                    'syntax': syntax
                }))

            elif m_type == 'execute_file':
                file_path = msg.get('path', '')
                args = msg.get('args', '')
                if os.path.isabs(file_path):
                    rel = os.path.relpath(file_path, tools.workspace)
                else:
                    rel = file_path
                
                t_start = time.time()
                res = await asyncio.to_thread(tools.execute_script, rel, args)
                elapsed = round(time.time() - t_start, 3)

                await websocket.send_text(json.dumps({
                    'type': 'execution_result',
                    'path': file_path,
                    'stdout': res.get('stdout', ''),
                    'stderr': res.get('stderr', ''),
                    'returncode': res.get('returncode', 0),
                    'success': res.get('success', False),
                    'elapsed': elapsed
                }))

            elif m_type == 'get_settings':
                await websocket.send_text(json.dumps({
                    'type': 'settings_info',
                    'is_authenticated': config.is_authenticated(),
                    'token': config.token or '',
                    'php_path': tools.php_binary or '',
                    'php_version': get_php_version_info(tools.php_binary),
                    'python_path': sys.executable,
                    'python_version': sys.version.split()[0]
                }))

            elif m_type == 'save_settings':
                token = msg.get('token', '').strip()
                cookie = msg.get('cookie', '').strip()
                php_path = msg.get('php_path', '').strip()

                if token:
                    config.set_auth(token, cookie if cookie else None)
                if php_path:
                    config.php_path = php_path
                    tools.set_php_path(php_path)
                config.save()

                await websocket.send_text(json.dumps({
                    'type': 'system_msg',
                    'content': "Configurações e credenciais salvas com sucesso!"
                }))
                await send_workspace_info()

            elif m_type == 'auto_detect_php':
                detected = detect_php_binary()
                if detected:
                    tools.set_php_path(detected)
                    config.php_path = detected
                    config.save()
                    ver = get_php_version_info(detected)
                    await websocket.send_text(json.dumps({
                        'type': 'auto_detect_php_result',
                        'success': True,
                        'path': detected,
                        'version': ver,
                        'msg': f"PHP detectado com sucesso: {detected} ({ver})"
                    }))
                    await send_workspace_info()
                else:
                    await websocket.send_text(json.dumps({
                        'type': 'auto_detect_php_result',
                        'success': False,
                        'msg': "Não foi possível encontrar php.exe automaticamente nas pastas padrão (XAMPP/Laragon)."
                    }))

            elif m_type == 'toggle_pladix':
                pladix_mode = not pladix_mode
                current_role = "pladix_coder" if pladix_mode else "coder"
                status = "ATIVADO 🔥" if pladix_mode else "DESATIVADO"
                await send_workspace_info()
                await websocket.send_text(json.dumps({
                    'type': 'system_msg',
                    'content': f"Modo Pladix Coder: {status}"
                }))

            elif m_type == 'select_role':
                role_id = msg.get('role_id', 'pladix_coder')
                if role_id in DEFAULT_ROLES:
                    current_role = role_id
                    pladix_mode = (role_id == "pladix_coder")
                    role_info = DEFAULT_ROLES[role_id]
                    await send_workspace_info()
                    await websocket.send_text(json.dumps({
                        'type': 'system_msg',
                        'content': f"Agente Ativo alterado para: {role_info.icon} {role_info.name}"
                    }))

            elif m_type == 'clear_session':
                config.active_session_id = None
                config.save()
                await websocket.send_text(json.dumps({
                    'type': 'system_msg',
                    'content': "Nova sessão do DeepSeek iniciada. Contexto zerado."
                }))

            elif m_type == 'open_file':
                try:
                    fpath = msg['path']
                    with open(fpath, 'r', encoding='utf-8', errors='replace') as f:
                        content = f.read()
                    ext = os.path.splitext(fpath)[1].lower()
                    rel_p = os.path.relpath(fpath, str(tools.workspace)).replace('\\', '/')
                    await websocket.send_text(json.dumps({
                        'type': 'file_content',
                        'path': fpath,
                        'rel_path': rel_p,
                        'content': content,
                        'language': get_language_from_ext(ext)
                    }))
                except Exception as e:
                    await websocket.send_text(json.dumps({
                        'type': 'system_msg',
                        'content': f"Erro ao abrir arquivo: {e}"
                    }))

            elif m_type == 'validate_token':
                token = msg.get('token', '').strip()
                test_conf = Config()
                if token:
                    test_conf.set_auth(token)
                test_client = DeepSeekClient(test_conf)
                t_start = time.time()
                try:
                    sess = await test_client.create_chat_session(agent="chat")
                    latency = int((time.time() - t_start) * 1000)
                    if sess and "id" in sess:
                        if token:
                            config.set_auth(token)
                            config.active_session_id = sess["id"]
                            config.save()
                        await websocket.send_text(json.dumps({
                            'type': 'validate_token_result',
                            'valid': True,
                            'latency': latency,
                            'msg': f"✓ Conexão bem-sucedida! (Latência: {latency}ms | Sessão ativa: {sess['id'][:8]})"
                        }))
                    else:
                        await websocket.send_text(json.dumps({
                            'type': 'validate_token_result',
                            'valid': False,
                            'error': "Resposta inesperada da API DeepSeek."
                        }))
                except Exception as e:
                    await websocket.send_text(json.dumps({
                        'type': 'validate_token_result',
                        'valid': False,
                        'error': f"Falha na conexão: {str(e)[:140]}"
                    }))

            elif m_type == 'test_php':
                path_to_test = msg.get('path', '').strip() or tools.php_binary
                if not path_to_test or not os.path.isfile(path_to_test):
                    await websocket.send_text(json.dumps({
                        'type': 'test_php_result',
                        'success': False,
                        'msg': 'Interpretador php.exe não encontrado no caminho especificado.'
                    }))
                else:
                    try:
                        import subprocess
                        res = subprocess.run([path_to_test, "-v"], capture_output=True, text=True, timeout=5)
                        if res.returncode == 0 and res.stdout:
                            first_line = res.stdout.splitlines()[0]
                            await websocket.send_text(json.dumps({
                                'type': 'test_php_result',
                                'success': True,
                                'path': path_to_test,
                                'version': first_line,
                                'msg': f"✓ PHP operacional: {first_line}"
                            }))
                        else:
                            await websocket.send_text(json.dumps({
                                'type': 'test_php_result',
                                'success': False,
                                'msg': f"Erro ao executar php.exe: {res.stderr or res.stdout}"
                            }))
                    except Exception as e:
                        await websocket.send_text(json.dumps({
                            'type': 'test_php_result',
                            'success': False,
                            'msg': f"Erro ao testar php.exe: {e}"
                        }))

            elif m_type == 'stop_generation':
                cancel_event.set()
                if prompt_task and not prompt_task.done():
                    prompt_task.cancel()
                    try:
                        await prompt_task
                    except (asyncio.CancelledError, Exception):
                        pass
                await safe_send({
                    'type': 'chat_done',
                    'executed_tools_count': 0,
                    'stopped': True
                })
                await safe_send({
                    'type': 'system_msg',
                    'content': '⏹ Execução do agente interrompida pelo usuário.'
                })

            elif m_type == 'prompt':
                if prompt_task and not prompt_task.done():
                    prompt_task.cancel()
                    try:
                        await prompt_task
                    except (asyncio.CancelledError, Exception):
                        pass
                cancel_event.clear()

                async def run_agent_pipeline(p_msg: dict):
                    prompt_text = p_msg.get('content', '').strip()
                    attachment = p_msg.get('attachment')
                    role_override = p_msg.get('role') or current_role
                    auto_loop = p_msg.get('auto_loop', True)

                    if not prompt_text and not attachment:
                        return

                    if not config.is_authenticated():
                        await safe_send({
                            'type': 'system_msg',
                            'content': 'DeepSeek não autenticado. Clique no botão ⚙️ Configurações no topo e insira seu Bearer Token.'
                        })
                        await safe_send({
                            'type': 'chat_done',
                            'executed_tools_count': 0
                        })
                        return

                    # Ensure active chat session
                    if not config.active_session_id:
                        try:
                            sess = await client.create_chat_session(agent="chat")
                            config.active_session_id = sess["id"]
                            config.save()
                        except Exception as e:
                            await safe_send({
                                'type': 'system_msg',
                                'content': f"Erro ao criar sessão no DeepSeek: {e}"
                            })
                            await safe_send({'type': 'chat_done', 'executed_tools_count': 0})
                            return

                    selected_role = DEFAULT_ROLES.get(role_override, DEFAULT_ROLES["pladix_coder"])
                    system_base = project_engine.get_system_instructions()
                    
                    mentoria_extra = ""
                    if pladix_mode or role_override == "pladix_coder":
                        mentoria_extra = f"\n\n### MENTORIA & DIRETRIZES PLADIX:\n{MENTORIA_PLADIX_PROMPT}\n"

                    ws_summary = tools.get_workspace_summary()

                    attachment_block = ""
                    if attachment and attachment.get('content'):
                        attachment_block = (
                            f"\n\n=======================================================\n"
                            f"### ARQUIVO ANEXADO: `{attachment.get('name', 'conteudo.txt')}` ({attachment.get('size', 0)} bytes)\n"
                            f"Analise integralmente o conteúdo abaixo para produzir a API ou código correspondente:\n"
                            f"=======================================================\n"
                            f"```text\n{attachment.get('content')}\n```\n"
                            f"=======================================================\n"
                        )

                    current_step_prompt = (
                        f"{system_base}\n"
                        f"{mentoria_extra}\n"
                        f"### AGENTE ESPECIALISTA ATIVO: {selected_role.name} ({selected_role.description})\n\n"
                        f"### CONTEXTO DA PASTA ATUAL DO WORKSPACE:\n{ws_summary}\n"
                        f"{attachment_block}\n"
                        f"### SOLICITAÇÃO DO USUÁRIO:\n{prompt_text or 'Por favor, processe o arquivo anexado e gere a solução/API completa.'}\n\n"
                        f"### DIRETRIZ DE EXECUÇÃO OBRIGATÓRIA:\n"
                        f"SEMPRE gere o código PHP completo utilizando o bloco estruturado de ferramenta:\n"
                        f"<tool_call>\n"
                        f"<action>create_file</action>\n"
                        f"<path>api.php</path>\n"
                        f"<content>\n"
                        f"...codigo PHP completo estruturado com cookies, tokens, cURL das etapas e padrao bootstrap...\n"
                        f"</content>\n"
                        f"</tool_call>\n"
                        f"NUNCA entregue apenas texto sem salvar o arquivo fisicamente na pasta através da tag <tool_call>!"
                    )

                    max_steps = 5 if auto_loop else 1
                    total_executed_tools = 0

                    try:
                        for step_idx in range(max_steps):
                            if cancel_event.is_set():
                                break

                            if step_idx > 0:
                                await safe_send({
                                    'type': 'autonomous_step_notice',
                                    'step': step_idx + 1,
                                    'max_steps': max_steps,
                                    'msg': f"⚡ Agente avançando autonomamente na Etapa {step_idx + 1}/{max_steps}..."
                                })

                            full_response = ""
                            async for chunk in client.chat_completion(
                                session_id=config.active_session_id,
                                prompt=current_step_prompt,
                                thinking_enabled=True,
                                search_enabled=False
                            ):
                                if cancel_event.is_set():
                                    break
                                if chunk.chunk_type == "think":
                                    if not await safe_send({
                                        'type': 'chat_chunk',
                                        'content': chunk.content,
                                        'is_think': True
                                    }):
                                        break
                                elif chunk.chunk_type == "response":
                                    full_response += chunk.content
                                    if not await safe_send({
                                        'type': 'chat_chunk',
                                        'content': chunk.content,
                                        'is_think': False
                                    }):
                                        break
                                    if "<checklist>" in full_response and "</checklist>" in full_response:
                                        items_raw = re.findall(
                                            r'<item status=["\'](.*?)["\']>(.*?)</item>',
                                            full_response,
                                            re.DOTALL | re.IGNORECASE
                                        )
                                        if items_raw:
                                            items = [{"status": s.strip().lower(), "text": t.strip()} for s, t in items_raw]
                                            await safe_send({
                                                'type': 'checklist_update',
                                                'items': items
                                            })
                                elif chunk.chunk_type == "error":
                                    await safe_send({
                                        'type': 'system_msg',
                                        'content': f"Erro na API DeepSeek: {chunk.error}"
                                    })
                                    break

                            if cancel_event.is_set():
                                break

                            # Parse tool calls
                            tool_calls = project_engine.parse_tool_calls(full_response)

                            # Failsafe: se gerou bloco ```php mas não usou <tool_call>, cria api.php automaticamente!
                            if not any(c.get("action") == "create_file" for c in tool_calls):
                                php_matches = re.findall(r'```(?:php)?\s*([\s\S]*?)```', full_response, re.IGNORECASE)
                                if php_matches:
                                    largest = max(php_matches, key=len)
                                    if len(largest.strip()) > 150:
                                        tool_calls.append({
                                            "action": "create_file",
                                            "path": "api.php",
                                            "content": largest.strip()
                                        })

                            executed_tools = []
                            last_created_path = None
                            tool_results_feedback = []

                            if tool_calls and not cancel_event.is_set():
                                for call in tool_calls:
                                    if cancel_event.is_set():
                                        break
                                    res = await project_engine.execute_tool_call(call)
                                    act = call.get("action")
                                    p = call.get("path") or call.get("command") or ""
                                    
                                    t_info = {
                                        "action": act,
                                        "path": p,
                                        "success": res.get("success", False),
                                        "error": res.get("error"),
                                        "syntax": res.get("syntax")
                                    }
                                    executed_tools.append(t_info)

                                    await safe_send({
                                        'type': 'tool_executed',
                                        'tool': t_info
                                    })

                                    if act == "create_file" and res.get("success"):
                                        last_created_path = p

                                    # Collect outputs for autonomous continuation
                                    out_text = ""
                                    if act == "run_command":
                                        out_text = res.get("stdout") or res.get("stderr") or ("Comando executado (exit 0)" if res.get("success") else "Falha")
                                    elif act in ("create_file", "edit_file"):
                                        syntax_val = res.get("syntax", {}).get("valid", True)
                                        out_text = f"Arquivo '{p}' gravado no disco com sucesso. Sintaxe PHP: {'Válida' if syntax_val else 'Erro'}"
                                    elif act == "create_dir":
                                        out_text = f"Diretório '{p}' estruturado com sucesso."

                                    tool_results_feedback.append(f"• Ação '{act}' [{p}]: {out_text[:400]}")

                            total_executed_tools += len(executed_tools)

                            # Refresh file tree
                            tree = get_file_tree(str(tools.workspace))
                            await safe_send({'type': 'file_tree', 'tree': tree})
                            await send_workspace_info()

                            # Auto-open created file in editor
                            if last_created_path and not cancel_event.is_set():
                                try:
                                    full_target = (tools.workspace / last_created_path).resolve()
                                    if full_target.exists():
                                        with open(full_target, 'r', encoding='utf-8', errors='replace') as fp:
                                            created_code = fp.read()
                                        ext = os.path.splitext(last_created_path)[1].lower()
                                        await safe_send({
                                            'type': 'file_content',
                                            'path': str(full_target).replace('\\', '/'),
                                            'rel_path': last_created_path,
                                            'content': created_code,
                                            'language': get_language_from_ext(ext)
                                        })
                                except Exception as e:
                                    print(f"Erro ao abrir arquivo gerado: {e}")

                            # Check if agent should continue recursively
                            # If no tools called, or reached max_steps, or auto_loop is disabled, break!
                            if not tool_calls or step_idx == max_steps - 1 or not auto_loop or cancel_event.is_set():
                                break

                            # Prepare recursive prompt for next turn
                            feedback_blob = "\n".join(tool_results_feedback)
                            current_step_prompt = (
                                f"[RESULTADO DAS AÇÕES QUE VOCÊ EXECUTOU NO SISTEMA]:\n"
                                f"{feedback_blob}\n\n"
                                f"[INSTRUÇÃO PARA CONTINUAÇÃO AUTÔNOMA]:\n"
                                f"Analise os resultados das ações acima e dê continuidade imediata à implementação da API PHP.\n"
                                f"Gere ou atualize o arquivo api.php utilizando <tool_call><action>create_file</action> ou <action>edit_file</action>.\n"
                                f"Se o trabalho já estiver 100% completo, forneça o resumo final e encerre sem novas chamadas de ferramentas."
                            )

                    except asyncio.CancelledError:
                        pass
                    except Exception as e:
                        if not cancel_event.is_set():
                            await safe_send({
                                'type': 'system_msg',
                                'content': f"Erro durante a execução do agente: {e}"
                            })

                    # Send interactive suggestions
                    suggestions = [
                        {"label": "🚀 Continuar Produção Autônoma", "prompt": "Continue autonomamente o desenvolvimento da API gerando e ajustando as próximas etapas no api.php."},
                        {"label": "✅ Fazer isso (Sim, continuar)", "prompt": "Sim, continue com as etapas sugeridas e aplique as alterações no arquivo api.php agora."},
                        {"label": "❌ Não fazer / Ajustar", "prompt": "Não execute dessa forma. Vamos ajustar a abordagem: preciso que você..."},
                        {"label": "🛠️ Simular Checkout / Pagamento", "prompt": "Adicione a simulação completa das etapas de checkout e pagamento no api.php com dados de teste."},
                        {"label": "▶ Testar Execução no XAMPP", "action": "execute_current"},
                        {"label": "🔍 Auditar api.php e Otimizar", "prompt": "Faça uma auditoria cirúrgica de segurança, performance e cabeçalhos no api.php."}
                    ]

                    if not cancel_event.is_set():
                        await safe_send({
                            'type': 'chat_done',
                            'executed_tools_count': total_executed_tools,
                            'suggestions': suggestions
                        })

                prompt_task = asyncio.create_task(run_agent_pipeline(msg))
                def _handle_task_result(t: asyncio.Task):
                    try:
                        t.result()
                    except (asyncio.CancelledError, WebSocketDisconnect):
                        pass
                    except Exception:
                        pass
                prompt_task.add_done_callback(_handle_task_result)

    except WebSocketDisconnect:
        print("Cliente Web desconectado.")
    except Exception as e:
        print(f"Conexão websocket encerrada: {e}")
    finally:
        cancel_event.set()
        if prompt_task and not prompt_task.done():
            prompt_task.cancel()
            try:
                await prompt_task
            except (asyncio.CancelledError, WebSocketDisconnect, Exception):
                pass

def find_available_port(default_port: int = 58910, max_attempts: int = 100) -> int:
    import socket
    for p in range(default_port, default_port + max_attempts):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                s.bind(('127.0.0.1', p))
                return p
            except OSError:
                continue
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]

def run_server(port: int):
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="error")

def start_gui():
    port = find_available_port(58910)
    print(f"[*] Servidor PladixAgentIA GUI alocado com sucesso na porta segura: {port}")
    t = threading.Thread(target=run_server, args=(port,), daemon=True)
    t.start()
    
    # Wait for server to boot
    import time
    time.sleep(1)
    
    # Open PyWebView window
    webview.create_window(
        'PladixAgentIA - Supremo IDE v2.0',
        f'http://127.0.0.1:{port}',
        width=1440,
        height=900,
        min_size=(1024, 700)
    )
    webview.start()

if __name__ == "__main__":
    start_gui()
