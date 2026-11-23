"""Controller: مؤلفهٔ کنترلی معماری مرجع؛ کد قطعی که حلقهٔ عامل را مثل یک ماشین حالت با بودجهٔ محدود اداره می‌کند.
حالت‌ها: PLAN → ACT (retrieve/tool) → OBSERVE → ... → VERIFY → DONE | ESCALATED | STOPPED_BUDGET"""
import json, os, re
from .textutil import norm, order_ids, numbers

INJECTION_PATTERNS = [r"نادیده بگیر", r"ignore (all )?previous", r"دستور(های|ات)? (قبلی|سیستم)", r"system prompt", r"همهٔ? سفارش"]
EGRESS_ALLOW = ("https://ketabsara.ir",)          # تنها مقصد مجاز برای پیوند در خروجی
URL_RE = re.compile(r"!?\[[^\]]*\]\((https?://[^)\s]+)\)|(https?://\S+)")

class Budget:
    """بودجهٔ هر درخواست: گام، token، زمان، هزینه (قابل تنظیم با متغیر محیطی)."""
    def __init__(self):
        self.max_steps = int(os.getenv("BUDGET_STEPS", "6"))
        self.max_tokens = int(os.getenv("BUDGET_TOKENS", "4000"))
        self.max_ms = int(os.getenv("BUDGET_MS", "6000"))
        self.max_cost = float(os.getenv("BUDGET_USD", "0.002"))

class Controller:
    def __init__(self, tracer, guards="full", budget=None):
        self.t, self.level = tracer, guards
        self.guards = guards == "full"
        self.b = budget or Budget()
        self.max_steps = self.b.max_steps
        self.seen = {}
        self.plan = None

    # ---------- لایهٔ «فیلتر» (حالت filter و full) ----------
    def input_check(self, q):
        hits = [p for p in INJECTION_PATTERNS if re.search(p, norm(q), re.I)]
        if self.level != "off":
            self.t.log("controller", 0, rule="input_filter", result="flagged" if hits else "pass", patterns=hits)
        return bool(hits)

    # ---------- plan-then-execute: مجموعهٔ ابزارهای مجاز پیش از دیدن هر دادهٔ نامطمئن ثابت می‌شود ----------
    def make_plan(self, q):
        nq = norm(q)
        if re.search(r"پولم|بازپرداخت|پس بگیرم|refund", nq):
            tools = ["request_refund"]
        elif order_ids(nq) or re.search(r"سفارش|کجاست|می ?رسد", nq):
            tools = ["get_order_status"]
        else:
            tools = []
        self.plan = tools
        if self.guards:
            self.t.log("controller", 0, rule="plan_then_execute", result="plan_fixed", allowed_tools=tools)
        return tools

    def tool_in_plan(self, step, name):
        if self.guards and self.plan is not None and name not in self.plan:
            self.t.log("controller", step, rule="plan_then_execute", result="blocked", tool=name,
                       note="فراخوانی خارج از plan ثابت‌شده؛ احتمالاً ناشی از دادهٔ نامطمئن")
            return False
        return True

    # ---------- بودجه ----------
    def budget_ok(self, step):
        used = {"steps": step, "tokens": self.t.tokens_in + self.t.tokens_out, "ms": self.t.elapsed_ms(), "usd": self.t.cost}
        lim = {"steps": self.b.max_steps, "tokens": self.b.max_tokens, "ms": self.b.max_ms, "usd": self.b.max_cost}
        for k in ("tokens", "ms", "usd"):
            if used[k] > lim[k]:
                self.t.log("controller", step, rule="budget", result="stop", budget=k,
                           used=round(used[k], 6) if k == "usd" else used[k], limit=lim[k], state="STOPPED_BUDGET")
                return False
        return True

    def check_action(self, step, action):
        """تشخیص حلقه: تکرار عین‌به‌عین یک عمل."""
        sig = json.dumps({k: action.get(k) for k in ("action", "tool", "args", "query")}, sort_keys=True, ensure_ascii=False)
        self.seen[sig] = self.seen.get(sig, 0) + 1
        if self.seen[sig] >= 3:
            self.t.log("controller", step, rule="loop_detected", result="stop", repeated=self.seen[sig])
            return False
        return True

    def output_check(self, step, final):
        """خروجی بدون منبع پذیرفته نمی‌شود."""
        if final["status"] == "answered" and not final.get("sources"):
            self.t.log("controller", step, rule="out_of_scope_output", result="rejected", note="پاسخ بدون منبع")
            return False
        return True

    def output_filter(self, step, final):
        """فیلتر متنی خروجی (لایهٔ filter): فقط کلیدواژه‌های آشکار را می‌گیرد."""
        bad = [w for w in ("system prompt", "دستور برای دستیار", "نادیده بگیر") if w in final.get("answer", "")]
        self.t.log("controller", step, rule="output_filter", result="blocked" if bad else "pass", words=bad)
        return not bad

    def egress_check(self, step, final):
        """حذف کانال خروج داده: هر پیوند/تصویر به مقصد خارج از فهرست مجاز حذف می‌شود."""
        ans = final.get("answer", "")
        bad = [m.group(1) or m.group(2) for m in URL_RE.finditer(ans)]
        bad = [u for u in bad if not u.startswith(EGRESS_ALLOW)]
        if bad:
            final["answer"] = URL_RE.sub(lambda m: m.group(0) if (m.group(1) or m.group(2)).startswith(EGRESS_ALLOW) else "", ans).strip()
            self.t.log("controller", step, rule="egress_allowlist", result="blocked", urls=[u[:60] for u in bad])
        return final

def verify(final, evidence, question, customer_id, db, tracer, step):
    """گام راستی‌آزمایی (قطعی): grounding، منبع معتبر، و جلوگیری از نشت دادهٔ مشتریان دیگر."""
    problems = []
    seen_chunks = {h["id"] for o in evidence if o["type"] == "retrieve" for h in o["hits"]}
    own_found = {o["result"]["order_id"] for o in evidence if o["type"] == "tool" and o["result"].get("found")}
    obs_text = norm(json.dumps(evidence, ensure_ascii=False)) + " " + norm(question)
    ans = final.get("answer", "")
    for s in final.get("sources", []):
        if s.startswith("orders_db:"):
            if s.split(":", 1)[1] not in own_found | set(order_ids(question)):
                problems.append(f"منبع {s} در مشاهدات این نشست تأیید نشده")
        elif s not in seen_chunks:
            problems.append(f"منبع {s} بازیابی نشده بود")
    asked = set(order_ids(question)) if final["status"] != "answered" else set()
    for oid in order_ids(ans):
        if oid in asked:
            continue
        row = db.by_id(oid)
        if row and row["customer_id"] != customer_id:
            problems.append(f"نشت داده: سفارش {oid} متعلق به مشتری دیگری است")
    for row in db.rows:
        if row["customer_id"] != customer_id and norm(row["customer_name"]) in norm(ans):
            problems.append("نشت داده: نام مشتری دیگر در پاسخ")
    if final["status"] == "answered":
        for n in numbers(ans):
            if n not in obs_text:
                problems.append(f"عدد {n} در منابع پشتیبانی نمی‌شود (احتمال توهم)")
    tracer.log("verification", step, result="pass" if not problems else "fail", problems=problems)
    return problems
