#!/usr/bin/env python3
"""CORPACIAO 4.9: controlled ID retrieval with explicit documented type semantics.

Uses fixed 4.8 track sample. No outcomes, no missing=0 assumptions.
Vary retrieval batch size but keep type='single albumtrack' and limit=200.
Logs API header warnings and fullcount hints, not credentials.
"""
import csv,datetime,json,os,pathlib,random,time,urllib.parse,urllib.request,urllib.error
ROOT=pathlib.Path("consistency_49");ROOT.mkdir(exist_ok=True)
CLIENT=os.environ.get("JAMENDO_CLIENT_ID","").strip()
if not CLIENT:raise SystemExit("Missing private JAMENDO_CLIENT_ID")
with open("prior48/sample_manifest.csv",newline="",encoding="utf8") as f:
    sample=list(csv.DictReader(f))
ids=sorted([r["track_id"] for r in sample],key=int)
if len(ids)!=60 or len(set(ids))!=60:raise ValueError("Expected exactly 60 unique frozen IDs")
rng=random.Random(2026111949)
base="https://api.jamendo.com/v3.0/tracks/"
records=[];requests=[];errors=[]
def retrieve(batch,kind,cycle):
    params={"client_id":CLIENT,"format":"json","id":" ".join(batch),"limit":200,"include":"stats",
            "type":"single albumtrack"}
    if kind=="explicit_id_order":params["order"]="id_asc"
    url=base+"?"+urllib.parse.urlencode(params)
    req=urllib.request.Request(url,headers={"User-Agent":"CORPACIAO-retrieval-consistency-4.9"})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req,timeout=40) as response:obj=json.load(response)
            h=obj.get("headers",{})
            if h.get("status")!="success" or str(h.get("code"))!="0":
                raise RuntimeError(f"Jamendo error code={h.get('code')}: {h.get('error_message')}")
            rows=obj.get("results")
            if not isinstance(rows,list):raise ValueError("Missing results array")
            returned={}
            for r in rows:
                tid=str(r.get("id"))
                if tid not in batch or tid in returned:raise ValueError("Unexpected/duplicate track ID "+tid)
                stats=r.get("stats")
                returned[tid]={"rate_listened_total":stats.get("rate_listened_total") if isinstance(stats,dict) else None,
                               "stats_present":isinstance(stats,dict)}
            requests.append({"cycle":cycle,"kind":kind,"batch_n":len(batch),"result_count":len(returned),
                   "header_results_count":h.get("results_count"),"warnings":str(h.get("warnings",""))[:500]})
            for tid in batch:
                a=returned.get(tid)
                records.append({"cycle":cycle,"kind":kind,"track_id":tid,"batch_n":len(batch),
                   "status":"returned" if a else "not_returned",
                   "stats_present":int(a["stats_present"]) if a else "",
                   "rate_listened_total":a["rate_listened_total"] if a else ""})
            return
        except (urllib.error.URLError,TimeoutError,RuntimeError,ValueError) as e:
            if attempt==2:
                errors.append({"cycle":cycle,"kind":kind,"batch_n":len(batch),"error":str(e)[:250]})
                for tid in batch:records.append({"cycle":cycle,"kind":kind,"track_id":tid,"batch_n":len(batch),"status":"api_error","stats_present":"","rate_listened_total":""})
            else:time.sleep(1+attempt)
def run_config(kind,batches,cycle):
    for group in batches:
        retrieve(group,kind,cycle)
        time.sleep(.15)
for cycle in (1,2):
    order=ids[:];rng.shuffle(order)
    # same exact ids and type filter across all arms
    batch20=[order[i:i+20] for i in range(0,60,20)]
    batch60=[order]
    single=[[x] for x in order]
    arms=[("single",single),("batch20",batch20),("batch60",batch60),("explicit_id_order",batch20)]
    if cycle==2:arms.reverse()
    for kind,batches in arms:
        run_config(kind,batches,cycle)
    print(f"Completed cycle {cycle}",flush=True)
with (ROOT/"observations.csv").open("w",newline="",encoding="utf8") as f:
    fields=["cycle","kind","track_id","batch_n","status","stats_present","rate_listened_total"]
    w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(records)
with (ROOT/"request_headers.json").open("w",encoding="utf8") as f:json.dump(requests,f,indent=2)
kinds=["single","batch20","batch60","explicit_id_order"]
summaries=[];repeat=[]
for kind in kinds:
    a={r["track_id"]:r for r in records if r["kind"]==kind and r["cycle"]==1}
    b={r["track_id"]:r for r in records if r["kind"]==kind and r["cycle"]==2}
    arr=list(a.values())+list(b.values())
    good=[r for r in arr if r["status"]!="api_error"]
    observed=sum(r["status"]=="returned" for r in good)
    summaries.append({"method":kind,"observed":observed,"valid":len(good),
             "retrieval_fraction":round(observed/len(good),4) if good else None})
    consistent=sum(a[t]["status"]==b[t]["status"] for t in ids if a[t]["status"]!="api_error" and b[t]["status"]!="api_error")
    n=sum(a[t]["status"]!="api_error" and b[t]["status"]!="api_error" for t in ids)
    repeat.append({"method":kind,"matched_status":consistent,"comparable":n})
recover={kind:len(set(r["track_id"] for r in records if r["kind"]==kind and r["status"]=="returned")) for kind in kinds}
report={"release":"4.9","timestamp_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "source":"frozen 4.8 difficult-to-retrieve 60 tracks",
        "documented_parameters":"id=space-separated, type=single albumtrack, include=stats, limit=200",
        "summary":summaries,"repeatability":repeat,"unique_tracks_recovered_by_method":recover,
        "unique_tracks_recovered_any":len({r["track_id"] for r in records if r["status"]=="returned"}),
        "api_errors":errors,"api_requests_logged":len(requests),
        "no_popularity_experiment":True,
        "note":"Non-random stress-test subset; retrieval rates do not estimate whole-catalog coverage"}
(ROOT/"REPORT_49.json").write_text(json.dumps(report,indent=2),encoding="utf8")
print(json.dumps(report,indent=2))
if errors:raise SystemExit("API error(s); diagnostics are partial")
