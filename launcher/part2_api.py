"""نقطهٔ ورود uvicorn برای backend دموی بخش ۲ با «حالت mock پشتیبان» — بدون هیچ تغییری در submodule آرشیا.

لانچر backend را با `uvicorn part2_api:app` (از پوشهٔ backend) اجرا می‌کند. این فایل فقط
build_embedder خود backend را می‌پوشاند:

  DEMO_EMBEDDINGS=auto  (پیش‌فرض) مدل محلی sentence-transformers؛ اگر بار نشد یا هر جا خطا داد،
                        خودکار به embedder ساختگی (HashingEmbedder خود backend) برمی‌گردد و
                        بردارهای پایگاه دانش را دوباره با همان می‌سازد. BM25 دست‌نخورده می‌ماند.
  DEMO_EMBEDDINGS=mock  از اول بدون مدل embedding (سریع‌ترین و مطمئن‌ترین حالت).
  DEMO_EMBEDDINGS=local رفتار اصلی backend: اگر مدل نبود، backend بالا نمی‌آید.

LLM هم در حالت آفلاین لانچر mock است و خود backend در هر خطای API به mock برمی‌گردد.
"""
from __future__ import annotations

import logging
import os
import sys

if os.getcwd() not in sys.path:   # لانچر این را از پوشهٔ backend اجرا می‌کند
    sys.path.insert(0, os.getcwd())

from app.knowledge import embeddings as _E

MODE = os.getenv("DEMO_EMBEDDINGS", "auto").strip().lower() or "auto"
_log = logging.getLogger("uvicorn.error")
_original_build = _E.build_embedder


class ResilientEmbedder(_E.Embedder):
    """embedder اصلی را صدا می‌زند و در اولین خطا برای همیشه روی mock می‌رود."""

    def __init__(self, inner: _E.Embedder | None, reason: str | None = None) -> None:
        self.inner = inner
        self.mock: _E.Embedder | None = None if inner is not None else _E.HashingEmbedder()
        self.reason = reason

    @property
    def name(self) -> str:
        return f"mock:{self.mock.name}" if self.mock is not None else self.inner.name

    def _switch(self, reason: str) -> None:
        self.mock, self.reason = _E.HashingEmbedder(), reason
        _log.warning("embedding → mock: %s", reason)
        from app.knowledge import ingest   # بردارهای پایگاه دانش را با embedder جدید بازسازی کن

        idx = getattr(ingest, "_index", None)
        if idx is not None and idx.chunks:
            idx.store.clear()
            idx.store.add(self.mock.embed([c.text for c in idx.chunks]))
            idx.embedding_warning = reason

    def embed(self, texts):
        if self.mock is None:
            try:
                return self.inner.embed(texts)
            except Exception as exc:  # noqa: BLE001
                if MODE == "local":
                    raise
                self._switch(f"حالت mock: مدل embedding خطا داد ({type(exc).__name__}: {exc})")
        return self.mock.embed(texts)


def build_embedder():
    if MODE == "mock":
        reason = "حالت mock: DEMO_EMBEDDINGS=mock (بدون مدل embedding)"
        _log.warning(reason)
        return ResilientEmbedder(None, reason), reason
    try:
        inner, warn = _original_build()
    except Exception as exc:  # noqa: BLE001
        if MODE == "local":
            raise
        reason = f"حالت mock: مدل embedding بار نشد ({type(exc).__name__}: {str(exc)[:300]})"
        _log.warning(reason)
        return ResilientEmbedder(None, reason), reason
    return ResilientEmbedder(inner, warn), warn


_E.build_embedder = build_embedder
from app.knowledge import ingest as _ingest  # noqa: E402

_ingest.build_embedder = build_embedder

from app.main import app  # noqa: E402,F401

# CORS: backend فقط localhost:3000 را قبول می‌کند؛ لانچر frontend را روی پورت دیگری (8082) اجرا می‌کند
# و آن مبدأ را با DEMO_WEB_ORIGINS می‌دهد. فقط فهرست مبدأها اضافه می‌شود؛ submodule دست نمی‌خورد.
_extra = [o.strip() for o in os.getenv("DEMO_WEB_ORIGINS", "").split(",") if o.strip()]
if _extra:
    from starlette.middleware.cors import CORSMiddleware as _CORS

    for _m in app.user_middleware:
        if _m.cls is _CORS:
            _opts = getattr(_m, "kwargs", None) or getattr(_m, "options", None)
            if isinstance(_opts, dict):
                _opts["allow_origins"] = list(dict.fromkeys([*_opts.get("allow_origins", []), *_extra]))
