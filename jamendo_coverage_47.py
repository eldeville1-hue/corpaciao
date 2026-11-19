#!/usr/bin/env python3
"""CORPACIAO Release 4.7: random-catalog coverage and unmatched-track diagnosis.
Never interpret API absence as zero listens. Uses private GitHub secret, no credentials exported.
"""
import collections, csv, datetime, hashlib, json, math, os, pathlib, random, time, urllib.parse, urllib.request, urllib.error

OUT=pathlib.Path("coverage_47");OUT.mkdir(exist_ok=True)
CLIENT=os.environ.get("JAMENDO_CLIENT_ID","").strip()
if not CLIENT:raise SystemExit("JAMENDO_CLIENT_ID secret is missing")
SOURCE=pathlib.Path("input/acoustic_features_joined.csv")
PRIOR=pathlib.Path("prior/track_coverage.csv")
N=400
SEED=20261119+47
BATCH=20
API="https://api.jamendo.com/v3.0/tracks/"

def cohort(r):
    e=r["experimental"]=="1";l=r["electronic"]=="1"
    return "both" if e and l else "experimental_only" if e else "electronic_only" if l else "other"

def fetch(ids,with_type):
    args={"client_id":CLIENT,"format":"json","id":" ".join(ids),
          "include":"stats","limit":BATCH}
    if with_type:args["type"]="single albumtrack"
    req=urllib.request.Request(API+"?"+urllib.parse.urlencode(args),
          headers={"User-Agent":"CORPACIAO-independent-coverage-audit/4.7"})
    with urllib.request.urlopen(req,timeout=40) as f:obj=json.load(f)
    hdr=obj.get("headers",{})
    if hdr.get("status")!="success" or str(hdr.get("code"))!="0":
        raise ValueError("API failure: "+str(hdr.get("code"))+" "+str(hdr.get("error_message"))[:100])
    data=obj.get("results")
    if not isinstance(data,list):raise ValueError("Missing results")
    seen={}
    for v in data:
        track=str(v.get("id"))
        if track not in ids:raise ValueError("Unrequested track ID returned")
        if track in seen:raise ValueError("Duplicate ID in API batch")
        st=v.get("stats")
        seen[track]={
          "stats_present":isinstance(st,dict),
          "rate_listened_total":st.get("rate_listened_total") if isinstance(st,dict) else None,
          "rate_downloads_total":st.get("rate_downloads_total") if isinstance(st,dict) else None
        }
    return seen

def evaluate(rows,label,typed):
    results={};failures=[]
    for i in range(0,len(rows),BATCH):
        ids=[r["track_id"] for r in rows[i:i+BATCH]]
        res=None;error=None
        for attempt in range(3):
            try:res=fetch(ids,typed);break
            except (urllib.error.URLError,TimeoutError,ValueError) as exc:
                error=str(exc)[:200]
                if attempt<2:time.sleep(2**attempt)
        if res is None:
            failures.append({"start":i,"error":error})
            for track in ids:results[track]={"status":"api_error"}
        else:
            for track in ids:
                results[track]={"status":"returned",**res[track]} if track in res else {"status":"not_returned"}
        time.sleep(.5)
    path=OUT/(label+".csv")
    with path.open("w",newline="",encoding="utf8") as f:
        columns=["track_id","artist_id","cohort","status","stats_present",
            "rate_listened_total","rate_downloads_total"]
        w=csv.DictWriter(f,fieldnames=columns);w.writeheader()
        for r in rows:w.writerow({**r,**results[r["track_id"]]})
    return results,failures

def wilson(k,n):
    if n==0:return None
    p=k/n;z=1.959963984540054
    den=1+z*z/n
    mid=(p+z*z/(2*n))/den
    rad=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/den
    return [round(max(0,mid-rad),4),round(min(1,mid+rad),4)]

def summarize(rows,res):
    valid=[r for r in rows if res[r["track_id"]]["status"]!="api_error"]
    found=[r for r in valid if res[r["track_id"]]["status"]=="returned"]
    values=[res[r["track_id"]].get("rate_listened_total") for r in found]
    return {"n":len(rows),"query_ok":len(valid),"returned":len(found),
            "listening_value_observed":sum(isinstance(x,(float,int)) for x in values),
            "coverage":round(len(found)/len(valid),4) if valid else None,
            "wilson_95":wilson(len(found),len(valid))}

def main():
    with SOURCE.open(newline="",encoding="utf8") as f:
        catalog=[{"track_id":r["track_id"],"artist_id":r["artist_id"],"cohort":cohort(r)} for r in csv.DictReader(f)]
    with PRIOR.open(newline="",encoding="utf8") as f:
        old=list(csv.DictReader(f))
    absent=[{k:r[k] for k in ("track_id","artist_id","cohort")} for r in old if r["returned"]=="0" and r["request_failed"]=="0"]
    if len(catalog)!=55213 or len(absent)!=161:raise ValueError("Unexpected frozen input counts")
    rng=random.Random(SEED)
    population=rng.sample(sorted(catalog,key=lambda r:int(r["track_id"])),N)
    random_res,random_fail=evaluate(population,"catalog_random_400",False)
    typed_res,typed_fail=evaluate(absent,"prior_missing_typed",True)
    untyped_res,untyped_fail=evaluate(absent,"prior_missing_untyped",False)
    groups={g:summarize([r for r in population if r["cohort"]==g],random_res) for g in ("experimental_only","electronic_only","both","other")}
    diag=collections.Counter((typed_res[r["track_id"]]["status"],untyped_res[r["track_id"]]["status"]) for r in absent)
    report={
      "release":"4.7","time_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
      "random_sampling":"simple random without replacement from all 55213 feature-joined tracks",
      "random_seed":SEED,"catalog_size":len(catalog),
      "random_400":summarize(population,random_res),
      "random_cohorts":groups,
      "missing_from_46":len(absent),
      "missing_recheck_status_cross_tab":[{"typed":x,"untyped":y,"count":n} for (x,y),n in sorted(diag.items())],
      "recovered_with_type":sum(typed_res[r["track_id"]]["status"]=="returned" for r in absent),
      "recovered_without_type":sum(untyped_res[r["track_id"]]["status"]=="returned" for r in absent),
      "api_batch_failures":{"catalog_random":random_fail,"typed_recheck":typed_fail,"untyped_recheck":untyped_fail},
      "does_not_impute_missing_values":True,
      "no_popularity_reranking_performed":True,
      "interpretation":"Current rate_listened_total may be a platform rate/engagement signal, not historical listening counts; missing API records are not zero popularity"}
    (OUT/"RELEASE_47_REPORT.json").write_text(json.dumps(report,indent=2),encoding="utf8")
    print(json.dumps(report,indent=2))
    if random_fail or typed_fail or untyped_fail:raise SystemExit("Partial API errors: do not treat as complete coverage evidence")

if __name__=="__main__":main()
