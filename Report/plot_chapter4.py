"""Scientific figures from rechecked project results, not illustrative data."""
from pathlib import Path
import json
import numpy as np,pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
R=Path(__file__).resolve().parent; A=R/'chapter4_assets'
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False,'savefig.dpi':180})
def save(fig,name):
    fig.tight_layout(); fig.savefig(A/name,bbox_inches='tight',facecolor='white');plt.close(fig)
c=pd.read_csv(A/'class_counts.csv',index_col=0).sort_values('test')
fig,ax=plt.subplots(figsize=(9,4.6));y=np.arange(len(c));ax.barh(y-.18,c.train,.35,label='Train',color='#22577a');ax.barh(y+.18,c.test,.35,label='Test',color='#38a3a5');ax.set_yticks(y,c.index);ax.set_xscale('log');ax.set_xlabel('Số flow (thang logarit)');ax.legend();save(fig,'class_distribution.png')
cm=pd.read_csv(A/'confusion_matrix.csv',index_col=0); norm=cm.to_numpy()/cm.sum(axis=1).to_numpy()[:,None]
fig,ax=plt.subplots(figsize=(10,7));im=ax.imshow(norm,vmin=0,vmax=1,cmap='Blues');ax.set_xticks(range(15),cm.columns,rotation=65,ha='right',fontsize=8);ax.set_yticks(range(15),cm.index,fontsize=8)
for i in range(15):
    for j in range(15):
        if norm[i,j]>=.01: ax.text(j,i,f'{norm[i,j]*100:.1f}',ha='center',va='center',fontsize=7,color='white' if norm[i,j]>.5 else 'black')
ax.set_ylabel('Nhãn thật');ax.set_xlabel('Nhãn dự đoán');fig.colorbar(im,ax=ax,label='Tỷ lệ theo hàng',shrink=.7);save(fig,'confusion_matrix.png')
lr=pd.read_csv(A/'lime_rerun.csv'); v=json.loads((A/'verification.json').read_text(encoding='utf-8'))
fig,axs=plt.subplots(1,2,figsize=(9,3.1));axs[0].hist(lr.local_r2,bins=24,color='#22577a',edgecolor='white');axs[0].axvline(.3,color='#b23a48',ls='--',label='Ngưỡng 0,3');axs[0].set(xlabel='R² cục bộ của LIME',ylabel='Số flow');axs[0].legend(fontsize=8)
a=v['rq2']['agreement_reaggregated'];axs[1].bar(list(a),list(a.values()),color='#38a3a5');axs[1].set(xlabel='Số đặc trưng top-k',ylabel='Jaccard trung bình',ylim=(0,.32))
for i,z in enumerate(a.values()):axs[1].text(i,z+.007,f'{z:.3f}',ha='center',fontsize=9)
save(fig,'lime_agreement.png')
f=pd.read_csv(A/'faithfulness_rerun.csv');fig,ax=plt.subplots(figsize=(8,3.1));bases=list(f.baseline.unique());pos=np.arange(3)
for j,(m,col) in enumerate([('SHAP','#22577a'),('LIME','#38a3a5'),('Random','#a5acaf')]):
    vals=f[f.method==m].set_index('baseline').loc[bases,'comprehensiveness_auc'];ax.bar(pos+(j-1)*.24,vals,.24,label=m,color=col)
ax.set_xticks(pos,['Trung vị train','Trung bình train','Trung vị Benign']);ax.set_ylabel('Mức giảm xác suất trung bình');ax.set_ylim(0,1);ax.legend(ncols=3);save(fig,'faithfulness.png')
live=pd.read_csv(A/'live_historical_timeline.csv');fig,axs=plt.subplots(2,1,figsize=(9,4.3),sharex=True)
axs[0].plot(live.elapsed_seconds/60,live.api_flows,color='#22577a');axs[0].set_ylabel('Flow API đã nhận')
for p,label,col in [('api','API','#22577a'),('capture','Capture','#b23a48'),('feeder','Feeder','#38a3a5')]:axs[1].plot(live.elapsed_seconds/60,live[p+'_rss_mib'],label=label,color=col)
axs[1].set(xlabel='Thời gian đã chạy (phút)',ylabel='RSS quan sát (MiB)');axs[1].legend(ncols=3);save(fig,'live_timeline.png')
p=json.loads((A/'pcap_recheck.json').read_text(encoding='utf-8'));case=next(r for r in p['runs'] if r['file']=='tesst2.pcapng')['candidate']['alert_xai'][0]
fig,ax=plt.subplots(figsize=(8,3));items=sorted(case['shap_top5'],key=lambda a:a['phi']);ax.barh([x['feature'] for x in items],[x['phi'] for x in items],color=['#b23a48' if x['phi']>0 else '#38a3a5' for x in items]);ax.axvline(0,color='gray',lw=.8);ax.set_xlabel('Đóng góp SHAP vào điểm thô của lớp Hulk');save(fig,'pcap_shap.png')
print('Saved 6 verified-data figures')
