"""پراکسی کوچک OpenAI-compatible برای دموی بخش ۱ و ۲ (بدون تغییر کد submodule).

backend آن دمو به‌جای سرویس اصلی به این پراکسی وصل می‌شود (LLM_BASE_URL=http://127.0.0.1:<port>/v1).
کارها:
  - کلید واقعی فقط در همین پروسه می‌ماند و به submodule داده نمی‌شود.
  - <think>…</think> مدل‌های استدلالی (مثل Qwen3) از content حذف می‌شود تا JSON پاسخ parse شود.
  - برای Qwen3، «/no_think» به پیام system اضافه می‌شود.
  - اگر مدل فراخوانی ابزار را به‌جای tool_calls به‌صورت متن JSON نوشت ({"name":…,"arguments":…} یا <tool_call>…</tool_call>،
    رفتار رایج مدل‌های کوچک در LM Studio)، همان به tool_calls استاندارد تبدیل می‌شود.
  - /v1/embeddings عمداً 404 می‌دهد تا آن دمو همیشه از embedding محلی (SentenceTransformer) استفاده کند
    و نتیجهٔ بازیابی در همهٔ حالت‌ها یکسان بماند.
"""
import json, re, threading, urllib.error, urllib.request
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

THINK = re.compile(r"<think>.*?(</think>|$)", re.S)
TOOL_TAG = re.compile(r"<tool_call>\s*(\{.*?\})\s*</tool_call>", re.S)


def text_tool_call(content, tool_names):
    """content متنی → (name, arguments) اگر واقعاً فراخوانی یکی از ابزارهای درخواست است؛ وگرنه None."""
    m = TOOL_TAG.search(content)
    cand = m.group(1) if m else content
    try:
        obj = json.loads(cand)
    except Exception:
        return None
    if isinstance(obj, dict) and obj.get("name") in tool_names and isinstance(obj.get("arguments", {}), (dict, str)):
        args = obj.get("arguments", {})
        return obj["name"], args if isinstance(args, str) else json.dumps(args, ensure_ascii=False)
    return None


def make_handler(cfg, log):
    base, key, no_think = cfg["base_url"].rstrip("/"), cfg["api_key"], cfg["no_think"]

    class H(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *a):
            pass

        def _send(self, code, data, ctype="application/json"):
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def _forward(self, method, path, body=None):
            headers = {"Content-Type": "application/json"}
            if key:
                headers["Authorization"] = f"Bearer {key}"
            req = urllib.request.Request(base + path, data=body, headers=headers, method=method)
            try:
                with urllib.request.urlopen(req, timeout=180) as r:
                    return r.status, r.read()
            except urllib.error.HTTPError as e:
                return e.code, e.read()
            except Exception as e:  # سرویس خاموش است
                return 502, json.dumps({"error": {"message": f"{cfg['label']} در دسترس نیست: {type(e).__name__}"}}).encode()

        def do_GET(self):
            path = self.path[3:] if self.path.startswith("/v1") else self.path
            if path.startswith("/models"):
                code, data = self._forward("GET", "/models")
                return self._send(code, data)
            self._send(404, b'{"error":"not found"}')

        def do_POST(self):
            n = int(self.headers.get("Content-Length", 0) or 0)
            raw = self.rfile.read(n) if n else b"{}"
            path = self.path[3:] if self.path.startswith("/v1") else self.path
            if path.startswith("/embeddings"):
                return self._send(404, b'{"error":{"message":"embeddings disabled by launcher; use local model"}}')
            if not path.startswith("/chat/completions"):
                return self._send(404, b'{"error":"not found"}')
            try:
                payload = json.loads(raw)
            except Exception:
                return self._send(400, b'{"error":"bad json"}')
            msgs = payload.get("messages") or []
            if no_think and msgs and msgs[0].get("role") == "system" and "/no_think" not in str(msgs[0].get("content")):
                msgs[0] = dict(msgs[0], content=str(msgs[0].get("content", "")) + "\n/no_think")
            payload["messages"] = msgs
            payload.setdefault("model", cfg["model"])
            payload["stream"] = False
            code, data = self._forward("POST", "/chat/completions", json.dumps(payload, ensure_ascii=False).encode("utf-8"))
            if code == 200:
                try:
                    body = json.JSONDecoder().raw_decode(data.decode("utf-8", "replace").lstrip())[0]
                    for ch in body.get("choices", []):
                        m = ch.get("message") or {}
                        if isinstance(m.get("content"), str):
                            c = THINK.sub("", m["content"]).strip()
                            if c.startswith("```"):           # ```json … ``` → JSON خالص
                                c = re.sub(r"^```[a-zA-Z]*\s*|\s*```$", "", c).strip()
                            m["content"] = c
                            names = {t.get("function", {}).get("name") for t in payload.get("tools") or []}
                            tc = text_tool_call(c, names) if names and not m.get("tool_calls") else None
                            if tc:
                                m["tool_calls"] = [{"id": "call_proxy_1", "type": "function",
                                                    "function": {"name": tc[0], "arguments": tc[1]}}]
                                m["content"] = ""
                                ch["finish_reason"] = "tool_calls"
                        m.pop("reasoning_content", None)
                    data = json.dumps(body, ensure_ascii=False).encode("utf-8")
                except Exception:
                    pass
            else:
                log(f"LLM proxy ({cfg['label']}): HTTP {code} {data[:200].decode('utf-8', 'replace')}")
            self._send(code, data)

    return H


def start(cfg, port, log=print):
    srv = ThreadingHTTPServer(("127.0.0.1", port), make_handler(cfg, log))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv
