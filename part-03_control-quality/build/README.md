# ساخت اسلایدهای بخش ۳

`build_v2.py` نسخهٔ ۱ را از `slides/archive/part-03_v1.pptx` می‌خواند، شکل‌های `fig/` و تصویرهای `ui_shots/` را اضافه می‌کند و نتیجه را در `slides/archive/part-03_v2.pptx` می‌نویسد (نسخهٔ جاری دیگر v3 است).

`build_v3.py` نسخهٔ ۲ را از `slides/archive/part-03_v2.pptx` می‌خواند، یادداشت‌های راست‌چین و بلوک‌های «▶ عملی» را می‌نویسد و نتیجه را در `slides/part-03_v3.pptx` می‌گذارد (اکنون در `slides/archive/`).

`build_v4.py` نسخهٔ ۳ را از `slides/archive/part-03_v3.pptx` می‌خواند، همهٔ ارجاع‌های [n] و خط‌های منبع زیر شکل‌ها را از اسلایدها حذف می‌کند (اسلایدهای منابع پایانی و یادداشت‌ها بدون تغییر) و نتیجه را در `slides/part-03_v4.pptx` می‌نویسد.

`guide_v3.py` راهنمای شخصی ارائه را در `private/Guide_Part3_Matin_v3.docx` می‌سازد. آن پوشه در git نیست.

از پوشهٔ `part-03_control-quality`:

```bash
python build/build_v3.py
python build/build_v4.py
python build/guide_v3.py
```

نیاز به `python-pptx` (و برای راهنما `python-docx`) و فونت AradFDVF نصب‌شده روی سیستم دارد. این فونت تجاری است و در مخزن نیست.

پوشهٔ دموی این مخزن `demo/` است (در ریشه). اگر در یادداشت‌ها نام `demo_v4` آمده، همان پوشه است.
