import json,sys
def fmt(v):
    a,_,b=v.partition('.'); return f'{int(a):,}'+('.'+b if b else '')
B='/mnt/project-files/zahlen-eval/testfaelle/'
import glob
cases=[c for f in sorted(glob.glob(B+'charge-*.json')) for c in json.load(open(f))]
import os
docs=sorted(os.listdir(B+'dokumente'))
out=['# Zahlen-Eval: Testfälle\n',f'Stand 18.10.2026, nach Review. {len(cases)} Testfälle, {len(docs)} Dokumente.\n',
'## Übersicht\n','| ID | Kategorie | Schwierigkeit | Musterlösung |','|---|---|---|---|']
for c in cases:
    m=c['musterloesung']; out.append(f"| {c['id']} | {c['kategorie']} | {c['schwierigkeit']} | {fmt(m['wert'])} {m['einheit']} |")
out.append('\n## Testfälle\n')
for c in cases:
    m=c['musterloesung']; d=c['dokument']
    out.append(f"<div class='case'>\n\n### {c['id']} · {c['kategorie']} · {c['schwierigkeit']}\n")
    out.append(f"**Dokument:** `{d['datei'].split('/')[-1]}`, Seite {d['seite']}\n")
    out.append(f"**Frage:**\n\n> {c['frage']}\n")
    ex='exakt' if m['exakt'] else f"gerundet auf {m['nachkommastellen']} Nachkommastellen"
    out.append(f"**Musterlösung:** **{fmt(m['wert'])} {m['einheit']}** ({ex})\n")
    out.append('**Verwendete Zahlen:**\n\n| Wert | Einheit | Bedeutung | Fundstelle |\n|---|---|---|---|')
    for z in c['verwendete_zahlen']: out.append(f"| {z['wert']} | {z['einheit']} | {z['bedeutung']} | {z['fundstelle']} |")
    out.append('\n**Rechenweg:**\n'); out+= [f"{i}. {s}" for i,s in enumerate(c['rechenweg'],1)]
    for k,t in (('pflicht_infos','Pflicht-Infos'),('fallen','Fallen')):
        if c.get(k): out.append(f'\n**{t}:**\n'); out+=[f"- {s}" for s in c[k]]
    out.append('\n</div>\n')
for i,f in enumerate(docs,1):
    t=f'Dokument {i}'
    txt=open(B+'dokumente/'+f).read().replace('\n# ','\n#### ').replace('\n## ','\n#### ').replace('\n### ','\n#### ')
    if txt.startswith('# '): txt='#### '+txt[2:]
    out.append(f"<div class='doc'>\n\n## {t}: {f}\n\n{txt}\n\n</div>\n")
open('charge01.md','w').write('\n'.join(out))
