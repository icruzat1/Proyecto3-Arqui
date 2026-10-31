#!/usr/bin/env python3
"""Render an auditable placement count map from two saved DEF files (stdlib only).

Color counts instance origins in equal physical bins, not occupied cell area.
Clock buffers/loads are recognized by buffer/inverter master AND CLOCK-net
connectivity, avoiding confusion with clock-buffer masters used on data nets.
"""
import argparse
from collections import Counter
import hashlib
from html import escape
import json
import math
from pathlib import Path
import re


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_variant(root, tag, variant):
    run = root/'config/gf180/runs'/f'{tag}_{variant}'
    candidates = sorted(run.glob('*-resizertimingpostcts/state_out.json'))
    if len(candidates) != 1:
        raise ValueError(f'Expected one postCTS repair state in {run}')
    state_path = candidates[0]
    state = json.loads(state_path.read_text())
    def_ref = state['def']
    if not def_ref.startswith('/work/'):
        raise ValueError(f'Unexpected DEF mount path: {def_ref}')
    def_path = root/def_ref.removeprefix('/work/')
    text = def_path.read_text()
    units = int(re.search(r'UNITS DISTANCE MICRONS (\d+)\s*;', text)[1])
    die_match = re.search(r'DIEAREA\s*\(\s*(-?\d+)\s+(-?\d+)\s*\)\s*\(\s*(-?\d+)\s+(-?\d+)\s*\)\s*;', text)
    if die_match is None:
        raise ValueError('Only rectangular DIEAREA is supported')
    die = [int(v)/units for v in die_match.groups()]
    core = list(map(float, state['metrics']['design__core__bbox'].split()))
    match = re.search(r'^COMPONENTS\s+(\d+)\s*;(.*?)^END COMPONENTS', text, re.M|re.S)
    records = re.findall(r'^\s*-\s+(.*?)\s*;', match[2], re.M|re.S)
    if len(records) != int(match[1]):
        raise ValueError('Component count does not match DEF header')
    instances = {}
    omitted = Counter()
    for record in records:
        name, master = record.split()[:2]
        position = re.search(r'\+\s+(PLACED|FIXED|COVER)\s+\(\s*(-?\d+)\s+(-?\d+)\s*\)\s+(\S+)', record)
        if position is None:
            raise ValueError(f'Unplaced component: {name}')
        x, y = int(position[2])/units, int(position[3])/units
        if not (die[0] <= x <= die[2] and die[1] <= y <= die[3]):
            raise ValueError(f'Component origin outside die: {name}')
        if re.search(r'__(?:filltie|endcap|fill_\d+)$', master):
            omitted[master] += 1
        else:
            instances[name] = {'name':name, 'master':master, 'x_um':x, 'y_um':y}
    nets = re.search(r'^NETS\s+(\d+)\s*;(.*?)^END NETS', text, re.M|re.S)
    clock_connected = set()
    clock_nets = 0
    for record in re.findall(r'^\s*-\s+(.*?)\s*;', nets[2], re.M|re.S):
        if re.search(r'\+\s+USE\s+CLOCK\b', record):
            clock_nets += 1
            for name, _ in re.findall(r'\(\s*(\S+)\s+(\S+)\s*\)', record.split('+',1)[0]):
                if name in instances:
                    clock_connected.add(name)
    clock_points = [cell for name,cell in instances.items()
                    if name in clock_connected and re.search(r'__(?:clkbuf|clkinv|buf|inv|dly[a-z])_\d+$', cell['master'])]
    if not clock_points or not clock_nets:
        raise ValueError('No clock buffers found; verify postCTS DEF classification')
    return {'variant':variant.upper(), 'die_bbox_um':die, 'core_bbox_um':core,
            'units_per_um':units, 'component_count':len(records),
            'mapped_instance_count':len(instances), 'excluded_physical_cells':dict(omitted),
            'clock_marker_count':len(clock_points), 'clock_net_count':clock_nets,
            'clock_markers':clock_points, 'instances':list(instances.values()),
            'source_def':def_path.relative_to(root).as_posix(), 'source_def_sha256':sha(def_path),
            'source_state':state_path.relative_to(root).as_posix(), 'source_state_sha256':sha(state_path)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path.cwd())
    parser.add_argument('--tag', default='stage5_100ns_u40_clockv3')
    parser.add_argument('--out', type=Path, required=True, help='Output SVG; source JSON uses same stem')
    args = parser.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9_]+', args.tag):
        raise ValueError('Unsafe run tag')
    root = args.root.resolve()
    variants = [load_variant(root,args.tag,v) for v in 'ab']
    if any(v['die_bbox_um'][:2] != [0.0,0.0] for v in variants):
        raise ValueError('Common grid currently requires zero die origin')
    extent = max(max(v['die_bbox_um'][2:]) for v in variants)
    pitch = extent/40
    for v in variants:
        grid = [[0]*40 for _ in range(40)]
        for cell in v.pop('instances'):
            ix = min(39, int(cell['x_um']/pitch)); iy = min(39,int(cell['y_um']/pitch))
            grid[iy][ix] += 1
        assert sum(map(sum,grid)) == v['mapped_instance_count']
        v['grid_counts_y_ascending'] = grid
    peak = max(max(row) for v in variants for row in v['grid_counts_y_ascending'])
    # Common, linear count scale and identical micrometre-to-pixel scale.
    scale = 420/extent
    width,height = 1120,760
    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
           '<rect width="1120" height="760" fill="#ffffff"/>',
           '<style>text{font-family:Arial,Helvetica,sans-serif;fill:#172c44}.small{font-size:14px}.note{font-size:15px}</style>',
           '<text x="55" y="48" font-size="27" font-weight="700">Colocación y árbol de reloj · GF180MCU</text>',
           '<text x="55" y="78" font-size="17">A/B · 100 ns · misma escala física · estado posterior a reparación de timing</text>',
           '<text x="55" y="104" class="note">Mapa derivado de DEF. No muestra cables ni acredita ruteo, DRC o LVS.</text>']
    def color(count):
        t=count/peak if peak else 0
        low=(242,247,251); high=(21,77,124)
        return '#'+''.join(f'{round(a+(b-a)*t):02x}' for a,b in zip(low,high))
    for v,cx in zip(variants,[285,825]):
        die=v['die_bbox_um']; x0=cx-(die[2]*scale)/2; y0=166
        w=die[2]*scale; h=die[3]*scale
        svg += [f'<text x="{cx}" y="135" text-anchor="middle" font-size="21" font-weight="700">Memoria {v["variant"]}</text>',
                f'<text x="{cx}" y="156" text-anchor="middle" class="small">{die[2]:.2f} × {die[3]:.2f} µm</text>',
                f'<defs><clipPath id="die{v["variant"]}"><rect x="{x0:.3f}" y="{y0}" width="{w:.3f}" height="{h:.3f}"/></clipPath></defs>',
                f'<g clip-path="url(#die{v["variant"]})">',
                f'<rect x="{x0:.3f}" y="{y0}" width="{w:.3f}" height="{h:.3f}" fill="{color(0)}"/>']
        for iy,row in enumerate(v['grid_counts_y_ascending']):
            for ix,count in enumerate(row):
                if count:
                    x=x0+ix*pitch*scale; y=y0+(die[3]-(iy+1)*pitch)*scale
                    svg.append(f'<rect x="{x:.3f}" y="{y:.3f}" width="{pitch*scale+.03:.3f}" height="{pitch*scale+.03:.3f}" fill="{color(count)}"><title>{escape(v["variant"])} · bin ({ix},{iy}): {count} orígenes de instancia</title></rect>')
        for cell in v['clock_markers']:
            x=x0+cell['x_um']*scale; y=y0+(die[3]-cell['y_um'])*scale
            svg.append(f'<circle cx="{x:.3f}" cy="{y:.3f}" r="0.75" fill="#ed781a" opacity="0.82"><title>{escape(cell["name"])} · {escape(cell["master"])}</title></circle>')
        core=v['core_bbox_um']; rx=x0+core[0]*scale; ry=y0+(die[3]-core[3])*scale
        svg += ['</g>',f'<rect x="{x0:.3f}" y="{y0}" width="{w:.3f}" height="{h:.3f}" fill="none" stroke="#172c44" stroke-width="1.6"/>',
                f'<rect x="{rx:.3f}" y="{ry:.3f}" width="{(core[2]-core[0])*scale:.3f}" height="{(core[3]-core[1])*scale:.3f}" fill="none" stroke="#b32d60" stroke-width="1.3" stroke-dasharray="4 3"/>',
                f'<text x="{cx}" y="{y0+h+23:.1f}" text-anchor="middle" class="small">{v["mapped_instance_count"]:,} instancias en el mapa · {v["clock_marker_count"]:,} marcas de reloj</text>']
    svg += ['<text x="55" y="638" class="note" font-weight="700">Conteo por bin, no porcentaje de área ocupada</text>']
    for i in range(80):
        svg.append(f'<rect x="{55+i*2.5:.1f}" y="653" width="2.6" height="13" fill="{color(peak*i/79)}"/>')
    svg += [f'<text x="55" y="683" class="small">0</text><text x="255" y="683" text-anchor="end" class="small">{peak} instancias/bin</text>',
            '<circle cx="300" cy="660" r="3" fill="#ed781a"/><text x="312" y="665" class="small">Buffers y cargas del reloj</text>',
            '<path d="M555 660h25" stroke="#b32d60" stroke-width="1.5" stroke-dasharray="4 3"/><text x="589" y="665" class="small">Núcleo</text>',
            '<path d="M695 660h25" stroke="#172c44" stroke-width="1.6"/><text x="729" y="665" class="small">Die</text>',
            f'<path d="M865 656v8m0 -4h{250*scale:.3f}m0 -4v8" stroke="#172c44" stroke-width="1.6"/><text x="{865+125*scale:.3f}" y="683" text-anchor="middle" class="small">250 µm</text>',
            f'<text x="55" y="712" class="small">Malla común 40 × 40 · paso {pitch:.3f} µm en ambos diseños; se recorta al die de A.</text>',
            '<text x="55" y="734" class="small">Incluye lógica y reparación, incluido reloj. Excluye taps/endcaps/fillers. Se cuentan orígenes, no superficies.</text>',
            '</svg>']
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text('\n'.join(svg)+'\n')
    source={'tag':args.tag,'description':'Instance-origin count map, not occupied-area density; placement only, no routing',
            'grid_size':[40,40],'common_pitch_um':pitch,'count_scale':'linear, same range for A/B',
            'maximum_bin_count':peak,'pixels_per_um':scale,'script_sha256':sha(Path(__file__)),
            'svg_sha256':sha(args.out),'variants':variants}
    args.out.with_suffix('.sources.json').write_text(json.dumps(source,indent=2)+'\n')
    print(f'Wrote {args.out} and {args.out.with_suffix(".sources.json")}')
    for v in variants:
        print(v['variant'],v['mapped_instance_count'],'mapped instances;',v['clock_marker_count'],'clock markers;',sum(v['excluded_physical_cells'].values()),'excluded physical cells')


if __name__=='__main__':
    main()
