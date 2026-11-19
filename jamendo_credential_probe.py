#!/usr/bin/env python3
"""Five-track Jamendo research feasibility with private GitHub secret."""
import datetime,json,os,pathlib,urllib.request,urllib.parse
ids=['1133100','1375200','1273900','101900','1333600']
client_id=os.environ.get('JAMENDO_CLIENT_ID','').strip()
if not client_id: raise SystemExit('Missing JAMENDO_CLIENT_ID secret')
report={'purpose':'5-track API permission and track-ID / stats coverage check','track_ids':ids,
        'timestamp_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(), 'results':[],
        'confirmatory_recommendation_evaluation':False,'bulk_access':False}
for t in ids:
    params=urllib.parse.urlencode({'client_id':client_id,'id':t,'limit':1,'include':'stats','format':'json','type':'single albumtrack'})
    req=urllib.request.Request('https://api.jamendo.com/v3.0/tracks/?'+params,headers={'User-Agent':'CORPACIAO-research-metadata-pilot/0.1'})
    row={'requested_track_id':t}
    try:
        with urllib.request.urlopen(req,timeout=30) as f:data=json.load(f)
        header=data.get('headers',{})
        row.update(api_status=header.get('status'),api_code=header.get('code'),api_error=header.get('error_message'),result_count=len(data.get('results',[])))
        if data.get('results'):
            result=data['results'][0];stats=result.get('stats')
            row.update(returned_track_id=str(result.get('id')),id_matches=str(result.get('id'))==t,
                stats_fields=sorted(stats) if isinstance(stats,dict) else [],
                rate_listened_total=stats.get('rate_listened_total') if isinstance(stats,dict) else None,
                rate_downloads_total=stats.get('rate_downloads_total') if isinstance(stats,dict) else None,
                stats_present=isinstance(stats,dict))
    except Exception as e:row['request_failed']=str(e)[:300]
    report['results'].append(row)
path=pathlib.Path('jamendo_auth_probe');path.mkdir(exist_ok=True)
(path/'API_COVERAGE_REPORT.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps({'requests':len(ids),'success_responses':sum(x.get('api_status')=='success' for x in report['results']),
 'matched_tracks':sum(x.get('id_matches') is True for x in report['results']),
 'stats_present':sum(x.get('stats_present') is True for x in report['results'])},indent=2))
