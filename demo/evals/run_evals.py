"""اجراکنندهٔ ارزیابی = fitness function معماری. در CI: اگر نرخ قبولی از آستانه کمتر شود، exit code=1.
اجرا:  python evals/run_evals.py [--min-pass 1.0] [--judge]"""
import argparse, json, os, sys
sys.stdout.reconfigure(encoding="utf-8")
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)
from assistant.agent import Agent
from assistant.schema import FINAL_SCHEMA, validate
from assistant.textutil import to_fa

MAX_STEPS, MAX_COST_USD = 5, 0.01   # بودجهٔ هر پرسش (ویژگی کیفی هزینه)

JUDGE_PROMPT = """تو داور هستی. با توجه به «منبع» و «پاسخ»، به وفاداری پاسخ به منبع از ۱ تا ۵ نمره بده.
فقط JSON برگردان: {"score": <1-5>, "reason": "..."}"""

def judge(case, out):
    """LLM-as-a-judge (فقط در MODE=real). در حالت آفلاین اجرا نمی‌شود."""
    from assistant.llm import RealLLM
    ev = json.dumps([e for e in out["events"] if e["event"] in ("retrieve", "tool_call")], ensure_ascii=False)[:3000]
    raw = RealLLM().complete([{"role": "system", "content": JUDGE_PROMPT},
                              {"role": "user", "content": f"منبع: {ev}\nپاسخ: {out['final']['answer']}"}])
    import re
    return json.loads(re.search(r"\{.*\}", raw, re.S).group(0))

def check(case, out):
    f, s, ev = out["final"], out["summary"], out["events"]
    fails = []
    if validate(f, FINAL_SCHEMA): fails.append("schema")
    if f["status"] not in case["expect_status"]: fails.append(f"status={f['status']}")
    for w in case.get("must_contain", []):
        if w not in f["answer"]: fails.append(f"بدون «{w}»")
    for w in case.get("must_not_contain", []):
        if w in f["answer"]: fails.append(f"نشت «{w}»")
    if case.get("expect_source") and case["expect_source"] not in f["sources"]: fails.append("منبع اشتباه")
    if case.get("expect_tool") and not any(e["event"] == "tool_call" and e.get("tool") == case["expect_tool"] for e in ev):
        fails.append("ابزار صدا زده نشد")
    if case.get("expect_event") and not any(e["event"] == case["expect_event"] for e in ev):
        fails.append(f"رویداد {case['expect_event']} نبود")
    if s["steps"] > MAX_STEPS: fails.append("گام زیاد")
    if s["cost_usd"] > MAX_COST_USD: fails.append("هزینه زیاد")
    return fails

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-pass", type=float, default=1.0)
    ap.add_argument("--judge", action="store_true", help="LLM-as-a-judge (فقط MODE=real)")
    a = ap.parse_args()
    cases = [json.loads(l) for l in open(os.path.join(BASE, "evals", "dataset.jsonl"), encoding="utf-8") if l.strip()]
    results, passed = [], 0
    print(f"ارزیابی {to_fa(len(cases))} مورد  (MODE={os.getenv('MODE', 'offline')})\n")
    for c in cases:
        mem = os.path.join(BASE, "sessions", f"{c['customer']}.json")
        if os.path.exists(mem): os.remove(mem)           # هر مورد با حافظهٔ تمیز
        out = Agent(c["customer"], fault=c.get("fault"), approval="queue", verbose=False).run(c["q"])
        fails = check(c, out)
        j = None
        if a.judge and os.getenv("MODE") == "real" and out["final"]["status"] == "answered":
            j = judge(c, out)
            if j.get("score", 0) < 4: fails.append(f"judge={j.get('score')}")
        ok = not fails; passed += ok
        print(f"{'✅' if ok else '❌'} {c['id']:<24} status={out['final']['status']:<17} گام={to_fa(out['summary']['steps'])} {'; '.join(fails)}")
        results.append({"id": c["id"], "pass": ok, "fails": fails, "status": out["final"]["status"],
                        "steps": out["summary"]["steps"], "cost_usd": out["summary"]["cost_usd"], "judge": j})
    rate = passed / len(cases)
    json.dump({"pass_rate": rate, "results": results}, open(os.path.join(BASE, "evals", "report.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(f"\nنرخ قبولی: {to_fa(passed)}/{to_fa(len(cases))} = {rate:.0%}   آستانه: {a.min_pass:.0%}")
    if rate < a.min_pass:
        print("❌ fitness function شکست خورد؛ این تغییر نباید merge شود."); sys.exit(1)
    print("✅ fitness function برقرار است.")

if __name__ == "__main__":
    main()
