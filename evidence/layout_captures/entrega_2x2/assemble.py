from PIL import Image, ImageDraw, ImageFont, ImageOps
from pathlib import Path
import hashlib,json
p=Path(__file__).resolve().parent
font='/System/Library/Fonts/Supplemental/Arial.ttf'
f=lambda n:ImageFont.truetype(font,n)
im=Image.new('RGB',(3000,3380),'white');d=ImageDraw.Draw(im)
d.text((60,25),'A y B   |   Vista física completa y bloques identificados',font=f(49),fill='#182635')
d.text((60,92),'Layouts finales a 10 MHz. Cada columna ajusta su escala para mostrar el diseño completo.',font=f(29),fill='#475564')
for col,(v,size) in enumerate([('A','0,553389 mm²'),('B','2,135480 mm²')]):
 x=50+col*1500
 d.text((x,150),f'{v}  ·  {size}',font=f(41),fill='#182635')
 for row,(suffix,label) in enumerate([('complete','Completo: celdas y conexiones metálicas'),('blocks','Sectores funcionales: metales ocultos')]):
  y=218+row*1480
  d.text((x,y),label,font=f(32),fill='#182635')
  img=Image.open(p/(v+'_'+suffix+'.png')).convert('RGB')
  im.paste(ImageOps.contain(img,(1400,1400)),(x,y+52))
items=[('Memoria','#B19CD9'),('RF','#1565C0'),('ALU','#E66100'),('Contador','#00875A'),('Decodificador','#CB218E'),('Fetch','#37A7B8'),('Load/store','#A67B00'),('Control','#333333'),('SPI','#E6AA00'),('Periféricos','#999999'),('Reset','#FF5252'),('Botones','#76512D')]
for i,(name,color) in enumerate(items):
 x=65+(i%6)*490;y=3180+(i//6)*65
 d.rectangle((x,y,x+28,y+28),fill=color);d.text((x+40,y-5),name,font=f(29),fill='#182635')
d.text((65,3320),'Las marcas siguen las celdas reales; un bloque puede estar distribuido en varias zonas.',font=f(28),fill='#475564')
im.save(p/'Comparacion_AB_2x2.png')
(p/'manifest.json').write_text(json.dumps({'scope':'Visualization only, saved final GDS; no physical runs','files':{x.name:hashlib.sha256(x.read_bytes()).hexdigest() for x in p.glob('*.png')}},indent=2)+'\n')
