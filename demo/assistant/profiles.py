"""پروفایل‌های مدل: offline (mock قطعی) | 9router | lmstudio | real (همان OPENAI_* قدیمی).

انتخاب: متغیر MODE (یا LLM_PROFILE). کلیدها فقط از محیط یا فایل .env ریشهٔ مخزن خوانده می‌شوند
(آن فایل در git نیست). هیچ کلیدی در لاگ، trace یا UI نوشته نمی‌شود.
"""
import os

DEMO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(DEMO)

PROFILES = {
    # name: (پیشوند env، base پیش‌فرض، مدل پیش‌فرض، برچسب)
    "9router": ("NINEROUTER", "http://localhost:20128/v1", "demo", "9router"),
    "lmstudio": ("LMSTUDIO", "http://127.0.0.1:1234/v1", "qwen/qwen3-4b", "LM Studio"),
    "real": ("OPENAI", "https://api.openai.com/v1", "gpt-4o-mini", "OpenAI-compatible"),
}
LIVE = ("9router", "lmstudio", "real")
_loaded = False


def load_dotenv():
    """خواندن .env ریشهٔ مخزن و demo/.env بدون بازنویسی متغیرهایی که از قبل در محیط هستند."""
    global _loaded
    if _loaded:
        return
    _loaded = True
    for path in (os.path.join(DEMO, ".env"), os.path.join(ROOT, ".env")):
        if not os.path.isfile(path):
            continue
        for line in open(path, encoding="utf-8-sig"):
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            k, v = k.strip(), v.strip().strip('"').strip("'")
            if k and k not in os.environ:
                os.environ[k] = v


def normalize(mode):
    m = (mode or "").strip().lower().replace("-", "").replace(" ", "")
    if m in ("9router", "ninerouter", "router"):
        return "9router"
    if m in ("lmstudio", "lm", "local"):
        return "lmstudio"
    if m in ("real", "openai"):
        return "real"
    return "offline"


def current():
    load_dotenv()
    return normalize(os.getenv("MODE") or os.getenv("LLM_PROFILE") or "offline")


def is_live(mode=None):
    return normalize(mode) in LIVE if mode is not None else current() in LIVE


def config(name):
    """{"base_url","api_key","model","small_model","fallback","label"}؛ برای offline مقدار None."""
    load_dotenv()
    name = normalize(name)
    if name not in PROFILES:
        return None
    pre, base, model, label = PROFILES[name]
    model = os.getenv(f"{pre}_MODEL", model)
    return {
        "name": name,
        "label": label,
        "base_url": os.getenv(f"{pre}_BASE_URL", base).rstrip("/"),
        "api_key": os.getenv(f"{pre}_API_KEY", ""),
        "model": model,
        "small_model": os.getenv(f"{pre}_SMALL_MODEL", "") or os.getenv(f"{pre}_FALLBACK_MODEL", "") or model,
        # provider پشتیبان در AI Gateway (و مدل نقش قرنطینه): پروفایل دیگر یا همین پروفایل
        "fallback": normalize(os.getenv(f"{pre}_FALLBACK_PROFILE", name)) if os.getenv(f"{pre}_FALLBACK_PROFILE") else name,
        "no_think": os.getenv(f"{pre}_NO_THINK", "1" if "qwen3" in model.lower() else "0") == "1",
    }


def missing_reason(name):
    """اگر پروفایل قابل استفاده نیست، دلیل فارسی؛ وگرنه None. (بدون نشان دادن کلید)"""
    name = normalize(name)
    if name == "offline":
        return None
    c = config(name)
    pre = PROFILES[name][0]
    if name != "lmstudio" and not c["api_key"]:
        return f"کلید {pre}_API_KEY در .env تنظیم نشده است"
    return None


def public_status():
    """وضعیت برای UI، بدون کلید."""
    out = {"default_mode": current(), "profiles": {}}
    for n in ("9router", "lmstudio"):
        c = config(n)
        out["profiles"][n] = {"label": c["label"], "model": c["model"], "base_url": c["base_url"],
                              "fallback": c["fallback"], "ready": missing_reason(n) is None, "reason": missing_reason(n)}
    r = config("real")
    out["profiles"]["real"] = {"label": r["label"], "model": r["model"], "base_url": r["base_url"],
                               "fallback": r["fallback"], "ready": bool(r["api_key"]), "reason": missing_reason("real")}
    return out
