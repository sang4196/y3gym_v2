from pathlib import Path
import json,re,sys
qdir=Path('backend/review/qa-lifecycle-independent');root=Path.cwd();sys.path.insert(0,str(root/'backend/scripts'));import qa_lifecycle as q
p=root/'.local/qa/qa-20261013T151215Z-aa300e83d93f/logs/auto-browser-cli.log';d=json.loads(p.read_text());assert d['command_exit_code']==0 and d['cleanup']['state']=='DELETED'
e=[json.loads(x.read_text()) for x in Path(d['evidence']).glob('evidence-auto-result-*.json')];assert len(e)==1;ev=e[0];assert ev['tests']['run']==ev['tests']['pass']==1 and not ev['tests']['skip'];bs=ev['browser_result_summaries'];assert len(bs)==1 and bs[0]['status']=='PASS' and bs[0]['checks']==11 and bs[0]['errors']==0
runtime=ev['browser_runtime'];assert len(runtime)==1 and runtime[0].get('exe');assert q.proc_info(runtime[0]['pid'],strict=True) is None
run,value,token=q.load(d['run_id']);assert not run.exists() and token is None
with q.db_connect() as connection,connection.cursor() as cursor:assert all(q.db_state(cursor,name) is None for name in value['database_names'])
origins=sorted(set(re.findall(r'http://localhost:\d+', '\n'.join(x['diagnostic'] for x in ev['sanitized_logs']))));assert origins and not any(x.rsplit(':',1)[1] in ['8767','8768','8769','8772','8773','8774','8775','8776','8780','8781','34471'] for x in origins)
summary={'status':'PASS','CLI':d,'tests':ev['tests'],'browser_result_summaries':bs,'browser_runtime':runtime,'actual_Chrome_process_exited':True,'live_signed_identity_observation':'browser-live-observation.json','origins_in_sanitized_run_log':origins,'both_reserved_DBs_absent':True,'run_folder_absent':True}
(qdir/'auto-browser.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps({'id':d['run_id'],'run_pass':1,'internal_pass':11,'origin':origins,'Chrome_exited':True,'cleanup':'DELETED'}))
