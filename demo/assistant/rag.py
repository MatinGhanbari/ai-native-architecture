"""پایگاه دانش: بازیابی ساده بر اساس n-gram نویسه‌ای روی بندهای آیین‌نامه (بدون وابستگی بیرونی)."""
import math, re
from collections import Counter
from .textutil import norm

STOP = {"چند", "است", "را", "به", "از", "در", "که", "و", "آیا", "من", "چه", "یک", "می", "ها", "برای", "با", "این"}

def _grams(text, n=3):
    words = [w for w in re.findall(r"\w+", norm(text)) if w not in STOP]
    c = Counter()
    for w in words:
        w = f" {w} "
        for i in range(max(1, len(w) - n + 1)):
            c[w[i:i + n]] += 1
    return c

def _cos(a, b):
    dot = sum(v * b.get(k, 0) for k, v in a.items())
    na = math.sqrt(sum(v * v for v in a.values())); nb = math.sqrt(sum(v * v for v in b.values()))
    return dot / (na * nb) if na and nb else 0.0

class KnowledgeBase:
    def __init__(self, paths):
        if isinstance(paths, str): paths = [paths]
        text = "\n".join(open(p, encoding="utf-8").read() for p in paths)
        self.chunks = []
        for m in re.finditer(r"^## (.+?)\n(.+?)(?=^## |\Z)", text, re.S | re.M):
            title, body = m.group(1).strip(), m.group(2).strip()
            self.chunks.append({"id": f"آیین‌نامه §{title.split('.')[0]}", "title": title, "text": body,
                                "vec": _grams(title + " " + title + " " + body)})

    def search(self, query, k=2):
        q = _grams(query)
        scored = sorted(({"id": c["id"], "title": c["title"], "text": c["text"], "score": round(_cos(q, c["vec"]), 3)}
                         for c in self.chunks), key=lambda x: -x["score"])
        return scored[:k]
