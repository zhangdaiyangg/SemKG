import argparse,csv,json,time,statistics,collections
from pathlib import Path
import sys
sys.path.insert(0,'realworld_v2/controller')
from v2_runtime import ObservedGraph
ap=argparse.ArgumentParser(); ap.add_argument('--runs-dir',default='realworld_v2/runs/formal'); ap.add_argument('--label',default='formal'); args=ap.parse_args()
rows=[]
for p in sorted(Path(args.runs_dir).glob('*.json')):
 d=json.loads(p.read_text())
 if not d.get('schema','').startswith('semkg-v2-run-v1'): continue
 ev=d['events']; records=[]
 for mode in ['cold','warm','incremental']:
  g=ObservedGraph(); t=time.perf_counter(); g.from_events(ev); build=time.perf_counter()-t
  if mode=='cold': cold=build
  elif mode=='warm': warm=build
  else:
   t=time.perf_counter(); g.add('contract:C','metadata','A_direct','instrumented_contract','scenario'); g.affected(); incr=time.perf_counter()-t
 rows.append({'run_id':d['run_id'],'protocol':d['protocol'],'repository':d['repository'],'scenario':d['scenario'],'cold_graph_build_seconds':cold,'warm_graph_build_seconds':warm,'incremental_graph_update_seconds':incr})
out=Path('realworld_v2/reports')/f'V2_GRAPH_COST_REPLAY_{args.label}.csv';
with out.open('w',newline='',encoding='utf-8') as h:
 w=csv.DictWriter(h,fieldnames=rows[0].keys());w.writeheader();w.writerows(rows)
print(json.dumps({'rows':len(rows),'cold':sum(x['cold_graph_build_seconds'] for x in rows),'warm':sum(x['warm_graph_build_seconds'] for x in rows),'incremental':sum(x['incremental_graph_update_seconds'] for x in rows)}))
