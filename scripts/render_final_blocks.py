"""Run with KLayout -z -r, Qt offscreen; render actual GUI layout and markers."""
import json
from pathlib import Path
import pya

root=Path('/work');out=root/capture_dir
data=json.loads((out/'regions.json').read_text())
app=pya.Application.instance()
view=pya.LayoutView()
view.load_layout(str(root/data['gds']),0)
view.load_layer_props(str(root/'.pdk/gf180mcuD/libs.tech/klayout/tech/gf180mcu.lyp'))
view.max_hier()
view.set_config('background-color','#ffffff')
view.set_config('text-visible','false')
view.set_config('grid-visible','false')
view.set_config('show-cell-boxes','false')
for layer in view.each_layer():
    layer.visible = layer.source_layer in [34,36,42] and layer.source_datatype == 0
    layer.fill_color=0xc6cbd0;layer.frame_color=0xc6cbd0
colors=data.get('colors',{'rf':0x1766c5,'alu':0xd64e0a,'counter':0x00805a})
labels=data.get('labels',{'rf':'RF: celdas con jerarquia u_rf','alu':'ALU: celdas con jerarquia u_alu','counter':'Contador: 32 flip-flops cycles_q'})
markers=[]
def mark(box,color):
    m=pya.Marker(view);m.set(pya.DBox(*box));m.color=color;m.frame_color=color;m.line_width=2
    markers.append(m)
def label(text,x,y,color,size):
    d=pya.DText(text,pya.DTrans(x,y));d.size=size
    m=pya.Marker(view);m.set(d);m.color=color;m.frame_color=color;m.text_frame_enabled=False
    markers.append(m)
die=data.get('capture_bbox_um',data['die_bbox_um']);w=die[2]-die[0];pad=w*.06
target=pya.DBox(die[0]-pad,die[1]-pad,die[2]+pad,die[3]+w*.22)
for group in data.get('capture_groups',['overview','rf','alu','counter']):
    for m in markers:m._destroy()
    markers=[]
    selected=data.get('overview_groups',list(colors)) if group=='overview' else [group]
    for g in selected:
        for item in data['regions'][g]:mark(item['bbox_um'],colors[g])
    label(data['run'],die[0],die[3]+w*.16,0x253344,w*.018)
    for i,g in enumerate(selected):
        label(labels[g]+f" ({len(data['regions'][g])})",die[0],die[3]+w*(.11-.035*i),colors[g],w*.017)
    if data.get('annotation_note'):
        label(data['annotation_note'],die[0],die[3]+w*.025,0x754b00,w*.015)
    scale=50 if w<300 else 100
    edge=pya.Marker(view);edge.set(pya.DEdge(die[0],die[1]-pad*.6,die[0]+scale,die[1]-pad*.6));edge.color=0x253344;edge.line_width=3;markers.append(edge)
    label(f'{scale} um',die[0],die[1]-pad*.3,0x253344,w*.015)
    view.zoom_box(target)
    view.save_image_with_options(str(out/(group+'.png')),1600,1600,0,1,2,target,False)
view.save_layer_props(str(out/'capture.lyp'))
(out/'renderer.json').write_text(json.dumps(dict(renderer='KLayout LayoutView GUI with offscreen Qt platform',version=app.version(),macro=str(Path(__file__).resolve().relative_to(root)),source_gds_unchanged=True),indent=2)+'\n')
app.exit(0)
