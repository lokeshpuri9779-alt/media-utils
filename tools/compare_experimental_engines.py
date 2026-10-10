"""Compare real experimental benchmark reports; never invent quality scores.

Usage: python tools/compare_experimental_engines.py artifacts/experimental-*/report.json
Also accepts OpenVINO keyframe.json and Blender report.json.
"""
import argparse,json
from pathlib import Path

def compare(paths):
    rows=[]
    for path in paths:
        p=Path(path)
        try:
            d=json.loads(p.read_text())
            if not isinstance(d,dict):raise ValueError('report must be object')
            rows.append({'report':str(p),'engine':d.get('engine') or d.get('renderer') or d.get('model') or 'unknown',
                         'success':d.get('success') is True,'elapsed_seconds':d.get('elapsed_seconds'),
                         'output':d.get('output'),'error':d.get('error'),
                         'quality_verified':False,'production_eligible':False})
        except (OSError,ValueError) as exc:
            rows.append({'report':str(p),'success':False,'error':f'{type(exc).__name__}: {exc}',
                         'quality_verified':False,'production_eligible':False})
    valid=[x for x in rows if x['success'] and isinstance(x['elapsed_seconds'],(int,float)) and x['elapsed_seconds']>0]
    fastest=min(valid,key=lambda x:x['elapsed_seconds'])['engine'] if valid else None
    # Time-only winner is not a quality winner. Images and videos require review.
    return {'benchmarks':rows,'fastest_successful_benchmark':fastest,
            'visual_quality_winner':None,'promoted_engine':None,
            'warning':'Still images and animated videos are different tasks; timing is not directly comparable.'}

def main():
    p=argparse.ArgumentParser();p.add_argument('reports',nargs='+');p.add_argument('--output',type=Path)
    a=p.parse_args();data=compare(a.reports)
    result=json.dumps(data,indent=2)
    if a.output:
        a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(result+'\\n')
    print(result)

if __name__=='__main__':main()
