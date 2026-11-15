from __future__ import annotations
import argparse, concurrent.futures, json, threading, traceback
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
from v2_runtime import run_workflow

def main():
 p=argparse.ArgumentParser(); p.add_argument('--manifest',required=True); p.add_argument('--prefix',required=True); p.add_argument('--workers',type=int,default=4); a=p.parse_args()
 mf=Path(a.manifest); data=json.loads(mf.read_text(encoding='utf-8')); rows=data['rows']; lock=threading.Lock(); outdir=Path('realworld_v2/runs')/a.prefix; outdir.mkdir(parents=True,exist_ok=True)
 def one(i,row):
  out=outdir/f"{row['run_id']}.json"
  try:
   result=run_workflow(Path(row['repo_path']),row['scenario'],row['protocol'],row['repeat'])
   result['run_id']=row['run_id']; out.write_text(json.dumps(result,indent=2),encoding='utf-8')
   return i,'complete',None,result
  except Exception as exc:
   err=f'{type(exc).__name__}: {exc}'; (out.with_suffix('.error.txt')).write_text(traceback.format_exc(),encoding='utf-8')
   failure={"schema":"semkg-v2-run-failure-v1","run_id":row["run_id"],"repository":row["repository"],"scenario":row["scenario"],"protocol":row["protocol"],"repeat":row["repeat"],"status":"agent_or_evaluator_failure","error":err}
   out.write_text(json.dumps(failure,indent=2),encoding='utf-8'); return i,'failed',err,failure
 def save(): mf.write_text(json.dumps(data,indent=2),encoding='utf-8')
 todo=[(i,r) for i,r in enumerate(rows) if r.get('status') not in {'complete','failed'}]
 with concurrent.futures.ThreadPoolExecutor(max_workers=a.workers) as ex:
  futs=[ex.submit(one,i,r) for i,r in todo]
  for fut in concurrent.futures.as_completed(futs):
   i,status,err,result=fut.result(); rows[i]['status']=status; rows[i]['output']=str((outdir/f"{rows[i]['run_id']}.json").resolve());
   if err: rows[i]['error']=err
   with lock: save()
   print(json.dumps({'run_id':rows[i]['run_id'],'status':status,'error':err,'pass':None if result is None else result.get('evaluation',{}).get('all_pass'),'selected':None if result is None else result.get('selected_tasks',[])}),flush=True)
 print(json.dumps({'total':len(rows),'complete':sum(r['status']=='complete' for r in rows),'failed':sum(r['status']=='failed' for r in rows)}))
if __name__=='__main__': main()
