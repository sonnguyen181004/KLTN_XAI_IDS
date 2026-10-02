from pathlib import Path
import csv
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'RQ2_LIME_FI' / 'report_charts'
OUT.mkdir(parents=True, exist_ok=True)

# Hinh 1: Agreement@k tu CSV macro da chay
src = ROOT / 'RQ2_LIME_FI' / 'rq2_agreement' / '20260929_075049_171393' / 'summary_macro.csv'
with open(src, encoding='utf-8-sig', newline='') as f:
    r = next(csv.DictReader(f))
ks = [3, 5, 10]
j = [float(r[f'jaccard_{k}_macro_mean_of_class_means']) for k in ks]
s = [float(r[f'spearman_{k}_macro_mean_of_class_means']) for k in ks]
a = [float(r[f'signed_agreement_{k}_macro_mean_of_class_means']) for k in ks]

try:
    font_title=ImageFont.truetype('arialbd.ttf',30); font=ImageFont.truetype('arial.ttf',21); small=ImageFont.truetype('arial.ttf',17)
except:
    font_title=font=small=ImageFont.load_default()
w,h=1500,820; left,right,top,bottom=135,70,135,125; chart_h=h-top-bottom
img=Image.new('RGB',(w,h),'white'); draw=ImageDraw.Draw(img)
draw.text((left,30),'Độ tương đồng SHAP và LIME trên cohort 1.339 flow',fill='black',font=font_title)
for tick in range(0,11,2):
    y=top+chart_h-(tick/10)*chart_h; draw.line((left,y,w-right,y),fill='#DDDDDD',width=1)
    draw.text((35,y-10),f'{tick/10:.1f}',fill='black',font=small)
draw.line((left,top,left,h-bottom),fill='black',width=3); draw.line((left,h-bottom,w-right,h-bottom),fill='black',width=3)
series=[('Jaccard',j,'#235789'),('Spearman',s,'#E27D3A'),('Signed agreement',a,'#4C9F70')]
centers=[390,780,1170]; bw=78
for gi,cx in enumerate(centers):
    for si,(name,vals,color) in enumerate(series):
        val=vals[gi]; x=cx+(si-1)*(bw+12); y=top+chart_h-val*chart_h
        draw.rectangle((x,y,x+bw,h-bottom),fill=color)
        draw.text((x+2,y-28),f'{val:.3f}',fill='black',font=small)
    draw.text((cx-55,h-bottom+28),f'Top {ks[gi]}',fill='black',font=font)
for i,(name,_,color) in enumerate(series):
    x=360+i*280; draw.rectangle((x,88,x+25,112),fill=color); draw.text((x+35,88),name,fill='black',font=small)
draw.text((18,370),'Macro',fill='black',font=small)
img.save(OUT/'agreement_shap_lime.png')

# Hinh 2: panel 4 bieu do Top 5 SHAP global da ton tai
base = ROOT / 'RQ2_SHAP' / 'shap_top5_each_attack' / 'top5_each_attack' / '20260925_030724_702031'
items = [
    ('SSH Bruteforce', base/'SSH-Bruteforce'/'top5_positive.png'),
    ('DDoS LOIC UDP', base/'DDOS_attack-LOIC-UDP'/'top5_positive.png'),
    ('DoS Slowloris', base/'DoS_attacks-Slowloris'/'top5_positive.png'),
    ('SQL Injection', base/'SQL_Injection'/'top5_positive.png'),
]
imgs=[]
for label,path in items:
    im=Image.open(path).convert('RGB')
    im.thumbnail((760,460))
    imgs.append((label,im.copy()))
cell_w, cell_h = 800, 520
canvas=Image.new('RGB',(cell_w*2,cell_h*2+65),'white')
draw=ImageDraw.Draw(canvas)
try: font=ImageFont.truetype('arial.ttf',25)
except: font=ImageFont.load_default()
for idx,(label,im) in enumerate(imgs):
    col, row = idx%2, idx//2
    x0,y0=col*cell_w,row*cell_h+65
    draw.text((x0+18,y0+12),label,fill='black',font=font)
    px=x0+(cell_w-im.width)//2; py=y0+52+(cell_h-52-im.height)//2
    canvas.paste(im,(px,py))
draw.text((25,18),'SHAP global Top 5 feature theo 4 lớp đại diện',fill='black',font=font)
canvas.save(OUT/'shap_global_top5_four_representative_classes.png')
print(OUT/'agreement_shap_lime.png')
print(OUT/'shap_global_top5_four_representative_classes.png')
