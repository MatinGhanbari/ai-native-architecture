# دموی بخش ۲

این دمو مال بخش دوم است: نقشهٔ اجرای درخواست (RAG، Router، ابزار سفارش، حافظه، ارجاع انسانی) و نمودار معماری `/architecture`. دموی بخش اول جداست: `part-01/demo/c4-explorer.html`.

- `software-architecture-demo/`: مخزن جدا به‌صورت submodule، https://github.com/SArshiaK/software-architecture-demo
- `recording-2026-11-23.mp4`: فیلم ضبط‌شده از اجرای همین دمو

پس از کلون این مخزن:

```bash
git submodule update --init --recursive
```

## اجرا

ساده‌ترین راه، اجرای هر دو دمو از ریشهٔ مخزن است: `python run_all.py`. صفحهٔ شروع روی http://127.0.0.1:8080 باز می‌شود. این دمو روی http://127.0.0.1:8082 و نمودار معماری آن روی http://127.0.0.1:8082/architecture است (دکمهٔ «نمودار معماری» در کارت بخش دوم). لانچر هیچ فایلی از submodule را تغییر نمی‌دهد.

حالت مدل با `python run_all.py --llm offline|9router|lmstudio` انتخاب می‌شود. پیش‌فرض `LLM_PROFILE` در `.env` ریشه است. لانچر `LLM_PROVIDER`، `LLM_BASE_URL` و `LLM_MODEL` را به backend می‌دهد که از `backend/.env` اولویت دارند. در حالت زنده، backend به پراکسی لانچر (`127.0.0.1:8085`) وصل می‌شود. کلید واقعی فقط دست پراکسی است. پراکسی `<think>` را حذف می‌کند، `stream=false` می‌گذارد و `/embeddings` را می‌بندد تا embedding همیشه محلی بماند. اگر provider خاموش باشد، این دمو خودش به mock برمی‌گردد و badge صفحه دلیلش را نشان می‌دهد.

اجرای دستی طبق `software-architecture-demo/README.md` است: backend روی پورت 8000 و frontend روی پورت 3000 (پیش‌فرض خود اپ). لانچر به‌جای آن‌ها 8083 و 8082 را به کار می‌برد.

### نصب یک‌باره (اگر روی سیستم جدید هستید)

```bash
cd software-architecture-demo/backend
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
copy .env.example .env
cd ../frontend
npm install
```

## بررسی کد

**ساختار**
- **Backend:** FastAPI + uvicorn (Python). ماژول‌ها: `orchestrator` (حلقهٔ عامل، حداکثر چند گام)، `llm/router` (مدل سبک تریاژ: `continue` | `handoff_refund` با schema validation)، `knowledge` (RAG ترکیبی BM25 + بردار)، `tools/order_status` (ابزار فقط‌خواندنی سفارش از `data/orders_db.json`)، `memory` (حافظهٔ نشست در RAM، ۶ نوبت آخر)، `handoff` (صف اپراتور در RAM)، `llm` (mock یا API سازگار با OpenAI)، `trace` (ساخت مسیر اجرا برای نمایش).
- **Frontend:** Next.js 15.5 (App Router، Turbopack) + React 19، Tailwind 4، shadcn/base-ui، `@xyflow/react` برای نمودار و framer-motion برای انیمیشن. صفحهٔ `/` مسیر اجرا را نشان می‌دهد و `/architecture` نمای C4 لایه‌لایه با ADR است.
- **API:** `GET /health`، `POST /chat`، `POST /session/reset`، `GET /admin/handoffs`، `POST /admin/reindex`، `POST /debug/retrieve`.
- Docker لازم نیست.

**وابستگی‌ها و حجم:** backend به `sentence-transformers` و در نتیجه PyTorch نیاز دارد (چند صد مگابایت). مدل embedding (`paraphrase-multilingual-MiniLM-L12-v2`) بار اول از Hugging Face دانلود و بعد از cache خوانده می‌شود. frontend به `node_modules` نیاز دارد.

**کلید API و حالت آفلاین**
- پیش‌فرض `LLM_PROVIDER=mock` است و کلید لازم نیست. پاسخ‌ها از mock قطعی می‌آیند و badge صفحه «mock» نشان می‌دهد.
- با `LLM_PROVIDER=openai` و `LLM_API_KEY` (پیش‌فرض `.env`: AvalAI با مدل `deepseek-v4-flash`) مدل واقعی صدا زده می‌شود. اگر کلید خالی باشد، خودکار به mock برمی‌گردد.
- backend بدون اینترنت کار می‌کند، به شرطی که مدل embedding یک بار دانلود شده باشد. روی سیستم متین در cache هست. اگر نبود، دمو خودکار روی mock می‌رود (پایین را ببینید).
- frontend فونت‌ها را با `next/font/google` از Google Fonts می‌گیرد. بدون اینترنت، Next.js در حالت dev فونت جایگزین نشان می‌دهد و صفحه باز می‌شود، اما ظاهر فونت فرق می‌کند. بهتر است قبل از ارائه یک بار با اینترنت اجرا شود.

**نکته‌ها و ایرادهای کوچک** (هیچ‌کدام تغییر داده نشده است)
1. **CORS:** فقط `localhost:3000` و `127.0.0.1:3000` مجاز است. لانچر frontend را روی 8082 اجرا می‌کند و این مبدأ را با `DEMO_WEB_ORIGINS` در `launcher/part2_api.py` به CORS اضافه می‌کند. آدرس backend از `NEXT_PUBLIC_API_BASE_URL` خوانده می‌شود و پیش‌فرضش `http://127.0.0.1:8000` است.
2. **`.env`:** نسبت به پوشهٔ جاری خوانده می‌شود، پس uvicorn باید از داخل `backend/` اجرا شود. لانچر همین کار را می‌کند.
3. **README داخل submodule:** به `frontend/.env.local.example` اشاره می‌کند، ولی این فایل وجود ندارد. لازم هم نیست، چون مقدار پیش‌فرض درست است.
4. **`.venv` و مسیر قدیمی:** `.venv` روی این سیستم در مسیر قدیمی `demo-1/` ساخته شده است. `uvicorn.exe` داخل آن ممکن است مسیر قدیمی را صدا بزند. برای همین لانچر از `.venv\Scripts\python.exe -m uvicorn` استفاده می‌کند که مشکلی ندارد.
5. **شروع کند و شکست سخت:** شروع backend به‌خاطر بار کردن مدل embedding ده‌ها ثانیه طول می‌کشد. اگر embedding بار نشود، خود backend عمداً بالا نمی‌آید؛ لانچر با `launcher/part2_api.py` در این حالت به mock برمی‌گردد.
6. **کد بی‌استفاده:** `HashingEmbedder` استفاده نمی‌شود و `memory_max_turns` در تنظیمات هم بی‌اثر است، چون مقدارش در `memory/store.py` ثابت نوشته شده.
7. **هشدار Next.js:** Next.js دربارهٔ چند `package-lock.json` (یکی در `C:\Users\Matin`) هشدار workspace root می‌دهد. این هشدار بی‌خطر است.
8. **حافظه و صف اپراتور:** فقط در RAM هستند و با هر بار راه‌اندازی خالی می‌شوند.

## بدون اینترنت و حالت mock پشتیبان

- **مدل embedding:** `paraphrase-multilingual-MiniLM-L12-v2` یک بار در cache هاگینگ‌فیس روی همین سیستم دانلود شده است. لانچر backend را با `HF_HUB_OFFLINE=1` و `TRANSFORMERS_OFFLINE=1` اجرا می‌کند تا هیچ درخواستی به اینترنت نرود.
- **mock خودکار:** لانچر backend را با `uvicorn part2_api:app` اجرا می‌کند (`launcher/part2_api.py`). این همان `app.main:app` است و فقط ساخت embedder را می‌پوشاند. اگر مدل embedding بار نشود، یا وسط کار خطا بدهد، backend خودکار به embedder ساختگی (`HashingEmbedder` خود backend) برمی‌گردد و بردارهای پایگاه دانش را دوباره می‌سازد. BM25، ابزار سفارش، Router و LLM mock مثل قبل کار می‌کنند. در `/health` مقدار `embedder` برابر `mock:hashing-fallback` می‌شود و `warning` دلیلش را می‌گوید.
- **LLM:** در حالت `offline` (پیش‌فرض)، `LLM_PROVIDER=mock` است. در حالت زنده هم اگر API خطا بدهد، خود backend به mock برمی‌گردد.
- **اگر باز هم بالا نیامد:** لانچر یک بار دیگر backend را با `DEMO_EMBEDDINGS=mock` اجرا می‌کند.
- **سوییچ دستی:** `python run_all.py --embeddings mock` (بدون مدل embedding، سریع‌ترین شروع)، `--embeddings local` (رفتار اصلی: بدون مدل، backend بالا نمی‌آید)، پیش‌فرض `--embeddings auto`. همین را با متغیر `DEMO_EMBEDDINGS` در `.env` ریشه هم می‌شود گذاشت.
- **فونت‌های frontend:** `next/font/google` با `NEXT_FONT_GOOGLE_MOCKED_RESPONSES=launcher/next_font_mock.js` فونت‌ها را از `part-01/demo/vendor/fonts/` می‌خواند.

هیچ‌کدام از این‌ها فایلی داخل submodule آرشیا را عوض نمی‌کند.
