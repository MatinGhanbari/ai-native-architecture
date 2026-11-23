"""اجرای هر دو دمو در یک برنامه: python run_all.py  →  صفحهٔ شروع روی http://127.0.0.1:8700

فقط کتابخانهٔ استاندارد Python. هیچ فایلی از دموها تغییر نمی‌کند؛ هر دمو مثل قبل با پورت خودش بالا می‌آید
و صفحهٔ شروع فقط به آن‌ها لینک می‌دهد. جزئیات: launcher/README.md
"""
import os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from launcher.server import main

if __name__ == "__main__":
    main()
