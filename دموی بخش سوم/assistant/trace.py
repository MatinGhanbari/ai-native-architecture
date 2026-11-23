"""ردگیری (tracing): هر تصمیم، فراخوانی مدل/ابزار، رویداد gateway و Controller، و token/هزینه/تأخیر ثبت می‌شود."""
import json, os, sys, time, uuid
from .textutil import to_fa

LABELS = {"run_start": "شروع", "memory_read": "خواندن حافظه", "llm_call": "فراخوانی مدل",
          "decision": "تصمیم مدل", "schema": "اعتبارسنجی schema", "retrieve": "بازیابی (RAG)",
          "quarantine": "قرنطینه (Dual LLM)", "tool_call": "فراخوانی ابزار", "approval": "تأیید انسانی",
          "controller": "Controller", "gateway": "AI Gateway", "verification": "گام راستی‌آزمایی",
          "memory_write": "نوشتن حافظه", "run_end": "پایان"}
COLORS = {"controller": "\033[93m", "gateway": "\033[95m", "verification": "\033[96m", "quarantine": "\033[94m",
          "run_end": "\033[92m", "tool_call": "\033[37m"}

def use_color():
    return os.getenv("FORCE_COLOR") == "1" or (sys.stdout.isatty() and os.getenv("NO_COLOR") is None)

class Tracer:
    def __init__(self, out_dir="traces", verbose=True):
        self.run_id = time.strftime("%Y%m%d-%H%M%S-") + uuid.uuid4().hex[:6]
        self.events, self.verbose, self.t0 = [], verbose, time.time()
        self.tokens_in = self.tokens_out = self.llm_calls = 0
        self.cost = 0.0
        os.makedirs(out_dir, exist_ok=True)
        self.path = os.path.join(out_dir, f"{self.run_id}.jsonl")
        self.color = use_color()

    def elapsed_ms(self):
        return int((time.time() - self.t0) * 1000)

    def llm(self, step, tin, tout, model, price_in, price_out, **extra):
        c = tin / 1000 * price_in + tout / 1000 * price_out
        self.tokens_in += tin; self.tokens_out += tout; self.cost += c; self.llm_calls += 1
        self.log("llm_call", step, model=model, tokens_in=tin, tokens_out=tout, cost_usd=f"{c:.6f}", **extra)

    def log(self, kind, step=0, **data):
        ev = {"run_id": self.run_id, "t_ms": self.elapsed_ms(), "step": step, "event": kind, **data}
        self.events.append(ev)
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(ev, ensure_ascii=False) + "\n")
        if self.verbose:
            body = ", ".join(f"{k}={json.dumps(v, ensure_ascii=False) if not isinstance(v, str) else v}" for k, v in data.items())
            line = f"  [trace {to_fa(ev['t_ms']).rjust(5)}ms] گام {to_fa(step)} | {LABELS.get(kind, kind)} | {body}"[:330]
            if self.color and kind in COLORS:
                hot = kind == "controller" or data.get("result") in ("timeout", "fallback", "circuit_breaker_open", "fail", "blocked")
                line = ("\033[1m" if hot else "") + COLORS[kind] + line + "\033[0m"
            print(line)

    def summary(self):
        return {"steps": max((e["step"] for e in self.events), default=0), "tokens_in": self.tokens_in,
                "tokens_out": self.tokens_out, "llm_calls": self.llm_calls, "cost_usd": round(self.cost, 6),
                "latency_ms": self.elapsed_ms(), "trace_file": self.path}
