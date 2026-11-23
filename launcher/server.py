"""لانچر یکپارچهٔ دموها (فقط stdlib، سازگار با ویندوز).

سرویس‌ها:
  part3        دموی بخش ۳ (demo/run_ui.py)                 http://127.0.0.1:8765
  part12-api   backend دموی بخش ۱ و ۲ (FastAPI/uvicorn)      http://127.0.0.1:8000
  part12-web   frontend دموی بخش ۱ و ۲ (Next.js dev)         http://127.0.0.1:3000
  home         صفحهٔ شروع همین لانچر                         http://127.0.0.1:8700
"""
import argparse, json, os, shutil, signal, socket, subprocess, sys, threading, time, urllib.request, webbrowser
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SUB = os.path.join(ROOT, "part-01-02_demo", "software-architecture-demo")
DEMO3 = os.path.join(ROOT, "demo")
FONTS = os.path.join(DEMO3, "ui", "fonts")
LOGS = os.path.join(HERE, "logs")
WIN = os.name == "nt"

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
    def __init__(self, key, title, port, health, cmd_fn, cwd, env=None, timeout=180):
        self.key, self.title, self.port, self.health = key, title, port, health
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
                self.state, self.note = "error", f"پروسه بسته شد (کد {self.proc.returncode}). لاگ: launcher/logs/{self.key}.log"
                log(f"✗ {self.title}: {self.note}")
                return
            if http_ok(self.health):
                self.state = "ready"
                log(f"✓ {self.title} آماده شد ({int(time.time() - t0)} ثانیه): {self.url}")
                return
            time.sleep(1)
        self.state, self.note = "error", f"بعد از {self.timeout} ثانیه جواب نداد. لاگ: launcher/logs/{self.key}.log"
        log(f"✗ {self.title}: {self.note}")

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
        return [venv_python(backend), "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(a.api_port)]

    def web_cmd():
        next_bin = os.path.join(frontend, "node_modules", "next", "dist", "bin", "next")
        node = shutil.which("node")
        if not os.path.isfile(next_bin) or not node:
            svc_web.state = "missing"
            svc_web.note = "node_modules نصب نیست؛ یک بار در frontend دستور npm install را اجرا کنید" if node else "Node.js نصب نیست"
            return None
        # پورت 3000 ثابت است: CORS در backend فقط localhost:3000 و 127.0.0.1:3000 را قبول می‌کند.
        return [node, next_bin, "dev", "--turbopack", "-p", "3000", "-H", "127.0.0.1"]

    svc3 = Service("part3", "دموی بخش ۳", a.part3_port, f"http://127.0.0.1:{a.part3_port}/api/status", part3_cmd, DEMO3,
                   {"UI_PORT": str(a.part3_port)}, timeout=60)
    svc_api = Service("part12-api", "backend بخش ۱ و ۲", a.api_port, f"http://127.0.0.1:{a.api_port}/health", api_cmd, backend,
                      timeout=300)
    svc_web = Service("part12-web", "frontend بخش ۱ و ۲", 3000, "http://127.0.0.1:3000/", web_cmd, frontend,
                      {"NEXT_PUBLIC_API_BASE_URL": f"http://127.0.0.1:{a.api_port}", "NEXT_TELEMETRY_DISABLED": "1"},
                      timeout=300)
    out = []
    if a.only in (None, "part12"):
        out += [svc_api, svc_web]
    if a.only in (None, "part3"):
        out.append(svc3)
    return out


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
            if path.startswith("/fonts/"):
                full = os.path.normpath(os.path.join(FONTS, path[len("/fonts/"):]))
                if full.startswith(FONTS) and os.path.isfile(full) and full.endswith(".ttf"):
                    return self._send(200, open(full, "rb").read(), "font/ttf")
            self._send(404, {"error": "not found"})

    return H


def main():
    ap = argparse.ArgumentParser(description="اجرای هر دو دمو + صفحهٔ شروع")
    ap.add_argument("--home-port", type=int, default=int(os.getenv("HOME_PORT", "8700")))
    ap.add_argument("--part3-port", type=int, default=int(os.getenv("UI_PORT", "8765")))
    ap.add_argument("--api-port", type=int, default=8000)
    ap.add_argument("--only", choices=["part12", "part3"], help="فقط یکی از دموها")
    ap.add_argument("--no-browser", action="store_true")
    a = ap.parse_args()

    services = build_services(a)
    if port_busy(a.home_port):
        log(f"پورت {a.home_port} گرفته است؛ با --home-port پورت دیگری بدهید.")
        sys.exit(1)

    log("در حال بالا آوردن دموها… (بار اول backend بخش ۱ و ۲ مدل embedding را بار می‌کند و ممکن است ۳۰ تا ۹۰ ثانیه طول بکشد)")
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
