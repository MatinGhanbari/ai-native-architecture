import re
FA_DIGITS = "۰۱۲۳۴۵۶۷۸۹"; AR_DIGITS = "٠١٢٣٤٥٦٧٨٩"
_TO_LATIN = {ord(c): str(i) for i, c in enumerate(FA_DIGITS)}
_TO_LATIN.update({ord(c): str(i) for i, c in enumerate(AR_DIGITS)})

def norm(s: str) -> str:
    """یکسان‌سازی حروف و ارقام برای مقایسهٔ قطعی."""
    s = s.translate(_TO_LATIN).replace("ي", "ی").replace("ك", "ک").replace("ة", "ه")
    s = s.replace("\u200c", " ").replace("ـ", "")
    return re.sub(r"\s+", " ", s).strip()

def to_fa(s) -> str:
    return str(s).translate({ord(str(i)): FA_DIGITS[i] for i in range(10)})

def numbers(s: str):
    return re.findall(r"\d+", norm(s))

def order_ids(s: str):
    return re.findall(r"(?<!\d)(\d{4})(?!\d)", norm(s))

def est_tokens(s: str) -> int:
    """تخمین سادهٔ تعداد token (حدود ۴ نویسه به ازای هر token)؛ فقط برای برآورد هزینه."""
    return max(1, (len(s) + 3) // 4)
