# دموی بخش‌های ۱ و ۲

این دمو برای هر دو بخش اول و دوم است: نقشهٔ اجرای درخواست (RAG، ابزار سفارش، حافظه، ارجاع انسانی) و نمای تعاملی C4.

- `software-architecture-demo/`: مخزن جدا به‌صورت submodule، https://github.com/SArshiaK/software-architecture-demo
- `recording-2026-11-23.mp4`: فیلم ضبط‌شده از اجرای همین دمو

پس از کلون این مخزن:

```bash
git submodule update --init --recursive
```

## اجرا

ساده‌ترین راه، اجرای هر دو دمو از ریشهٔ مخزن است: `python run_all.py`. صفحهٔ شروع روی http://127.0.0.1:8700 باز می‌شود. این دمو روی http://127.0.0.1:3000 و نمای C4 روی http://127.0.0.1:3000/architecture است. لانچر هیچ فایلی از submodule را تغییر نمی‌دهد.

اجرای دستی طبق `software-architecture-demo/README.md` است: backend روی پورت 8000 و frontend روی پورت 3000.

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
- **Backend:** FastAPI + uvicorn (Python). ماژول‌ها: `orchestrator` (حلقهٔ عامل، حداکثر چند گام)، `knowledge` (RAG ترکیبی BM25 + بردار)، `tools/order_status` (ابزار فقط‌خواندنی سفارش از `data/orders_db.json`)، `memory` (حافظهٔ نشست در RAM، ۶ نوبت آخر)، `handoff` (صف اپراتور در RAM)، `llm` (mock یا API سازگار با OpenAI)، `trace` (ساخت مسیر اجرا برای نمایش).
- **Frontend:** Next.js 15.5 (App Router، Turbopack) + React 19، Tailwind 4، shadcn/base-ui، `@xyflow/react` برای نمودار و framer-motion برای انیمیشن. صفحهٔ `/` مسیر اجرا را نشان می‌دهد و `/architecture` نمای C4 لایه‌لایه با ADR است.
- **API:** `GET /health`، `POST /chat`، `POST /session/reset`، `GET /admin/handoffs`، `POST /admin/reindex`، `POST /debug/retrieve`.
- Docker لازم نیست.

**وابستگی‌ها و حجم:** backend به `sentence-transformers` و در نتیجه PyTorch نیاز دارد (چند صد مگابایت). مدل embedding (`paraphrase-multilingual-MiniLM-L12-v2`) بار اول از Hugging Face دانلود و بعد از cache خوانده می‌شود. frontend به `node_modules` نیاز دارد.

**کلید API و حالت آفلاین**
- پیش‌فرض `LLM_PROVIDER=mock` است و کلید لازم نیست. پاسخ‌ها از mock قطعی می‌آیند و badge صفحه «mock» نشان می‌دهد.
- با `LLM_PROVIDER=openai` و `LLM_API_KEY` (پیش‌فرض `.env`: AvalAI با مدل `deepseek-v4-flash`) مدل واقعی صدا زده می‌شود. اگر کلید خالی باشد، خودکار به mock برمی‌گردد.
- backend بدون اینترنت کار می‌کند، به شرطی که مدل embedding یک بار دانلود شده باشد. روی لپ‌تاپ متین در cache هست.
- frontend فونت‌ها را با `next/font/google` از Google Fonts می‌گیرد. بدون اینترنت، Next.js در حالت dev فونت جایگزین نشان می‌دهد و صفحه باز می‌شود، اما ظاهر فونت فرق می‌کند. بهتر است قبل از ارائه یک بار با اینترنت اجرا شود.

**نکته‌ها و ایرادهای کوچک** (هیچ‌کدام تغییر داده نشده است)
1. **CORS:** فقط `localhost:3000` و `127.0.0.1:3000` مجاز است. یعنی frontend باید روی پورت 3000 اجرا شود. آدرس backend از `NEXT_PUBLIC_API_BASE_URL` خوانده می‌شود و پیش‌فرضش `http://127.0.0.1:8000` است.
2. **`.env`:** نسبت به پوشهٔ جاری خوانده می‌شود، پس uvicorn باید از داخل `backend/` اجرا شود. لانچر همین کار را می‌کند.
3. **README داخل submodule:** به `frontend/.env.local.example` اشاره می‌کند، ولی این فایل وجود ندارد. لازم هم نیست، چون مقدار پیش‌فرض درست است.
4. **`.venv` و مسیر قدیمی:** `.venv` روی این سیستم در مسیر قدیمی `demo-1/` ساخته شده است. `uvicorn.exe` داخل آن ممکن است مسیر قدیمی را صدا بزند. برای همین لانچر از `.venv\Scripts\python.exe -m uvicorn` استفاده می‌کند که مشکلی ندارد.
5. **شروع کند و شکست سخت:** شروع backend به‌خاطر بار کردن مدل embedding ده‌ها ثانیه طول می‌کشد. اگر embedding بار نشود، backend عمداً بالا نمی‌آید.
6. **کد بی‌استفاده:** `HashingEmbedder` استفاده نمی‌شود و `memory_max_turns` در تنظیمات هم بی‌اثر است، چون مقدارش در `memory/store.py` ثابت نوشته شده.
7. **هشدار Next.js:** Next.js دربارهٔ چند `package-lock.json` (یکی در `C:\Users\Matin`) هشدار workspace root می‌دهد. این هشدار بی‌خطر است.
8. **حافظه و صف اپراتور:** فقط در RAM هستند و با هر بار راه‌اندازی خالی می‌شوند.
