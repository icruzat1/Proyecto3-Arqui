import json
from pathlib import Path
import pya
root=Path('/work'); out=Path('/out')
tags={'A':'stage13_final_traceable_a','B':'stage12_electrical_route_b'}
colors={'memory':0xB19CD9,'rf':0x1565C0,'alu':0xE66100,'decode':0xCB218E,'fetch':0x37A7B8,'load_store':0xA67B00,'control':0x333333,'peripherals':0x999999,'spi':0xE6AA00,'reset':0xFF5252,'buttons':0x76512D,'counter':0x00875A}
app=pya.Application.instance()
for variant,tag in tags.items():
 d=json.loads((root/'evidence/layout_captures'/(tag+'_blocks')/'regions.json').read_text())
 v=pya.LayoutView();v.load_layout(str(root/d['gds']),0)
 v.load_layer_props(str(root/'.pdk/gf180mcuD/libs.tech/klayout/tech/gf180mcu.lyp'));v.max_hier()
 v.set_config('background-color','#ffffff');v.set_config('text-visible','false');v.set_config('grid-visible','false');v.set_config('show-cell-boxes','false')
 die=d['die_bbox_um']; pad=(die[2]-die[0])*.015
 box=pya.DBox(die[0]-pad,die[1]-pad,die[2]+pad,die[3]+pad)
 for layer in v.each_layer():
  layer.visible=layer.source_datatype==0 and layer.source_layer in [34,36,42,46,49,50,51,53,54,56,57,58,59,60,61,62,63,64,65,66,81]
 v.zoom_box(box); v.save_image_with_options(str(out/(variant+'_complete.png')),1400,1400,0,1,2,box,False)
 for layer in v.each_layer():
  layer.visible=layer.source_layer in [34,36,42] and layer.source_datatype==0
  layer.fill_color=0xE1E4E7;layer.frame_color=0xE1E4E7
 marks=[]
 for group,color in colors.items():
  for item in d['regions'][group]:
   m=pya.Marker(v);m.set(pya.DBox(*item['bbox_um']));m.color=color;m.frame_color=color;m.line_width=2; marks.append(m)
 v.save_image_with_options(str(out/(variant+'_blocks.png')),1400,1400,0,1,2,box,False)
 for m in marks:m._destroy()
 v._destroy()
app.exit(0)
