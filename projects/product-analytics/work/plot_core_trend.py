import json
import math
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent/'plotting-deps'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties, fontManager

root=Path(__file__).resolve().parent.parent
data=json.loads((root/'work/daily_trend.json').read_text())
font_path=Path('/System/Library/Fonts/Hiragino Sans GB.ttc')
assert font_path.exists()
fontManager.addfont(str(font_path))
font=FontProperties(fname=str(font_path))
plt.rcParams.update({'font.family':font.get_name(),'axes.unicode_minus':False,'font.size':10,'savefig.facecolor':'white'})
dates=sorted({r['date'] for r in data['records']})
assert len(dates)==7
codes=['YX9354001','YX9615001']
names=['月光舞裙','好运相随']
colors=['#216F91','#B45B2B']
metrics=[('uv','商详访客 UV','人'),('orders','支付订单数','单'),('favorites','收藏用户数','人')]
series={c:{r['date']:r for r in data['records'] if r['code']==c} for c in codes}
fig,axes=plt.subplots(3,2,figsize=(14,10.2),dpi=170)
fig.subplots_adjust(left=.065,right=.975,top=.82,bottom=.09,hspace=.48,wspace=.16)
fig.text(.065,.965,'得物商品｜近7天每日趋势',fontproperties=font,fontsize=23,color='#17384A',weight='bold')
fig.text(.065,.925,'2026年10月2日—10月8日  ·  一级类目：流行饰品/眼镜/服配',fontproperties=font,fontsize=12,color='#566F7D')
fig.text(.065,.892,'同一指标左右共用刻度；每个点都标明当天数值。',fontproperties=font,fontsize=10.5,color='#566F7D')
for j,(code,name,color) in enumerate(zip(codes,names,colors)):
    axes[0,j].text(0,1.27,f'{name}  {code}',transform=axes[0,j].transAxes,fontproperties=font,fontsize=14,color=color,weight='bold')
for i,(key,label,unit) in enumerate(metrics):
    values_all=[series[c][d][key] for c in codes for d in dates]
    assert all(isinstance(v,(int,float)) for v in values_all)
    peak=max(values_all)
    if key=='orders':
        max_y=max(2,math.ceil(peak+1))
        ticks=list(range(max_y+1))
    elif key=='uv':
        max_y=max(100,math.ceil(peak*1.13/100)*100)
        ticks=list(range(0,max_y+1,200 if max_y>400 else 100))
    else:
        max_y=max(10,math.ceil(peak*1.15/10)*10)
        ticks=list(range(0,max_y+1,10))
    for j,(code,color) in enumerate(zip(codes,colors)):
        ax=axes[i,j]
        vals=[series[code][d][key] for d in dates]
        ax.plot(range(7),vals,color=color,linewidth=2.1,marker='o',markersize=5,zorder=3)
        for x,y in enumerate(vals):
            ax.annotate(str(y),xy=(x,y),xytext=(0,9),textcoords='offset points',ha='center',va='bottom',fontsize=11,color=color,weight='bold')
        ax.set_title(f'{label}（{unit}）',fontproperties=font,fontsize=12,loc='left',pad=14,color='#284A5B')
        ax.set_xticks(range(7),[d[5:].replace('-','/') for d in dates])
        ax.set_xlim(-.3,6.3)
        ax.set_ylim(0,max_y)
        ax.set_yticks(ticks)
        ax.set_axisbelow(True)
        ax.grid(axis='y',color='#E3EAF0',linewidth=.8)
        ax.tick_params(axis='both',colors='#627A88',length=0,pad=7,labelsize=10)
        for side in ['top','right','left']:
            ax.spines[side].set_visible(False)
        ax.spines['bottom'].set_color('#D6E0E8')
fig.text(.065,.038,'数据：得物商品分析逐日主值。单量为支付订单数；收藏为当日收藏用户数。46款×7天共322条，缺失0条。',fontproperties=font,fontsize=9.3,color='#627A88')
fig.savefig(root/'work/core_daily_chart.png',dpi=170)
print(root/'work/core_daily_chart.png')
