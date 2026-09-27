"""
DeepSeek Web API Client
Handles PoW verification, session management, and SSE streaming.

Desenvolvido por PladixOficial
Telegram: t.me/pladixoficial
"""

import json
import base64
import asyncio
from dataclasses import dataclass, field
from typing import Optional, AsyncGenerator, Dict, Any, List

import httpx

from .config import Config
from .pow_solver import solve_pow

BASE_URL = "https://chat.deepseek.com"


@dataclass
class StreamChunk:
    chunk_type: str  # "think", "response", "ready", "finish", "tokens", "title", "error"
    content: str = ""
    elapsed_secs: Optional[float] = None
    accumulated_tokens: int = 0
    message_id: Optional[int] = None
    title: Optional[str] = None
    error: Optional[str] = None


class DeepSeekClient:
    def __init__(self, config: Config):
        self.config = config

    async def get_pow_response_header(self, target_path: str = "/api/v0/chat/completion") -> str:
        """
        Requests a PoW challenge from DeepSeek and solves it, returning the base64 header.
        """
        url = f"{BASE_URL}/api/v0/chat/create_pow_challenge"
        headers = self.config.get_headers()
        payload = {"target_path": target_path}

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, headers=headers, json=payload)
            if resp.status_code != 200:
                raise RuntimeError(f"Erro ao obter PoW Challenge: HTTP {resp.status_code} - {resp.text}")
            
            res_json = resp.json()
            if res_json.get("code") != 0:
                raise RuntimeError(f"Erro na resposta do PoW: {res_json.get('msg', 'Erro desconhecido')}")

            ch = res_json["data"]["biz_data"]["challenge"]
            salt = ch["salt"]
            challenge_hex = ch["challenge"]
            difficulty = ch.get("difficulty", 144000)
            expire_at = ch["expire_at"]
            signature = ch["signature"]

        # Run CPU-bound PoW solver in threadpool so it doesn't block async event loop
        loop = asyncio.get_running_loop()
        answer = await loop.run_in_executor(
            None,
            solve_pow,
            salt,
            expire_at,
            challenge_hex,
            difficulty
        )

        if answer < 0:
            raise RuntimeError(f"Falha ao resolver PoW (não convergiu no limite de {difficulty} iterações).")

        pow_obj = {
            "algorithm": "DeepSeekHashV1",
            "challenge": challenge_hex,
            "salt": salt,
            "answer": answer,
            "signature": signature,
            "target_path": target_path,
        }

        encoded = base64.b64encode(json.dumps(pow_obj, separators=(",", ":")).encode("utf-8")).decode("utf-8")
        return encoded

    async def create_chat_session(self, agent: str = "chat") -> Dict[str, Any]:
        """
        Creates a new chat session on DeepSeek web.
        """
        url = f"{BASE_URL}/api/v0/chat_session/create"
        headers = self.config.get_headers()
        payload = {"agent": agent}

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, headers=headers, json=payload)
            if resp.status_code != 200:
                raise RuntimeError(f"Falha ao criar chat_session: HTTP {resp.status_code} - {resp.text}")
            res_json = resp.json()
            if res_json.get("code") != 0:
                raise RuntimeError(f"Falha na API DeepSeek: {res_json.get('msg')}")
            return res_json["data"]["biz_data"]["chat_session"]

    async def list_chat_sessions(self, count: int = 50) -> List[Dict[str, Any]]:
        """
        Lists user's recent chat sessions.
        """
        url = f"{BASE_URL}/api/v0/chat_session/fetch_page"
        headers = self.config.get_headers()
        params = {"count": count}

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                resp = await client.get(url, headers=headers, params=params)
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("code") == 0:
                        return data.get("data", {}).get("biz_data", {}).get("chat_sessions", [])
            except Exception:
                pass
        return []

    async def chat_completion(
        self,
        session_id: str,
        prompt: str,
        parent_message_id: Optional[int] = None,
        thinking_enabled: bool = True,
        search_enabled: bool = False,
    ) -> AsyncGenerator[StreamChunk, None]:
        """
        Streams completion from DeepSeek SSE endpoint, yielding think and response fragments.
        """
        pow_header = await self.get_pow_response_header("/api/v0/chat/completion")
        
        headers = self.config.get_headers()
        headers["x-ds-pow-response"] = pow_header
        headers["accept"] = "text/event-stream"

        payload = {
            "chat_session_id": session_id,
            "parent_message_id": parent_message_id,
            "model_type": self.config.model_type or "default",
            "prompt": prompt,
            "ref_file_ids": [],
            "thinking_enabled": thinking_enabled,
            "search_enabled": search_enabled,
            "action": None,
            "preempt": False,
        }

        url = f"{BASE_URL}/api/v0/chat/completion"

        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream("POST", url, headers=headers, json=payload) as response:
                if response.status_code != 200:
                    err_body = await response.aread()
                    yield StreamChunk(chunk_type="error", error=f"HTTP {response.status_code}: {err_body.decode('utf-8', errors='ignore')}")
                    return

                current_stage = "think" if thinking_enabled else "response"
                current_msg_id = None
                tokens_count = 0

                async for line in response.aiter_lines():
                    if not line:
                        continue

                    # Handle SSE event lines
                    if line.startswith("event:"):
                        event_name = line[6:].strip()
                        if event_name == "close":
                            yield StreamChunk(chunk_type="finish", accumulated_tokens=tokens_count, message_id=current_msg_id)
                            break
                        continue

                    if line.startswith("data:"):
                        data_str = line[5:].strip()
                        if not data_str:
                            continue

                        try:
                            data = json.loads(data_str)
                        except json.JSONDecodeError:
                            continue

                        # Check for ready event
                        if "response_message_id" in data:
                            current_msg_id = data.get("response_message_id")
                            yield StreamChunk(chunk_type="ready", message_id=current_msg_id)
                            continue

                        # Check for title
                        if "content" in data and isinstance(data.get("content"), str):
                            yield StreamChunk(chunk_type="title", title=data.get("content"))
                            continue

                        # Check for fragment switch or initial response
                        v = data.get("v")
                        if isinstance(v, dict) and "response" in v:
                            resp_info = v["response"]
                            current_msg_id = resp_info.get("message_id", current_msg_id)
                            fragments = resp_info.get("fragments", [])
                            for frag in fragments:
                                frag_type = frag.get("type")
                                content = frag.get("content", "")
                                if frag_type == "THINK":
                                    current_stage = "think"
                                    if content:
                                        yield StreamChunk(chunk_type="think", content=content)
                                elif frag_type == "RESPONSE":
                                    current_stage = "response"
                                    if content:
                                        yield StreamChunk(chunk_type="response", content=content)
                            continue

                        # Check for new fragment appended (e.g. switching from THINK to RESPONSE)
                        p = data.get("p", "")
                        o = data.get("o", "")

                        if p == "response/fragments" and o == "APPEND" and isinstance(v, list):
                            for frag in v:
                                frag_type = frag.get("type")
                                content = frag.get("content", "")
                                if frag_type == "THINK":
                                    current_stage = "think"
                                    if content:
                                        yield StreamChunk(chunk_type="think", content=content)
                                elif frag_type == "RESPONSE":
                                    current_stage = "response"
                                    if content:
                                        yield StreamChunk(chunk_type="response", content=content)
                            continue

                        # Check for elapsed seconds on thinking fragment
                        if p == "response/fragments/-1/elapsed_secs":
                            yield StreamChunk(chunk_type="think_elapsed", elapsed_secs=float(v))
                            continue

                        # Batch update tokens
                        if o == "BATCH" and isinstance(v, list):
                            for item in v:
                                if item.get("p") == "accumulated_token_usage":
                                    tokens_count = int(item.get("v", 0))
                                    yield StreamChunk(chunk_type="tokens", accumulated_tokens=tokens_count)
                            continue

                        # Incremental text appending
                        # Case 1: {"p":"response/fragments/-1/content","o":"APPEND","v":"..."}
                        # Case 2: {"v":"..."}
                        if isinstance(v, str):
                            if current_stage == "think":
                                yield StreamChunk(chunk_type="think", content=v)
                            else:
                                yield StreamChunk(chunk_type="response", content=v)
