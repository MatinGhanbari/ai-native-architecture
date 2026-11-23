"""لانچر یکپارچهٔ دموها (فقط stdlib، سازگار با ویندوز).

سرویس‌ها:
  home         صفحهٔ شروع همین لانچر + دموی بخش ۱ (/part1/)    http://127.0.0.1:8080
  part12-web   frontend دموی بخش ۲ (Next.js dev)             http://127.0.0.1:8082
  part12-api   backend دموی بخش ۲ (FastAPI/uvicorn)          http://127.0.0.1:8083
  part3        دموی بخش ۳ (demo/run_ui.py)                     http://127.0.0.1:8084
  (پراکسی LLM بخش ۲ فقط در حالت زنده)                          http://127.0.0.1:8085
همهٔ پورت‌ها در بازهٔ 8080 تا 8090 و ثابت‌اند؛ هر کدام با گزینهٔ خودش عوض می‌شود.
"""
import argparse, importlib.util, json, os, shutil, signal, socket, subprocess, sys, threading, time, urllib.request, webbrowser
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SUB = os.path.join(ROOT, "part-02", "demo", "software-architecture-demo")   # دموی بخش ۲ (submodule آرشیا)
DEMO3 = os.path.join(ROOT, "demo")
FONTS = os.path.join(DEMO3, "ui", "fonts")
PART1 = os.path.join(ROOT, "part-01", "demo")   # دموی بخش اول: نمای C4 (HTML محلی)
MIME = {".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8", ".css": "text/css; charset=utf-8", ".woff2": "font/woff2", ".svg": "image/svg+xml", ".png": "image/png"}
# اجرای بدون اینترنت: مدل embedding از cache محلی Hugging Face خوانده می‌شود (یک بار از قبل دانلود شده است)
OFFLINE_ENV = {"HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1", "HF_HUB_DISABLE_TELEMETRY": "1"}
LOGS = os.path.join(HERE, "logs")
WIN = os.name == "nt"

# پروفایل‌های مدل (offline / 9router / lmstudio) از همان ماژول دموی بخش ۳ خوانده می‌شود؛ کلیدها از .env ریشه
_spec = importlib.util.spec_from_file_location("demo_profiles", os.path.join(DEMO3, "assistant", "profiles.py"))
profiles = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(profiles)

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def port_busy(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", port)) == 0


def http_ok(url, timeout=5):
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return r.status < 500
    except urllib.error.HTTPError as e:
        return e.code < 500
    except Exception:
        return False


def venv_python(backend):
    for p in (os.path.join(backend, ".venv", "Scripts", "python.exe"), os.path.join(backend, ".venv", "bin", "python")):
        if os.path.isfile(p):
            return p
    return sys.executable


class Service:
    def __init__(self, key, title, port, health, cmd_fn, cwd, env=None, timeout=180, fallback_env=None):
        self.key, self.title, self.port, self.health = key, title, port, health
        self.fallback_env = fallback_env   # اگر پروسه بالا نیامد، یک بار دیگر با این env (حالت mock) اجرا می‌شود
        self.cmd_fn, self.cwd, self.env, self.timeout = cmd_fn, cwd, env or {}, timeout
        self.proc, self.state, self.note, self.external = None, "stopped", "", False

    @property
    def url(self):
        return f"http://127.0.0.1:{self.port}/"

    def start(self):
        if not os.path.isdir(self.cwd):
            self.state, self.note = "missing", f"پوشه پیدا نشد: {os.path.relpath(self.cwd, ROOT)}"
            return
        if port_busy(self.port):
            if http_ok(self.health):
                self.state, self.external = "ready", True
                self.note = "از قبل در حال اجرا بود؛ همان استفاده شد"
            else:
                self.state, self.note = "error", f"پورت {self.port} را برنامهٔ دیگری گرفته است"
            return
        cmd = self.cmd_fn()
        if cmd is None:
            return
        os.makedirs(LOGS, exist_ok=True)
        env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1", **self.env)
        if self.key != "part3":   # کلیدهای .env فقط به دموی بخش ۳ و پراکسی لانچر می‌رسند
            env = {k: v for k, v in env.items() if not k.endswith("_API_KEY") or k in self.env}
        kw = {}
        if WIN:
            kw["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
        else:
            kw["start_new_session"] = True
        self.logf = open(os.path.join(LOGS, f"{self.key}.log"), "w", encoding="utf-8", errors="replace")
        self.proc = subprocess.Popen(cmd, cwd=self.cwd, env=env, stdout=self.logf, stderr=subprocess.STDOUT,
                                     stdin=subprocess.DEVNULL, **kw)
        self.state = "starting"
        threading.Thread(target=self._wait_ready, daemon=True).start()

    def _wait_ready(self):
        t0 = time.time()
        while time.time() - t0 < self.timeout:
            if self.proc.poll() is not None:
                if self._fallback():
                    return
                self.state, self.note = "error", f"پروسه بسته شد (کد {self.proc.returncode}). لاگ: launcher/logs/{self.key}.log"
                log(f"✗ {self.title}: {self.note}")
                return
            if http_ok(self.health):
                self.state = "ready"
                log(f"✓ {self.title} آماده شد ({int(time.time() - t0)} ثانیه): {self.url}")
                return
            time.sleep(1)
        if self._fallback():
            return
        self.state, self.note = "error", f"بعد از {self.timeout} ثانیه جواب نداد. لاگ: launcher/logs/{self.key}.log"
        log(f"✗ {self.title}: {self.note}")

    def _fallback(self):
        if not self.fallback_env:
            return False
        log(f"⚠ {self.title} بالا نیامد؛ دوباره در حالت mock اجرا می‌شود ({self.fallback_env})")
        self.stop()
        self.env, self.fallback_env = {**self.env, **self.fallback_env}, None
        self.note = "حالت mock (پشتیبان)"
        self.start()
        return True

    def stop(self):
        p = self.proc
        if not p or p.poll() is not None:
            return
        try:
            if WIN:
                subprocess.run(["taskkill", "/PID", str(p.pid), "/T", "/F"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                os.killpg(p.pid, signal.SIGTERM)
            p.wait(timeout=10)
        except Exception:
            try:
                p.kill()
            except Exception:
                pass

    def info(self):
        return {"key": self.key, "title": self.title, "url": self.url, "state": self.state, "note": self.note}


def build_services(a):
    backend = os.path.join(SUB, "backend")
    frontend = os.path.join(SUB, "frontend")

    def part3_cmd():
        return [sys.executable, os.path.join(DEMO3, "run_ui.py"), "--no-browser"]

    def api_cmd():
        return [
            venv_python(backend),
            "-m",
            "uvicorn",
            "part2_api:app",   # همان app.main:app، به‌علاوهٔ mock پشتیبان embedding (launcher/part2_api.py)
            "--reload",
            "--host",
            "127.0.0.1",
            "--port",
            str(a.api_port),
        ]

    def web_cmd():
        next_bin = os.path.join(frontend, "node_modules", "next", "dist", "bin", "next")
        node = shutil.which("node")
        if not os.path.isfile(next_bin) or not node:
            svc_web.state = "missing"
            svc_web.note = "node_modules نصب نیست؛ یک بار در frontend دستور npm install را اجرا کنید" if node else "Node.js نصب نیست"
            return None
        # CORS این پورت را launcher/part2_api.py (با DEMO_WEB_ORIGINS) به backend اضافه می‌کند؛ submodule دست نمی‌خورد.
        # بدون --turbopack: فقط حالت webpack فایل فونت mock را از دیسک می‌خواند (turbopack آن را از اینترنت می‌خواهد)
        return [node, next_bin, "dev", "-p", str(a.web_port), "-H", "127.0.0.1"]

    svc3 = Service("part3", "دموی بخش ۳", a.part3_port, f"http://127.0.0.1:{a.part3_port}/api/status", part3_cmd, DEMO3,
                   {"UI_PORT": str(a.part3_port), "LLM_PROFILE": a.llm}, timeout=60)
    if a.llm == "offline":
        api_env = {"LLM_PROVIDER": "mock"}
    else:   # backend بخش ۲ از پراکسی لانچر استفاده می‌کند؛ کلید واقعی به آن پروسه داده نمی‌شود
        cfg = profiles.config(a.llm)
        api_env = {"LLM_PROVIDER": "openai", "LLM_BASE_URL": f"http://127.0.0.1:{a.proxy_port}/v1",
                   "LLM_API_KEY": "via-launcher-proxy", "LLM_MODEL": cfg["model"], "EMBEDDING_MODEL": "local-only"}
    svc_api = Service("part12-api", "backend بخش ۲", a.api_port, f"http://127.0.0.1:{a.api_port}/health", api_cmd, backend,
                      {**api_env, **OFFLINE_ENV, "DEMO_EMBEDDINGS": a.embeddings, "PYTHONHASHSEED": "0",
                       "DEMO_WEB_ORIGINS": f"http://127.0.0.1:{a.web_port},http://localhost:{a.web_port}",
                       "PYTHONPATH": HERE + os.pathsep + os.environ.get("PYTHONPATH", "")},
                      timeout=300, fallback_env={"DEMO_EMBEDDINGS": "mock"} if a.embeddings == "auto" else None)
    svc_web = Service("part12-web", "frontend بخش ۲", a.web_port, f"http://127.0.0.1:{a.web_port}/", web_cmd, frontend,
                      {"NEXT_PUBLIC_API_BASE_URL": f"http://127.0.0.1:{a.api_port}", "NEXT_TELEMETRY_DISABLED": "1",
                       # بدون اینترنت: next/font/google فونت‌ها را از فایل‌های محلی می‌خواند (بدون تغییر در submodule)
                       "NEXT_FONT_GOOGLE_MOCKED_RESPONSES": os.path.join(HERE, "next_font_mock.js")},
                      timeout=300)
    out = []
    if a.only in (None, "part2", "part12"):
        out += [svc_api, svc_web]
    if a.only in (None, "part3"):
        out.append(svc3)
    return out


LLM_INFO = {"profile": "offline", "label": "آفلاین (mock)", "model": None}


def make_handler(services):
    by_key = {s.key: s for s in services}
    home = open(os.path.join(HERE, "home.html"), "rb").read()

    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _send(self, code, body, ctype="application/json; charset=utf-8"):
            data = body if isinstance(body, bytes) else json.dumps(body, ensure_ascii=False).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            path = self.path.split("?")[0]
            if path in ("/", "/index.html"):
                return self._send(200, home, "text/html; charset=utf-8")
            if path == "/api/services":
                return self._send(200, {k: s.info() for k, s in by_key.items()})
            if path == "/api/llm":
                return self._send(200, LLM_INFO)
            if path.startswith("/fonts/"):
                full = os.path.normpath(os.path.join(FONTS, path[len("/fonts/"):]))
                if full.startswith(FONTS) and os.path.isfile(full) and full.endswith(".ttf"):
                    return self._send(200, open(full, "rb").read(), "font/ttf")
            if path.startswith("/part1/"):
                rel = path[len("/part1/"):]
                rel = rel[len("demo/"):] if rel.startswith("demo/") else rel   # /part1/demo/... هم کار کند
                full = os.path.normpath(os.path.join(PART1, rel or "c4-explorer.html"))
                ext = os.path.splitext(full)[1]
                if full.startswith(PART1 + os.sep) and os.path.isfile(full) and ext in MIME:
                    return self._send(200, open(full, "rb").read(), MIME[ext])
            self._send(404, {"error": "not found"})

    return H


def main():
    ap = argparse.ArgumentParser(description="اجرای هر دو دمو + صفحهٔ شروع")
    ap.add_argument("--home-port", type=int, default=int(os.getenv("HOME_PORT", "8080")))
    ap.add_argument("--part3-port", type=int, default=8084, help="پورت دموی بخش ۳")
    ap.add_argument("--web-port", type=int, default=8082, help="پورت frontend دموی بخش ۲")
    ap.add_argument("--api-port", type=int, default=8083, help="پورت backend دموی بخش ۲")
    ap.add_argument("--only", choices=["part2", "part12", "part3"], help="فقط یکی از دموها (part12 نام قدیمی part2 است)")
    ap.add_argument("--embeddings", choices=["auto", "local", "mock"], default=os.getenv("DEMO_EMBEDDINGS", "auto"),
                    help="embedding دموی بخش ۲: auto = مدل محلی و در صورت خطا mock (پیش‌فرض) | local | mock")
    ap.add_argument("--llm", type=profiles.normalize, default=profiles.current(),
                    help="مدل دموها: offline | 9router | lmstudio (پیش‌فرض: LLM_PROFILE در .env، وگرنه offline)")
    ap.add_argument("--proxy-port", type=int, default=8085, help="پورت پراکسی LLM برای دموی بخش ۲")
    ap.add_argument("--no-browser", action="store_true")
    a = ap.parse_args()

    if a.llm != "offline":
        why = profiles.missing_reason(a.llm)
        if why:
            log(f"✗ حالت {a.llm}: {why}. با --llm offline اجرا کنید یا .env را کامل کنید.")
            sys.exit(1)
        cfg = profiles.config(a.llm)
        LLM_INFO.update(profile=a.llm, label=cfg["label"], model=cfg["model"])
        if port_busy(a.proxy_port):
            log(f"پورت {a.proxy_port} (پراکسی LLM) گرفته است؛ با --proxy-port پورت دیگری بدهید.")
            sys.exit(1)
        from launcher import llm_proxy
        llm_proxy.start(cfg, a.proxy_port, log)
        ok = http_ok(f"http://127.0.0.1:{a.proxy_port}/v1/models", timeout=8)
        log(f"مدل: {cfg['label']} · {cfg['model']} · {cfg['base_url']}" + ("" if ok else "  ⚠ الان جواب نمی‌دهد؛ اول آن را روشن کنید"))
    else:
        log("مدل: آفلاین (mock قطعی، بدون اینترنت و کلید)")

    services = build_services(a)
    busy = [f"{n}={p}" for n, p in (("home", a.home_port), ("part2-web", a.web_port), ("part2-api", a.api_port), ("part3", a.part3_port)) if port_busy(p)]
    if busy:
        log("⚠ این پورت‌ها از قبل گرفته شده‌اند: " + ", ".join(busy) + " (اگر دموی خودمان باشد همان استفاده می‌شود)")
    if port_busy(a.home_port):
        log(f"پورت {a.home_port} گرفته است؛ با --home-port پورت دیگری بدهید.")
        sys.exit(1)

    log("در حال بالا آوردن دموها… (بار اول backend بخش ۲ مدل embedding را بار می‌کند و ممکن است ۳۰ تا ۹۰ ثانیه طول بکشد)")
    for s in services:
        s.start()
        if s.state in ("missing", "error") or s.external:
            log(("• " if s.external else "✗ ") + f"{s.title}: {s.note}")

    srv = ThreadingHTTPServer(("127.0.0.1", a.home_port), make_handler(services))
    url = f"http://127.0.0.1:{a.home_port}/"
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    log(f"صفحهٔ شروع: {url}   (توقف همه: Ctrl+C)")
    if not a.no_browser:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()

    def _stop(*_):
        raise KeyboardInterrupt
    for name in ("SIGBREAK", "SIGTERM"):   # Ctrl+Break در ویندوز، SIGTERM در لینوکس/مک
        if hasattr(signal, name):
            signal.signal(getattr(signal, name), _stop)

    try:
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass
    finally:
        log("در حال بستن همهٔ دموها…")
        srv.shutdown()
        for s in services:
            s.stop()
        log("بسته شد.")
