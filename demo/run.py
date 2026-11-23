"""اجرای یک پرسش: python run.py --customer C001 "مهلت مرجوعی چند روز است؟" """
import argparse, json, os, sys
sys.stdout.reconfigure(encoding="utf-8")
from assistant.agent import Agent
from assistant import profiles
from assistant.textutil import to_fa

p = argparse.ArgumentParser(description="دستیار پشتیبانی فروشگاه (دموی AI-native، نسخهٔ ۲)")
p.add_argument("question")
p.add_argument("--customer", default="C001", help="مشتری احرازهویت‌شده (از نشست، نه از مدل)")
g = p.add_mutually_exclusive_group()
g.add_argument("--no-guards", action="store_true", help="فقط RAG، بدون هیچ دفاعی (برای نمایش حمله)")
g.add_argument("--filters-only", action="store_true", help="فقط فیلتر متنی ورودی/خروجی، بدون دفاع ساختاری")
p.add_argument("--poisoned-kb", action="store_true", help="افزودن سند بیرونی آلوده به پایگاه دانش (تزریق غیرمستقیم)")
p.add_argument("--fault", choices=["tool_error", "loop", "runaway", "bad_json", "off_scope_output", "provider_outage"],
               help="تزریق خطا برای نمایش Controller و Gateway")
p.add_argument("--approval", choices=["queue", "ask", "approve", "deny"], help="رفتار دروازهٔ تأیید انسانی")
p.add_argument("--quiet", action="store_true")
a = p.parse_args()

level = "off" if a.no_guards else ("filter" if a.filters_only else "full")
agent = Agent(a.customer, guards=level, fault=a.fault, approval=a.approval, verbose=not a.quiet, poisoned_kb=a.poisoned_kb or None)
names = {"off": "خاموش (فقط RAG)", "filter": "فقط فیلتر", "full": "کامل (ساختاری)"}
print(f"\n❓ {a.question}   (مشتری: {a.customer}، حالت: {profiles.current()}، guards: {names[level]})\n")
out = agent.run(a.question)
f, s = out["final"], out["summary"]
print("\n✅ خروجی نهایی (معتبر طبق JSON Schema):")
print(json.dumps(f, ensure_ascii=False, indent=2))
print(f"\n📊 گام‌ها: {to_fa(s['steps'])} | فراخوانی مدل: {to_fa(s['llm_calls'])} | token ورودی≈{to_fa(s['tokens_in'])} خروجی≈{to_fa(s['tokens_out'])}"
      f" | هزینهٔ تخمینی≈${s['cost_usd']:.6f} | تأخیر: {to_fa(s['latency_ms'])}ms | trace: {os.path.relpath(s['trace_file'])}")
