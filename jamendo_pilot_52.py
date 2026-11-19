#!/usr/bin/env python3
"""CORPACIAO 5.2: bounded Jamendo engagement coverage pilot.
120? No: preselected 2000 unique tracks sampled from 55213, split into 4
500-track shards. Missing remains missing; no repeated harvesting or imputation.
API client ID stays in Actions secret. Primary purpose: acquisition feasibility.
"""
import argparse,csv,datetime,hashlib,json,os,pathlib,random,time,urllib.parse,urllib.request,urllib.error,collections,math
SEED=2026111952
N=2000
SHARDS=4
BATCH=20
API="https://api.jamendo.com/v3.0/tracks/"
def pick(source):
    with open(source,newline="",encoding="utf-8") as f:
        rows=[r for r in csv.DictReader(f)]
    if len(rows)!=55213:raise ValueError("Unexpected catalog row count")
    randomizer=random.Random(SEED)
    sample=randomizer.sample(rows,N)
    return sample

def cls(r):
    e=r["experimental"]=="1"; t=r["electronic"]=="1"
    return "both" if e and t else "experimental_only" if e else "electronic_only" if t else "other"

def request(ids,client):
    args={"client_id":client,"format":"json","id":" ".join(ids),
          "limit":200,"include":"stats","type":"single albumtrack","order":"id_asc"}
    url=API+"?"+urllib.parse.urlencode(args)
    req=urllib.request.Request(url,headers={"User-Agent":"CORPACIAO-Research-CoveragePilot/5.2"})
    with urllib.request.urlopen(req,timeout=40) as res:content=json.load(res)
    hdr=content.get("headers",{})
    if hdr.get("status")!="success" or str(hdr.get("code"))!="0":
        raise ValueError("Jamendo code "+str(hdr.get("code"))+" "+str(hdr.get("error_message"))[:120])
    results=content.get("results")
    if not isinstance(results,list):raise ValueError("Missing API results")
    found={}
    for row in results:
        tid=str(row.get("id"))
        if tid not in ids or tid in found:raise ValueError("Unexpected or duplicated API ID")
        stats=row.get("stats")
        found[tid]={"stats_present":int(isinstance(stats,dict)),
                    "rate_listened_total":stats.get("rate_listened_total") if isinstance(stats,dict) else "",
                    "rate_downloads_total":stats.get("rate_downloads_total") if isinstance(stats,dict) else ""}
    return found,hdr.get("warnings"),hdr.get("results_count")

def main():
    p=argparse.ArgumentParser();p.add_argument("--shard",type=int,required=True)
    args=p.parse_args();i=args.shard
    if i not in range(SHARDS):raise ValueError("Invalid shard")
    client=os.getenv("JAMENDO_CLIENT_ID","").strip()
    if not client:raise ValueError("JAMENDO_CLIENT_ID absent")
    sample=pick("input/acoustic_features_joined.csv")
    sample_rows=[r for idx,r in enumerate(sample) if idx%SHARDS==i]
    out=pathlib.Path("pilot52");out.mkdir(exist_ok=True)
    records=[];errors=[];warning_count=0;attempts=0
    for start in range(0,len(sample_rows),BATCH):
        chunk=sample_rows[start:start+BATCH]
        ids=[r["track_id"] for r in chunk]
        found=None;err=""
        for attempt in range(3):
            attempts+=1
            try:
                found,warnings,returned=request(ids,client)
                if warnings:warning_count+=1
                break
            except (ValueError,TimeoutError,urllib.error.URLError) as exc:
                err=f"{type(exc).__name__}: {exc}"[:200]
                if attempt<2:time.sleep(1+attempt)
        if found is None:errors.append({"batch_start":start,"error":err})
        ts=datetime.datetime.now(datetime.timezone.utc).isoformat()
        for r in chunk:
            tid=r["track_id"];data=found.get(tid) if found is not None else None
            records.append({"track_id":tid,"artist_id":r["artist_id"],"cohort":cls(r),
                "status":"api_error" if found is None else "returned" if data is not None else "not_returned",
                "stats_present":data["stats_present"] if data else "",
                "rate_listened_total":data["rate_listened_total"] if data else "",
                "rate_downloads_total":data["rate_downloads_total"] if data else "",
                "measured_utc":ts})
        time.sleep(.25)
    if len(records)!=len(sample_rows):raise ValueError("Lost input rows")
    dest=out/f"observed_{i}.csv"
    cols=["track_id","artist_id","cohort","status","stats_present","rate_listened_total","rate_downloads_total","measured_utc"]
    with dest.open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=cols);w.writeheader();w.writerows(records)
    report={"release":"5.2","shard":i,"seed":SEED,"catalog":55213,
            "sample_total":N,"shard_tracks":len(sample_rows),"batch_size":BATCH,
            "sent_api_attempts":attempts,"warnings_nonempty":warning_count,
            "api_errors":errors,"returned":sum(r["status"]=="returned" for r in records),
            "not_returned":sum(r["status"]=="not_returned" for r in records),
            "source":"previously verified external acoustic catalog",
            "retrieval_rule":"type=single albumtrack, order=id_asc, 20 IDs, limit=200",
            "no_missing_imputation":True}
    (out/f"report_{i}.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    print(json.dumps(report,indent=2))
    if errors:raise SystemExit("Incomplete: API requests failed. No coverage claim.")
if __name__=="__main__":main()
