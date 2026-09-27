"""
DeepSeek Configuration & Credential Management
Desenvolvido por PladixOficial
Telegram: t.me/pladixoficial
"""

import os
import json
import uuid
from pathlib import Path
from typing import Optional, Dict, Any

CONFIG_DIR = Path.home() / ".deepseek_ide"
CONFIG_FILE = CONFIG_DIR / "config.json"

DEFAULT_HEADERS = {
    "accept": "*/*",
    "accept-language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
    "cache-control": "no-cache",
    "content-type": "application/json",
    "origin": "https://chat.deepseek.com",
    "pragma": "no-cache",
    "priority": "u=1, i",
    "referer": "https://chat.deepseek.com/",
    "sec-ch-ua": '"Chromium";v="154", "Google Chrome";v="154", "Not A(Brand";v="99"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/154.0.0.0 Safari/537.36",
    "x-client-bundle-id": "com.deepseek.chat",
    "x-client-locale": "pt_BR",
    "x-client-platform": "web",
    "x-client-timezone-offset": "-10800",
    "x-client-version": "2.5.0",
}


class Config:
    def __init__(self):
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        self.token: Optional[str] = None
        self.cookie: Optional[str] = None
        self.device_id: str = str(uuid.uuid4())
        self.active_session_id: Optional[str] = None
        self.thinking_enabled: bool = True
        self.search_enabled: bool = False
        self.model_type: str = "default"  # default
        self.php_path: Optional[str] = None
        self.python_path: Optional[str] = None
        self.load()

    def load(self) -> None:
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.token = data.get("token")
                    self.cookie = data.get("cookie")
                    self.device_id = data.get("device_id", self.device_id)
                    self.active_session_id = data.get("active_session_id")
                    self.thinking_enabled = data.get("thinking_enabled", True)
                    self.search_enabled = data.get("search_enabled", False)
                    self.model_type = data.get("model_type", "default")
                    self.php_path = data.get("php_path")
                    self.python_path = data.get("python_path")
            except Exception:
                pass

    def save(self) -> None:
        data = {
            "token": self.token,
            "cookie": self.cookie,
            "device_id": self.device_id,
            "active_session_id": self.active_session_id,
            "thinking_enabled": self.thinking_enabled,
            "search_enabled": self.search_enabled,
            "model_type": self.model_type,
            "php_path": self.php_path,
            "python_path": self.python_path,
        }
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def set_auth(self, token: str, cookie: Optional[str] = None) -> None:
        if token.lower().startswith("bearer "):
            token = token[7:].strip()
        self.token = token.strip()
        if cookie:
            self.cookie = cookie.strip()
        self.save()

    def is_authenticated(self) -> bool:
        return bool(self.token)

    def get_headers(self) -> Dict[str, str]:
        headers = dict(DEFAULT_HEADERS)
        if self.token:
            headers["authorization"] = f"Bearer {self.token}"
        if self.cookie:
            headers["cookie"] = self.cookie
        headers["x-device-id"] = self.device_id
        return headers
