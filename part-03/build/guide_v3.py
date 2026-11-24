import re
from pathlib import Path
from pptx import Presentation
from docx import Document
from docx.shared import Pt, RGBColor, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
_ROOT = Path(__file__).resolve().parents[1]
M = str(_ROOT)
FONT='AradFDVF'
p=Presentation(str(_ROOT / 'slides' / 'part-03_v3.pptx'))
d=Document()
for s in d.sections: s.right_margin=s.left_margin=Cm(2); s.top_margin=s.bottom_margin=Cm(1.8)
def rfont(run,size=None,bold=None,color=None):
    rPr=run._r.get_or_add_rPr()
    f=rPr.find(qn('w:rFonts'))
    if f is None: f=OxmlElement('w:rFonts'); rPr.append(f)
    for k in ('w:ascii','w:hAnsi','w:cs','w:eastAsia'): f.set(qn(k),FONT)
    rtl=OxmlElement('w:rtl'); rPr.append(rtl)
    if size: run.font.size=Pt(size); 
    cs=OxmlElement('w:szCs'); cs.set(qn('w:val'),str(int((size or 11)*2))); rPr.append(cs)
    if bold: run.bold=True; b=OxmlElement('w:bCs'); rPr.append(b)
    if color: run.font.color.rgb=color
def para(text='',size=11,bold=False,color=None,style=None,space=4):
    pp=d.add_paragraph(style=style) if style else d.add_paragraph()
    pPr=pp._p.get_or_add_pPr(); b=OxmlElement('w:bidi'); pPr.insert(0,b)
    pp.alignment=WD_ALIGN_PARAGRAPH.RIGHT; pp.paragraph_format.space_after=Pt(space)
    if text:
        r=pp.add_run(text); rfont(r,size,bold,color)
    return pp
TEAL=RGBColor(0,0x60,0x80)
def h(text,lvl=1): para(text,16 if lvl==1 else 13,True,TEAL,space=6)
def bullet(text): para('• '+text,11)
def table(rows,widths):
    t=d.add_table(rows=len(rows),cols=len(rows[0])); t.style='Table Grid'
    tblPr=t._tbl.tblPr; bv=OxmlElement('w:bidiVisual'); tblPr.append(bv)
    for i,row in enumerate(rows):
        for j,v in enumerate(row):
            c=t.cell(i,j); c.width=Cm(widths[j]); c.text=''
            pp=c.paragraphs[0]; pPr=pp._p.get_or_add_pPr(); pPr.insert(0,OxmlElement('w:bidi')); pp.alignment=WD_ALIGN_PARAGRAPH.RIGHT
            r=pp.add_run(v); rfont(r,9.5,i==0)
    d.add_paragraph()
# default font
st=d.styles['Normal']; rpr=st.element.get_or_add_rPr(); f=OxmlElement('w:rFonts')
for k in ('w:ascii','w:hAnsi','w:cs','w:eastAsia'): f.set(qn(k),FONT)
rpr.append(f)

para('راهنمای ارائهٔ بخش ۳: کنترل، کیفیت، امنیت و تکامل',18,True,TEAL)
para('ارائه‌دهنده: متین قنبری · ۲۰ دقیقه (۱۲ دقیقه اسلاید + ۸ دقیقه عملی) · فایل: part-03_v3.pptx (اسلایدهای ۲۸ تا ۴۷) · دمو: demo_v4',10.5,color=RGBColor(0x55,0x5B,0x63))
para('یادداشت شخصی است و نباید در git قرار بگیرد.',10,color=RGBColor(0xB0,0x2A,0x2A))

h('۱. چک‌لیست پیش از ارائه')
for x in ['Python 3.9+ روی لپ‌تاپ؛ در پوشهٔ demo_v4 در PowerShell: python run_ui.py ← مرورگر روی http://127.0.0.1:8765 باز می‌شود.',
 'سوییچ بالای رابط روی «آفلاین» (خروجی قطعی، بدون اینترنت و کلید API).',
 'یک بار دکمهٔ reset (حافظهٔ نشست و صف تأیید؛ با هر اجرای run_ui.py هم خودکار خالی می‌شود).',
 'همهٔ مرحله‌ها (۱ تا ۶) را یک بار اجرا کن تا ui_cache تازه شود و پشتیبان precomputed آماده باشد.',
 'بزرگ‌نمایی مرورگر برای پروژکتور؛ مرورگر روی مرحلهٔ ۱؛ جابه‌جایی با Alt+Tab.',
 'اگر درگاه اشغال بود: $env:UI_PORT="8800"; python run_ui.py',
 'فونت AradFDVF روی همان لپ‌تاپ نصب باشد؛ یک بار PowerPoint را در Slide Show باز کن و فونت، راست‌به‌چپ و انیمیشن‌ها را چک کن.',
 'PowerPoint در Presenter View تا یادداشت‌ها (با بلوک‌های ▶ عملی) جلوی چشمت باشد.',
 'پشتیبان CLI در صورت خرابی رابط: python run.py --poisoned-kb --no-guards --customer C001 "آیا ارسال بین‌المللی دارید؟"']: bullet(x)

h('۲. اسلاید به اسلاید')
rows=[['اسلاید','عنوان','زمان','پیام کوتاه','اقدام عملی']]
MSG={28:'معرفی و «با یک حمله شروع می‌کنم»',29:'سند بازیابی‌شده دستور پنهان دارد؛ داده نشت می‌کند',30:'سه قابلیت هم‌زمان = نشت؛ نمونه‌های واقعی',31:'حداکثر دو از سه؛ هر سه ← انسان در حلقه',32:'داده و دستور کانال جدا ندارند؛ LLM01',33:'scope از نشست، نه از مدل؛ plan-then-execute، Dual LLM، allowlist',34:'سناریو = نیازمندی؛ تاکتیک = راه؛ آزمون محدود ≠ اثبات',35:'۷۷٪ در برابر ۸۴٪؛ مصالحه به سبک ATAM',36:'فیلتر تزریق غیرمستقیم را نمی‌گیرد؛ ساختار می‌گیرد',37:'CACE؛ eval = fitness function',38:'آفلاین پیش از انتشار، آنلاین پس از آن',39:'judge هم کالیبره می‌شود؛ امنیت با assertion قطعی',40:'۱۴/۱۴ ← ۱۰/۱۴؛ نتیجه‌ها از پیش آماده',41:'state machine و چهار بودجه؛ سقف ← انسان',42:'timeout، retry، breaker، fallback',43:'توقف در گام ۶؛ پاسخ با مدل پشتیبان',44:'guard کامل کندتر ولی ارزان‌تر؛ باید اندازه گرفت',45:'تصمیم ← ویژگی کیفی ← هزینهٔ اندازه‌گیری‌شده',46:'منابع',47:'منابع و پرسش'}
ACT={29:'مرحلهٔ ۱: «اجرا (guards خاموش)»؛ اشاره به لینک sync و list_all_orders',36:'مرحلهٔ ۲: «اجرا» در سه ستون؛ output_filter pass و egress_allowlist blocked',40:'مرحلهٔ ۳: support-v3 «اجرای eval»، سپس support-v4؛ پشتیبان «نتیجهٔ از پیش آماده»',43:'مرحلهٔ ۴: «اجرای حلقهٔ runaway»؛ مرحلهٔ ۵: «اجرا» با تیک «مدل اصلی قطع است»',44:'مرحلهٔ ۶: «اجرای سفارش ۱۰۴۲»، سپس «اندازه‌گیری guards (۱۵ اجرا)»'}
for n,s in enumerate(p.slides,28):
    t=s.notes_slide.notes_text_frame.text.split('\n')[0]
    m=re.search(r'این صفحه ([۰-۹]+:[۰-۹]+)',t); tm=m.group(1) if m else ''
    title=[x.text_frame.text.strip('\u200f') for x in s.shapes if x.name=='TextBox 90']
    title=title[0] if title else 'عنوان بخش ۳'
    rows.append([str(n).translate(str.maketrans('0123456789','۰۱۲۳۴۵۶۷۸۹')),title,tm+(' (عملی)' if 'عملی —' in t else ''),MSG.get(n,''),ACT.get(n,'—')])
table(rows,[1.3,4.2,1.8,5,5])
para('جمع زمان: ۲۰:۰۰ — اسلایدها ۱۲:۰۰ و عملی ۸:۰۰ (شروع عملی ۱:۳۰ + ۲:۰۰ + ۱:۳۰ + ۱:۳۰ + ۱:۳۰). متن کامل گفتار در یادداشت‌های هر اسلاید است.',10)

h('۳. اقدام‌های دقیق دمو')
for x in [('مرحلهٔ ۱ (اسلاید ۲۹)','به کامنت پنهان قرمز در سند اشاره کن ← «اجرا (guards خاموش)» ← در پاسخ لینک تصویر sync.pakhsh-hamkar و نام علی رضایی و مریم کریمی؛ در trace فراخوانی list_all_orders.'),
 ('مرحلهٔ ۲ (اسلاید ۳۶)','«اجرا» در ستون‌های «بدون دفاع»، «فقط فیلتر»، «دفاع ساختاری». ستون دوم: نشت + output_filter result=pass. ستون سوم: قرنطینهٔ سند و egress_allowlist blocked.'),
 ('مرحلهٔ ۳ (اسلاید ۴۰)','support-v3 ← «اجرای eval» (۱۴/۱۴، CI passed) ← support-v4 ← «اجرای eval» (۱۰/۱۴، CI blocked)؛ چهار ردیف قرمز آیین‌نامه. صریح بگو نتیجه‌ها با mock قطعی از پیش گرفته شده‌اند.'),
 ('مرحلهٔ ۴ (اسلاید ۴۳)','«اجرای حلقهٔ runaway» ← نوار بودجهٔ گام تا STOPPED_BUDGET، ارجاع به انسان.'),
 ('مرحلهٔ ۵ (اسلاید ۴۳)','تیک «مدل اصلی قطع است» از قبل زده است ← «اجرا» ← timeout، retry، circuit breaker، fallback به مدل پشتیبان.'),
 ('مرحلهٔ ۶ (اسلاید ۴۴)','«اجرای سفارش ۱۰۴۲» ← trace کامل ← «اندازه‌گیری guards (۱۵ اجرا)» ← جدول و سطر شرایط زیر آن.')]:
    pp=para(); r=pp.add_run(x[0]+': '); rfont(r,11,True); r=pp.add_run(x[1]); rfont(r,11)

h('۴. اگر دمو خراب شد')
for x in ['اگر یک اجرای زنده خطا بدهد، رابط خودکار آخرین نتیجهٔ موفق را با برچسب «نتیجهٔ از پیش آماده (precomputed)» نشان می‌دهد؛ همین را بگو و ادامه بده.',
 'در مرحلهٔ ۳ دکمهٔ «نتیجهٔ از پیش آماده» را مستقیم بزن.',
 'اگر مرورگر یا سرور بالا نیامد: اسلایدهای عملی تصویر و خروجی واقعی همان مرحله را دارند؛ با آن‌ها توضیح بده و زمان را حفظ کن.',
 'پشتیبان CLI در پوشهٔ demo_v4: python run.py --poisoned-kb --filters-only --customer C001 "…" و python evals/run_evals.py',
 'سر کلاس سراغ حالت «مدل واقعی» نرو؛ تست نشده و به اینترنت و کلید وابسته است.']: bullet(x)

h('۵. پرسش‌های محتمل استاد و پاسخ کوتاه')
QA=[('فرق این تاکتیک‌ها با تاکتیک‌های کلاسیک Bass چیست؟','بیشترشان همان detect / resist / recover کلاسیک‌اند [1]. تازگی در محرک‌هاست: ورودی زبانی و خروجی غیرقطعی؛ برای همین معیار پاسخ آماری می‌شود (نرخ قبولی، نرخ نشت).'),
 ('اگر خروجی قطعی نیست، fitness function چطور قطعی است؟','خود آزمون قطعی است: آستانه روی نرخ قبولی تعریف می‌شود، مثل آزمون عملکرد روی p95 تأخیر [10]. آزمون کنترل دسترسی هم قبول/رد است.'),
 ('LLM-as-judge خودش غیرقابل‌اعتماد نیست؟','چرا؛ سوگیری position و verbosity دارد [11]. judge نسخه‌بندی و با برچسب انسانی کالیبره می‌شود [24] و موارد امنیتی با assertion قطعی سنجیده می‌شوند.'),
 ('چرا prompt injection مثل SQL injection با escape حل نمی‌شود؟','در LLM کانال جدایی برای داده و دستور نیست [13]. راه‌حل ساختاری است: جداکردن جریان کنترل از داده (CaMeL [19]) یا محدودکردن ترکیب قابلیت‌ها (Rule of Two [22]).'),
 ('هزینهٔ این لایه‌ها چقدر است و کی ارزشش را دارد؟','در دمو اندازه گرفتیم: guard کامل ۵۴ میلی‌ثانیه کندتر ولی کمی ارزان‌تر (mock آفلاین). در ادبیات، CaMeL حدود ۷ واحد درصد utility می‌دهد [19]. تصمیم با سناریوی کیفی و اولویت ذی‌نفعان گرفته می‌شود.'),
 ('این ATAM است؟','نه؛ فقط بحث tradeoff point به سبک ATAM [21] است، نه اجرای کامل روش با ذی‌نفعان و utility tree.'),
 ('قبولی ۱۴/۱۴ یعنی سیستم امن است؟','نه؛ فقط دربارهٔ همان موارد آزموده‌شده است. مجموعه باید با حمله‌های تازه رشد کند (مثل AgentDojo [23]).')]
for q,a in QA:
    para('پرسش: '+q,11,True); para('پاسخ: '+a,11,space=8)

h('۶. عددهای کلیدی و منبع')
rows=[['عدد','معنا','منبع'],
 ['۷۷٪ در برابر ۸۴٪','کارهای حل‌شدهٔ CaMeL با امنیت قابل اثبات در برابر سیستم بی‌دفاع، AgentDojo','[19] (preprint)، [23]'],
 ['بیش از ۸۰٪','توافق داور GPT-4 با ترجیح انسانی، هم‌سطح توافق دو انسان','[11]'],
 ['LLM01','رتبهٔ Prompt Injection در OWASP Top 10 for LLM 2025','[12]'],
 ['LLM10','Unbounded Consumption؛ کنترلش بودجهٔ Controller','[12]'],
 ['۲ از ۳','Agents Rule of Two (Meta، اکتبر ۲۰۲۵)','[22]'],
 ['۱۴/۱۴ ← ۱۰/۱۴','eval دمو با support-v3 و support-v4؛ چهار مورد آیین‌نامه رد','دموی خودمان، آفلاین'],
 ['۲۷۱ / ۲۷۱ / ۳۲۵ ms','تأخیر بدون guard / فقط فیلتر / کامل','دمو: MODE=offline، MOCK_LATENCY_MS=150، SEED=7'],
 ['۰٫۰۰۰۱۳۱ / ۰٫۰۰۰۱۳۱ / ۰٫۰۰۰۱۲۰ دلار','هزینهٔ برآوردی، میانگین سه پرسش، قیمت‌های فرضی','همان'],
 ['گام ۶، ۱۲ فراخوانی، ۱۳۷۳ ms','توقف runaway با بودجهٔ گام','اجرای CLI demo_v2، آفلاین'],
 ['حدود ۱٫۱ ثانیه','پاسخ در قطعی مدل اصلی با fallback','اجرای CLI demo_v2، آفلاین']]
table(rows,[4,8,5])
h('۷. نکته‌های دقت')
for x in ['عددهای دمو از mock آفلاین‌اند؛ همیشه بگو «در این شرایط اندازه‌گیری».',
 'نگو «هر guard هزینه اضافه می‌کند»؛ بگو «اثرش را باید اندازه گرفت».',
 'CaMeL و Beurer-Kellner هنوز preprint هستند.',
 'متن کامل کتاب‌های Bass و Ford در دسترس نبود؛ فقط تعریف‌های استاندارد آمده، بدون شمارهٔ صفحه.']: bullet(x)
d.save(str(_ROOT / 'private' / 'Guide_Part3_Matin_v3.docx'))
print('ok')
