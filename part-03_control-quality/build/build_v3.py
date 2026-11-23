import re
from pathlib import Path
from pptx import Presentation
from pptx.oxml.ns import qn
from lxml import etree
_ROOT = Path(__file__).resolve().parents[1]
M = str(_ROOT)
p=Presentation(str(_ROOT / 'slides' / 'archive' / 'part-03_v2.pptx'))
BACK='سپس با Alt+Tab برگرد به اسلاید.'
FB='اگر اجرای زنده خطا داد، رابط خودش نتیجهٔ ذخیره‌شده را با برچسب precomputed نشان می‌دهد؛ اگر مرورگر کلاً باز نشد، تصویر همین اسلاید کافی است.'
SETUP=('▶ آماده‌سازی پیش از ارائه (قبل از شروع کلاس):\n'
 '۱. در پوشهٔ demo_v4 یک PowerShell باز کن و بزن: python run_ui.py — مرورگر روی http://127.0.0.1:8765 باز می‌شود.\n'
 '۲. سوییچ بالای صفحه روی «آفلاین» باشد (نه «مدل واقعی»).\n'
 '۳. یک بار دکمهٔ reset را بزن تا حافظهٔ نشست و صف تأیید خالی شود.\n'
 '۴. مرورگر را روی مرحلهٔ ۱ نگه دار، بزرگ‌نمایی را برای پروژکتور تنظیم کن و با Alt+Tab بین PowerPoint و مرورگر جابه‌جا شو.\n'
 '۵. اگر درگاه اشغال بود: $env:UI_PORT="8800"; python run_ui.py')
D={
29:('[کلیک ۳]\n',
 '▶ عملی: به مرورگر برو، مرحلهٔ ۱ دمو «حمله با سند آلوده». اول به کامنت پنهان قرمز داخل سند اشاره کن. دکمهٔ «اجرا (guards خاموش)» را بزن. در پاسخ به لینک تصویر sync.pakhsh-hamkar و نام مشتریان دیگر (علی رضایی، مریم کریمی) اشاره کن؛ در پنل trace سمت چپ به فراخوانی list_all_orders. '+BACK+' '+FB+'\n'),
36:('[کلیک ۱]\n',
 '▶ عملی: به مرورگر برو، مرحلهٔ ۲ دمو (کلید ← یا دایرهٔ ۲). در سه ستون به ترتیب «بدون دفاع»، «فقط فیلتر» و «دفاع ساختاری» دکمهٔ «اجرا» را بزن. در ستون «فقط فیلتر» به لینک نشت در پاسخ و به output_filter result=pass در trace اشاره کن. در ستون «دفاع ساختاری» به قرنطینهٔ سند و egress_allowlist blocked اشاره کن. '+BACK+' بعد کلیک ۲ را بزن. '+FB+'\n'),
40:('[کلیک ۱]\n',
 '▶ عملی: به مرورگر برو، مرحلهٔ ۳ دمو «eval در CI». prompt را روی support-v3 بگذار و «اجرای eval» را بزن: ۱۴ از ۱۴، CI passed. بعد support-v4 را انتخاب کن و دوباره «اجرای eval»: ۱۰ از ۱۴، CI blocked؛ به چهار ردیف قرمز آیین‌نامه اشاره کن. اگر کند بود، دکمهٔ «نتیجهٔ از پیش آماده» را بزن و بگو precomputed است. '+BACK+'\n'),
43:('[کلیک ۱]\n',
 '▶ عملی: به مرورگر برو، مرحلهٔ ۴ دمو «Controller و بودجه». دکمهٔ «اجرای حلقهٔ runaway» را بزن و به نوار بودجهٔ گام اشاره کن که تا STOPPED_BUDGET پر می‌شود. بعد کلید ← برای مرحلهٔ ۵ «قطعی ارائه‌دهنده»: تیک «مدل اصلی قطع است» از قبل زده است؛ «اجرا» را بزن و در trace به timeout، retry، circuit breaker و fallback به مدل پشتیبان اشاره کن. '+BACK+' '+FB+'\n'),
44:('[کلیک ۱]\n',
 '▶ عملی: به مرورگر برو، مرحلهٔ ۶ دمو «trace و هزینهٔ guards». «اجرای سفارش ۱۰۴۲» را بزن و پنل trace را از بالا تا پایین نشان بده (تصمیم مدل، ابزار با scope=C001، اعتبارسنجی، راستی‌آزمایی). بعد «اندازه‌گیری guards (۱۵ اجرا)» را بزن و به جدول و سطر شرایط اندازه‌گیری زیر آن اشاره کن. اگر طول کشید، جدول همین اسلاید همان عددهاست. '+BACK+'\n'),
}
def set_notes(sl,text):
    tf=sl.notes_slide.notes_text_frame; tf.text=text
    for para in tf.paragraphs:
        pPr=para._p.get_or_add_pPr(); pPr.set('rtl','1'); pPr.set('algn','r')
        for r in para.runs:
            rPr=r._r.get_or_add_rPr(); rPr.set('lang','fa-IR')
            for t in ('a:latin','a:cs'):
                e=rPr.find(qn(t))
                if e is None: e=etree.SubElement(rPr,qn(t))
                e.set('typeface','AradFDVF')
for n,sl in enumerate(p.slides,28):
    t=sl.notes_slide.notes_text_frame.text
    t=t.replace('[اجرا] ','').replace(' [اجرا]','').replace('[اجرا]','')
    if n==28:
        h,b=t.split('\n',1); t=h+'\n'+SETUP+'\n'+b
    if n in D:
        key,blk=D[n]; assert key in t,(n,key); t=t.replace(key,key+blk,1)
    set_notes(sl,t)
p.save(str(_ROOT / 'slides' / 'part-03_v3.pptx'))
# verify
import zipfile
z=zipfile.ZipFile(str(_ROOT / 'slides' / 'part-03_v3.pptx')); bad=tot=0
for nm in z.namelist():
    if nm.startswith('ppt/notesSlides/notesSlide') and nm.endswith('.xml'):
        x=etree.fromstring(z.read(nm))
        ns={'a':'http://schemas.openxmlformats.org/drawingml/2006/main','p':'http://schemas.openxmlformats.org/presentationml/2006/main'}
        for sp in x.findall('.//p:sp',ns):
            ph=sp.find('.//p:nvPr/p:ph',ns)
            if ph is None or ph.get('type')!='body': continue
            for pp in sp.findall('.//a:p',ns):
                tot+=1; pr=pp.find('a:pPr',ns)
                if pr is None or pr.get('rtl')!='1' or pr.get('algn')!='r': bad+=1
print('notes paragraphs',tot,'non-RTL',bad)
print('demo blocks',sum(s.notes_slide.notes_text_frame.text.count('▶') for s in p.slides))
