import json, tempfile
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'controller'))
from v2_runtime import contract_pair

def run(code,scenario,meta):
 ns={}; exec(compile(code,'artifact.py','exec'),ns)
 fn={'price_unit':'normalize_price','api_error':'parse_error','state_machine':'can_transition','idempotency':'idempotency_key','configuration':'timeout'}[scenario]
 try:
  inp=meta['input']; got=ns[fn](*inp) if scenario=='state_machine' else ns[fn](inp); return got, None
 except Exception as e: return None,e.__class__.__name__
def main():
 rows=[]
 for s in ['price_unit','api_error','state_machine','idempotency','configuration']:
  v1,v2,m=contract_pair(s); new,ne=run(v2,s,m); old,oe=run(v1,s,m)
  pos=(new==m['expected'] or ne==m['expected']); neg=(old!=m['expected'] and oe!=m['expected'])
  rows.append({'scenario':s,'positive_new_pass':pos,'negative_old_reject':neg,'new_value':new,'new_error':ne,'old_value':old,'old_error':oe,'oracle':m})
 result={'schema':'v2-hidden-validation-v1','rows':rows,'all_positive':all(x['positive_new_pass'] for x in rows),'all_negative':all(x['negative_old_reject'] for x in rows)}
 Path('realworld_v2/runs/hidden_test_validation.json').write_text(json.dumps(result,indent=2),encoding='utf-8'); print(json.dumps({'positive':result['all_positive'],'negative':result['all_negative']})); raise SystemExit(0 if result['all_positive'] and result['all_negative'] else 1)
if __name__=='__main__': main()
