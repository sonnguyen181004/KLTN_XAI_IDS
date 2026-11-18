from pathlib import Path
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
H=Path(__file__).resolve().parent;A=H/'output/report_assets'
P=json.loads((H/'attack_load_audit_20261118.json').read_text(encoding='utf-8'))['pcaps']
fig,axs=plt.subplots(1,2,figsize=(9,3.5))
for ax,title,vals,ylabel in [(axs[0],'Tải HTTP',[P[k]['http_requests_per_capture_second'] for k in ['dos_oldeney','oldeneye2','hulk-go','hulk2']],'Request/s'),(axs[1],'Slowloris',[10,20],'Kết nối TCP')]:
    labs=['GoldenEye 1','GoldenEye 2','Hulk-Go 1','Hulk-Go 2'] if len(vals)==4 else ['Mức 1','Mức 2']
    bars=ax.bar(labs,vals,color=['#cccccc','#555555']*(len(vals)//2),edgecolor='black');ax.set_title(title);ax.set_ylabel(ylabel);ax.tick_params(axis='x',rotation=20)
    for b,v in zip(bars,vals):ax.text(b.get_x()+b.get_width()/2,v,f'{v:.1f}',ha='center',va='bottom',fontsize=8)
    ax.set_ylim(0,max(vals)*1.2)
fig.tight_layout();fig.savefig(A/'load_chart.png',dpi=190);plt.close(fig)
