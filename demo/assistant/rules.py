"""منطق قطعی (rule engine) برای قاعده‌های الزام‌آور آیین‌نامه؛ مدل در این تصمیم نقشی ندارد."""
import re

FA = str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789")
RETURN_WINDOW_DAYS = 7   # آیین‌نامه، بند ۱: مرجوعی تا ۷ روز پس از تحویل


def jalali_to_jdn(y, m, d):
    """شمارهٔ روز (Julian Day Number) برای تاریخ شمسی؛ الگوریتم حسابی رایج (معتبر برای ۱۳۰۰ تا ۱۴۹۹)."""
    epbase = y - 474 if y >= 0 else y - 473
    epyear = 474 + epbase % 2820
    mdays = (m - 1) * 31 if m <= 7 else (m - 1) * 30 + 6
    return d + mdays + (epyear * 682 - 110) // 2816 + (epyear - 1) * 365 + epbase // 2820 * 1029983 + 1948320


def parse(s):
    y, m, d = (int(x) for x in re.split(r"[/\-]", s.translate(FA).strip()))
    return y, m, d


def refund_allowed(delivered, today, window=RETURN_WINDOW_DAYS):
    days = jalali_to_jdn(*parse(today)) - jalali_to_jdn(*parse(delivered))
    return {"delivered": delivered, "today": today, "days_since_delivery": days, "window_days": window,
            "allowed": 0 <= days <= window, "verdict": "بله" if 0 <= days <= window else "خیر",
            "rule": f"days_since_delivery ({days}) <= window_days ({window})"}
