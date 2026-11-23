"""حلقهٔ تک‌عاملی: plan → tool → evaluate → finish / escalate، زیر نظارت Controller و پشت AI Gateway.
guards: off (فقط RAG) | filter (فیلتر متنی ورودی/خروجی) | full (دفاع ساختاری: Dual LLM، plan-then-execute، کمترین دسترسی، egress allowlist، راستی‌آزمایی)"""
import json, os, re, sys
from .controller import Controller, verify
from .gateway import Gateway, ProviderDown
from .llm import QUARANTINE_PROMPT, make_providers, prompt_version, system_prompt
from .rag import KnowledgeBase
from .schema import ACTION_SCHEMA, FINAL_SCHEMA, QUARANTINE_SCHEMA, TOOL_ARG_SCHEMAS, validate
from .textutil import est_tokens
from .tools import OrdersDB, ToolError, Tools
from .trace import Tracer

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def _parse(raw):
    m = re.search(r"\{.*\}", raw, re.S)
    if not m:
        raise ValueError("JSON پیدا نشد")
    return json.loads(m.group(0))

class Agent:
    def __init__(self, customer_id="C001", guards="full", fault=None, approval=None, verbose=True, poisoned_kb=None):
        if guards is True: guards = "full"
        if guards is False: guards = "off"
        self.customer_id, self.level, self.fault = customer_id, guards, fault
        self.guards = guards == "full"
        self.approval = approval or os.getenv("APPROVAL", "queue")   # queue | ask | approve | deny
        self.t = Tracer(os.path.join(BASE, "traces"), verbose)
        self.poisoned = poisoned_kb if poisoned_kb is not None else os.getenv("POISONED_KB") == "1"
        docs = [os.path.join(BASE, "data", "policy_fa.md")]
        if self.poisoned:
            docs.append(os.path.join(BASE, "data", "vendor_update_fa.md"))   # سند بیرونی (تأمین‌کننده) = نامطمئن
        self.kb = KnowledgeBase(docs)
        self.db = OrdersDB(os.path.join(BASE, "data", "orders.json"))
        self.tools = Tools(self.db, customer_id, self.guards, fault, queue_path=os.path.join(BASE, "approval_queue.jsonl"))
        self.ctrl = Controller(self.t, guards)
        primary, secondary = make_providers(fault)
        self.gw = Gateway(self.t, primary, secondary, outage=(fault == "provider_outage"))
        self.mem_path = os.path.join(BASE, "sessions", f"{customer_id}.json")

    # ---------- حافظهٔ کوتاه‌مدت ----------
    def _mem_read(self):
        mem = json.load(open(self.mem_path, encoding="utf-8")) if os.path.exists(self.mem_path) else {}
        self.t.log("memory_read", 0, key=f"session:{self.customer_id}", value=mem)
        return mem

    def _mem_write(self, mem, step=0):
        os.makedirs(os.path.dirname(self.mem_path), exist_ok=True)
        json.dump(mem, open(self.mem_path, "w", encoding="utf-8"), ensure_ascii=False)
        self.t.log("memory_write", step, value=mem)

    # ---------- تأیید انسانی برای عمل پرریسک (ADR 3) ----------
    def _human_gate(self, step, tool, args):
        mode = self.approval
        if mode == "ask" and sys.stdin.isatty():
            ans = input(f"\n⚠ عمل پرریسک «{tool}» برای سفارش {args.get('order_id')} — اپراتور تأیید می‌کند؟ (y/n) ").strip().lower()
            mode = "approve" if ans in ("y", "yes", "بله") else "deny"
        elif mode == "ask":
            mode = "queue"
        self.t.log("approval", step, tool=tool, args=args, decision=mode)
        return mode

    def _quarantine(self, step, question, hit, nvar):
        """Dual LLM: متن نامطمئن فقط به مدل قرنطینه (بدون ابزار) می‌رسد؛ planner فقط نام متغیر را می‌بیند."""
        msgs = [{"role": "system", "content": QUARANTINE_PROMPT},
                {"role": "user", "content": f"پرسش: {question}\nسند:\n{hit['text']}"}]
        raw = self.gw.complete(step, msgs, role="quarantine")
        try:
            out = _parse(raw); errs = validate(out, QUARANTINE_SCHEMA)
        except (ValueError, json.JSONDecodeError) as e:
            out, errs = {"answer_text": ""}, [str(e)]
        var = f"$DOC{nvar}"
        self.t.log("quarantine", step, var=var, source=hit["id"], schema="pass" if not errs else "fail",
                   note="متن سند به planner داده نشد")
        return var, (out.get("answer_text", "") if not errs else "")

    def run(self, question):
        t = self.t
        t.log("run_start", 0, customer=self.customer_id, mode=os.getenv("MODE", "offline"), model=self.gw.primary.name,
              guards=self.level, fault=self.fault, prompt_version=prompt_version(), poisoned_kb=self.poisoned, question=question)
        flagged = self.ctrl.input_check(question)
        if flagged and self.level == "filter":
            final = {"status": "refused", "answer": "درخواست شما با سیاست‌های فروشگاه سازگار نیست.", "sources": [], "order_id": None}
            return self._end(final, 0)
        self.ctrl.make_plan(question)
        mem = self._mem_read()
        obs, evidence, final, repairs, vars_ = [], [], None, 0, {}
        system = system_prompt().replace("{tools}", ", ".join(self.tools.allowed()))
        step = 0
        for step in range(1, self.ctrl.max_steps + 2):
            if step > self.ctrl.max_steps:
                t.log("controller", step - 1, rule="budget", result="stop", budget="steps", used=step - 1,
                      limit=self.ctrl.max_steps, state="STOPPED_BUDGET")
                step -= 1
                break
            if not self.ctrl.budget_ok(step - 1):
                break
            user = (f"سؤال کاربر:\n{question}\n\nحافظه: last_order_id={mem.get('last_order_id', 'ندارد')}\n\nمشاهدات:\n" +
                    "\n".join("OBS " + json.dumps(o, ensure_ascii=False) for o in obs))
            msgs = [{"role": "system", "content": system}, {"role": "user", "content": user}]
            try:
                raw = self.gw.complete(step, msgs, role="planner")
            except ProviderDown as e:
                t.log("controller", step, rule="provider_unavailable", result="graceful_degradation", error=str(e))
                final = {"status": "escalated", "answer": "سرویس موقتاً در دسترس نیست؛ درخواست برای اپراتور ثبت شد.", "sources": [], "order_id": None}
                break
            try:
                action = _parse(raw)
                errs = validate(action, ACTION_SCHEMA)
            except (ValueError, json.JSONDecodeError) as e:
                action, errs = None, [str(e)]
            if errs:
                repairs += 1
                t.log("schema", step, target="action", result="fail", errors=errs, raw=raw[:80])
                if repairs > 1:
                    t.log("controller", step, rule="invalid_output_twice", result="fallback_escalate")
                    final = {"status": "escalated", "answer": "پاسخ معتبری تولید نشد؛ درخواست به اپراتور انسانی ارجاع شد.", "sources": [], "order_id": None}
                    break
                obs.append({"type": "error", "msg": "خروجی قبلی JSON معتبر نبود؛ فقط JSON طبق قالب برگردان"})
                continue
            t.log("decision", step, **{k: action[k] for k in ("action", "tool", "args", "query", "reason") if action.get(k) is not None})
            if not self.ctrl.check_action(step, action):
                final = {"status": "escalated", "answer": "عامل در حلقه گیر کرد؛ درخواست به اپراتور انسانی ارجاع شد.", "sources": [], "order_id": None}
                break

            if action["action"] == "retrieve":
                hits = self.kb.search(action.get("query") or question)
                t.log("retrieve", step, query=(action.get("query") or "")[:60], hits=[(h["id"], h["score"]) for h in hits])
                evidence.append({"type": "retrieve", "hits": hits})
                if self.guards and hits:
                    var, text = self._quarantine(step, question, hits[0], len(vars_) + 1)
                    vars_[var] = text
                    obs.append({"type": "quarantined", "var": var, "source": hits[0]["id"], "score": hits[0]["score"]})
                else:
                    obs.append({"type": "retrieve", "hits": hits})

            elif action["action"] == "tool":
                name, args = action.get("tool", ""), action.get("args") or {}
                if name not in self.tools.allowed():
                    t.log("controller", step, rule="least_privilege", result="blocked", tool=name, note="ابزار در فهرست مجاز این عامل نیست")
                    obs.append({"type": "tool", "tool": name, "result": {"error": "tool_not_allowed"}})
                    continue
                if not self.ctrl.tool_in_plan(step, name):
                    obs.append({"type": "tool", "tool": name, "result": {"error": "not_in_plan"}})
                    continue
                aerrs = validate(args, TOOL_ARG_SCHEMAS[name]) if name in TOOL_ARG_SCHEMAS else []
                t.log("schema", step, target=f"args:{name}", result="pass" if not aerrs else "fail", errors=aerrs)
                if aerrs:
                    obs.append({"type": "tool", "tool": name, "result": {"error": "invalid_args", "details": aerrs}})
                    continue
                if name in Tools.HIGH_RISK:
                    decision = self._human_gate(step, name, args)
                    if decision == "deny":
                        obs.append({"type": "tool", "tool": name, "result": {"error": "rejected_by_human"}})
                        continue
                result = None
                for attempt in (1, 2):
                    try:
                        result = getattr(self.tools, name)(**args)
                        break
                    except ToolError as e:
                        t.log("tool_call", step, tool=name, args=args, attempt=attempt, error=str(e))
                        if attempt == 1:
                            t.log("controller", step, rule="tool_failure", result="retry")
                if result is None:
                    t.log("controller", step, rule="tool_failure", result="graceful_degradation")
                    final = {"status": "escalated", "answer": "سامانهٔ سفارش‌ها موقتاً در دسترس نیست؛ درخواست شما برای اپراتور ثبت شد.", "sources": [], "order_id": None}
                    break
                t.log("tool_call", step, tool=name, args=args, customer_scope=self.customer_id if self.guards else "ALL",
                      result=result if name != "list_all_orders" else {"orders": len(result["orders"])})
                obs.append({"type": "tool", "tool": name, "result": result})
                evidence.append({"type": "tool", "tool": name, "result": result})

            elif action["action"] == "escalate":
                t.log("controller", step, rule="escalate", reason=action.get("reason"))
                final = {"status": "escalated", "answer": "درخواست شما به اپراتور انسانی ارجاع شد.", "sources": [], "order_id": None}
                break

            elif action["action"] == "finish":
                cand = action.get("final") or {}
                if self.guards and isinstance(cand.get("answer"), str):
                    for var, text in vars_.items():          # جایگذاری متغیر توسط کد قطعی، نه مدل
                        cand["answer"] = cand["answer"].replace(var, text)
                ferrs = validate(cand, FINAL_SCHEMA)
                t.log("schema", step, target="final_output", result="pass" if not ferrs else "fail", errors=ferrs)
                if ferrs:
                    repairs += 1
                    if repairs > 1:
                        final = {"status": "escalated", "answer": "پاسخ معتبری تولید نشد؛ ارجاع به اپراتور.", "sources": [], "order_id": None}
                        break
                    obs.append({"type": "error", "msg": "final با schema نمی‌خواند: " + "; ".join(ferrs)})
                    continue
                if self.level == "filter" and not self.ctrl.output_filter(step, cand):
                    final = {"status": "refused", "answer": "پاسخ به دلیل سیاست محتوا مسدود شد.", "sources": [], "order_id": None}
                    break
                if self.guards and not self.ctrl.output_check(step, cand):
                    final = {"status": "refused", "answer": "این درخواست خارج از حوزهٔ پشتیبانی فروشگاه است.", "sources": [], "order_id": None}
                    break
                if self.guards:
                    cand = self.ctrl.egress_check(step, cand)
                    problems = verify(cand, evidence, question, self.customer_id, self.db, t, step)
                    if problems:
                        leak = any("نشت" in p for p in problems)
                        final = {"status": "refused" if leak else "insufficient_info",
                                 "answer": "فقط اطلاعات سفارش‌های خود شما قابل نمایش است." if leak else "اطلاعات کافی و قابل استناد برای پاسخ ندارم.",
                                 "sources": [], "order_id": None}
                        break
                final = cand
                break
        if final is None:
            final = {"status": "escalated", "answer": "بودجهٔ این درخواست تمام شد؛ درخواست به اپراتور انسانی ارجاع شد.", "sources": [], "order_id": None}
        if final.get("order_id"):
            mem["last_order_id"] = final["order_id"]
            self._mem_write(mem, step)
        return self._end(final, step)

    def _end(self, final, step):
        t = self.t
        s = t.summary()
        t.log("run_end", step, status=final["status"], **{k: (f"{v:.6f}" if k == "cost_usd" else v) for k, v in s.items() if k != "trace_file"})
        return {"final": final, "summary": s, "events": t.events}
