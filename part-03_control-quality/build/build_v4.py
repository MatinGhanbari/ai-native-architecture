# v4: remove in-slide citation markers and figure source captions; References slides (46-47) kept.
import re
from pptx import Presentation
from pathlib import Path
from pptx.oxml.ns import qn
_ROOT = Path(__file__).resolve().parents[1]
p=Presentation(str(_ROOT / 'slides' / 'archive' / 'part-03_v3.pptx'))
CIT=re.compile(r'\s*\[(?:\d+|[۰-۹]+)(?:\]\s*\[(?:\d+|[۰-۹]+))*\]')
CAP=re.compile(r'^\s*\u200f?(شکل|الگوی .*شکل از|منبع)')
removed=0; deleted=0; log=[]
def clean_tf(tf):
    global removed
    for para in tf.paragraphs:
        for r in para.runs:
            n=len(CIT.findall(r.text))
            if n:
                removed+=n
                t=CIT.sub('',r.text)
                t=re.sub(r'\s+([:؛،.])',r'\1',t)
                r.text=t
for n,sl in enumerate(p.slides,28):
    if n>=46: continue
    for sh in list(sl.shapes):
        if sh.has_text_frame:
            txt=sh.text_frame.text
            KEEP={'الگوی plan-then-execute':'الگوی plan-then-execute','کد ML فقط':'کد ML فقط جعبهٔ کوچک وسط است'}
            k=[v for kk,v in KEEP.items() if kk in txt]
            if CAP.search(txt) and len(txt)<120 and k:
                removed+=len(CIT.findall(txt)); runs=sh.text_frame.paragraphs[0].runs
                runs[0].text=('\u200f' if not k[0][0]>'\u0600' else '')+k[0]
                for r in runs[1:]: r.text=''
                log.append((n,'caption->desc',txt)); continue
            if CAP.search(txt) and len(txt)<120:
                removed+=max(1,len(CIT.findall(txt)))
                sid=str(sh.shape_id); sh._element.getparent().remove(sh._element); deleted+=1
                log.append((n,'caption',txt))
                tm=sl._element.find(qn('p:timing'))
                if tm is not None:
                    for tgt in tm.iter(qn('p:spTgt')):
                        if tgt.get('spid')==sid:
                            par=tgt
                            while par is not None and not (par.tag==qn('p:par') and par.find(qn('p:cTn')).get('presetClass')):
                                par=par.getparent()
                            # if this was the click leader, promote next sibling
                            ctn=par.find(qn('p:cTn'))
                            parent=par.getparent()
                            if ctn.get('nodeType')=='clickEffect':
                                sibs=[x for x in parent if x is not par]
                                if sibs: sibs[0].find(qn('p:cTn')).set('nodeType','clickEffect')
                            parent.remove(par)
                            break
                continue
            before=removed; clean_tf(sh.text_frame)
            if removed>before: log.append((n,'inline',sh.text_frame.text[:60]))
            if removed>before and not sh.text_frame.text.strip():
                sh._element.getparent().remove(sh._element); deleted+=1
        if sh.has_table:
            for row in sh.table.rows:
                for c in row.cells: clean_tf(c.text_frame)
# leftover check
left=[]
for n,sl in enumerate(p.slides,28):
    if n>=46: continue
    for sh in sl.shapes:
        t=sh.text_frame.text if sh.has_text_frame else ''
        if sh.has_table: t=' '.join(c.text for r in sh.table.rows for c in r.cells)
        if CIT.search(t) or re.search(r'شکل از|منبع:',t): left.append((n,t[:60]))
p.save(str(_ROOT / 'slides' / 'part-03_v4.pptx'))
for l in log: print(l)
print('markers removed',removed,'shapes deleted',deleted,'leftover',left)
