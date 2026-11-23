"""AI Gateway: نقطهٔ واحد عبور همهٔ فراخوانی‌های مدل.
تاکتیک‌ها: مسیریابی بر اساس نقش (planner → مدل بزرگ، quarantine → مدل کوچک)، timeout، retry،
circuit breaker، fallback به provider دوم، cache پاسخ (اختیاری) و ثبت token/هزینه/تأخیر در trace."""
import hashlib, json, os, threading, time
from .textutil import est_tokens

PRICES = {  # دلار به ازای ۱۰۰۰ token (فرضی، برای برآورد): ورودی، خروجی
    "large": (float(os.getenv("PRICE_IN_PER_1K", "0.00015")), float(os.getenv("PRICE_OUT_PER_1K", "0.0006"))),
    "small": (float(os.getenv("PRICE_SMALL_IN_PER_1K", "0.00005")), float(os.getenv("PRICE_SMALL_OUT_PER_1K", "0.0002"))),
}

class ProviderDown(Exception):
    pass

class Gateway:
    def __init__(self, tracer, primary, secondary, outage=False, timeout_ms=None, cb_threshold=2, cache=None):
        self.t, self.primary, self.secondary = tracer, primary, secondary
        self.outage = outage or os.getenv("OUTAGE") == "primary"
        self.timeout_ms = timeout_ms or int(os.getenv("GW_TIMEOUT_MS", "400"))
        self.cb_threshold, self.failures, self.circuit_open = cb_threshold, 0, False
        self.cache_on = cache if cache is not None else os.getenv("GW_CACHE") == "1"
        self.cache_path = os.path.join(os.path.dirname(tracer.path), "..", "gw_cache.json")
        self.cache = json.load(open(self.cache_path, encoding="utf-8")) if self.cache_on and os.path.exists(self.cache_path) else {}

    def _call(self, provider, messages, simulate_outage):
        if simulate_outage:
            time.sleep(self.timeout_ms / 1000)          # درخواست تا سقف timeout معطل می‌ماند
            raise ProviderDown(f"timeout پس از {self.timeout_ms}ms")
        return provider.complete(messages)

    def _ok(self, step, tier, prov, messages, role, down=False):
        t0 = time.time()
        raw = self._call(prov, messages, down)
        ms = int((time.time() - t0) * 1000)
        pin, pout = PRICES[tier]
        tin = est_tokens("".join(m["content"] for m in messages)); tout = est_tokens(raw)
        self.t.llm(step, tin, tout, prov.name, pin, pout, role=role, ms=ms)
        return raw

    def complete(self, step, messages, role="planner"):
        key = hashlib.sha256(json.dumps(messages, ensure_ascii=False).encode()).hexdigest()[:16]
        if self.cache_on and key in self.cache:
            self.t.log("gateway", step, role=role, result="cache_hit", key=key)
            return self.cache[key]
        if role == "quarantine":
            raw = self._ok(step, "small", self.secondary, messages, role)
        else:
            raw = None
            if self.circuit_open:
                self.t.log("gateway", step, provider=self.primary.name, result="circuit_open", action="skip_primary")
            else:
                for attempt in (1, 2):
                    t0 = time.time()
                    try:
                        raw = self._ok(step, "large", self.primary, messages, role, down=self.outage)
                        self.failures = 0
                        break
                    except (ProviderDown, OSError) as e:
                        self.failures += 1
                        self.t.log("gateway", step, provider=self.primary.name, attempt=attempt, result="timeout",
                                   ms=int((time.time() - t0) * 1000), error=str(e))
                        if self.failures >= self.cb_threshold:
                            self.circuit_open = True
                            self.t.log("gateway", step, provider=self.primary.name, result="circuit_breaker_open", failures=self.failures)
                            break
                        self.t.log("gateway", step, provider=self.primary.name, result="retry")
            if raw is None:
                self.t.log("gateway", step, result="fallback", to=self.secondary.name)
                raw = self._ok(step, "small", self.secondary, messages, role)
        if self.cache_on:
            self.cache[key] = raw
            json.dump(self.cache, open(self.cache_path, "w", encoding="utf-8"), ensure_ascii=False)
        return raw
