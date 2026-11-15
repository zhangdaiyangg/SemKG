import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'controller'))
from v2_runtime import ObservedGraph, topology_for
cases={
 'price_unit':[('contract:C','reads','A_direct'),('A_direct','artifact_to_task','B_transitive')],
 'api_error':[('contract:C','reads','A_direct'),('A_direct','artifact_to_task','B_transitive')],
 'state_machine':[('contract:C','reads','A_direct'),('contract:C','reads','B_transitive')],
 'idempotency':[('contract:C','reads','A_direct'),('A_direct','artifact_to_task','B_transitive'),('A_direct','artifact_to_task','D_unrelated')],
 'configuration':[('contract:C','reads','A_direct'),('A_direct','artifact_to_task','B_transitive'),('contract:C','reads','D_unrelated')],
}
rows=[]
for scenario,edges in cases.items():
 g=ObservedGraph()
 for src,rel,dst in edges:g.add(src,rel,dst,'fixture','independent')
 aff,tr=g.affected(); rows.append({'scenario':scenario,'topology':topology_for(scenario),'edges':g.edges,'affected':sorted(aff),'traversal':tr})
Path('realworld_v2/runs/topology_validation.json').write_text(json.dumps({'schema':'v2-topology-validation-v1','rows':rows},indent=2),encoding='utf-8')
print(json.dumps({'topologies':sorted({r['topology'] for r in rows}),'rows':len(rows)}))
