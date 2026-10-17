#!/usr/bin/env python3
"""Inspect archived CST surfaces against the input profile; no CFD is run."""
from pathlib import Path
import argparse
import base64
import csv
import io
import json
import struct
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]

def read_array(element):
    encoded = ''.join(element.text.split())
    decoded = base64.b64decode(encoded)
    length = struct.unpack('<Q', decoded[:8])[0]
    # OpenFOAM may encode the length header and payload separately.
    payload = base64.b64decode(encoded[12:]) if len(decoded)==8 else decoded[8:]
    if len(payload) != length:
        raise ValueError('VTK array length mismatch')
    code = {'Float32':'f','Float64':'d','Int32':'i','Int64':'q'}[element.attrib['type']]
    return struct.unpack('<' + code*(len(payload)//struct.calcsize(code)), payload)

def wing_surface(path):
    root = ET.parse(path).getroot()
    if root.get('byte_order')!='LittleEndian' or root.get('header_type')!='UInt64' or root.get('compressor'):
        raise ValueError('This lightweight reader supports the archived uncompressed UInt64 LittleEndian files only')
    raw = read_array(root.find('.//Points/DataArray'))
    points = list(zip(raw[::3],raw[1::3],raw[2::3]))
    conn = read_array(root.find('.//Polys/DataArray[@Name="connectivity"]'))
    offsets = read_array(root.find('.//Polys/DataArray[@Name="offsets"]'))
    pressure = read_array(root.find('.//CellData/DataArray[@Name="p"]'))
    start=0; rows=[]
    for i,end in enumerate(offsets):
        ids=conn[start:end]; start=end
        if len(ids)<3:
            continue
        face=[points[j] for j in ids]
        # Select faces spanning the extrusion, excluding flat symmetry planes.
        if max(p[1] for p in face)-min(p[1] for p in face) < 1e-9:
            continue
        rows.append({'x_over_c':sum(p[0] for p in face)/len(face),
                     'z_over_c':sum(p[2] for p in face)/len(face),
                     'Cp':pressure[i]/450.0})
    return rows

def profile():
    result=[]
    for line in (ROOT/'cases/case-b-cst/profiles/s809.dat').read_text().splitlines():
        try:
            x,z = map(float,line.split())
        except ValueError:
            continue
        result.append({'x_over_c':x,'z_over_c':z})
    return result

def bounds(rows):
    return {'count':len(rows),'min_x':min(r['x_over_c'] for r in rows),
            'max_x':max(r['x_over_c'] for r in rows),
            'min_z':min(r['z_over_c'] for r in rows),'max_z':max(r['z_over_c'] for r in rows)}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write',action='store_true')
    parser.add_argument('--plot',action='store_true')
    args=parser.parse_args()
    datasets={'input-profile':profile(),
              'cst-baseline':wing_surface(ROOT/'data/surfaces/cst-baseline.vtp'),
              'cst-optimized':wing_surface(ROOT/'data/surfaces/cst-optimized.vtp')}
    report={'status':'needs_geometry_verification',
            'description':'Archived CST baseline face-centroid coordinates have a larger vertical envelope than the input profile; cause not established.',
            'caution':'Envelope bounds are not a maximum-section-thickness calculation; this is a geometry diagnostic, not a new flow solution.',
            'coordinate_bounds':{name:bounds(rows) for name,rows in datasets.items()}}
    for name,rows in datasets.items():
        stream=io.StringIO(newline='')
        writer=csv.DictWriter(stream,fieldnames=list(rows[0]),lineterminator='\n')
        writer.writeheader(); writer.writerows(rows)
        destination=ROOT/'data'/f'{name}-geometry.csv'
        if args.write:
            destination.write_text(stream.getvalue(),encoding='utf-8',newline='')
        elif not destination.exists() or destination.read_text(encoding='utf-8')!=stream.getvalue():
            raise SystemExit(f'{destination.name} missing or stale; use --write')
    summary=json.dumps(report,indent=2)+'\n'
    destination=ROOT/'data/surface-geometry-audit.json'
    if args.write:
        destination.write_text(summary,encoding='utf-8')
    elif not destination.exists() or destination.read_text(encoding='utf-8')!=summary:
        raise SystemExit('Surface geometry audit missing or stale; use --write')
    if args.plot:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        fig,axis=plt.subplots(figsize=(10,4.8),layout='constrained')
        rows=datasets['input-profile']
        axis.plot([r['x_over_c'] for r in rows],[r['z_over_c'] for r in rows],color='black',lw=1.8,label='Input S809 profile')
        for name,color in [('cst-baseline','#2468a0'),('cst-optimized','#bb563b')]:
            rows=datasets[name]
            axis.scatter([r['x_over_c'] for r in rows],[r['z_over_c'] for r in rows],s=10,color=color,label=f'Archived {name} centroids')
        axis.set(xlabel='x/c',ylabel='z/c',title='CST surface geometry diagnostic: correspondence needs verification',xlim=(-.02,1.02),ylim=(-.19,.19))
        axis.set_aspect('equal',adjustable='box'); axis.grid(alpha=.2)
        axis.legend(loc='upper center',bbox_to_anchor=(.5,-.2),ncol=1,fontsize=9)
        fig.savefig(ROOT/'results/figures/geometry-diagnostic.png',dpi=180,bbox_inches='tight',pad_inches=.18)
        plt.close(fig)
    print(summary)

if __name__=='__main__':
    main()
