#!/usr/bin/env python3
"""CORPACIAO 4.6 — stratified Jamendo track-statistics COVERAGE audit.

This is an access/measurement validation, not a popularity-effect experiment.
No missing stats are imputed; the source is a frozen prior GitHub Actions artifact.
"""
import collections,csv,datetime,io,json,math,os,pathlib,random,time,urllib.parse,urllib.request,urllib.error

ROOT=pathlib.Path("jamendo_coverage_46")
ROOT.mkdir(exist_ok=True)
SOURCE=pathlib.Path("input/acoustic_features_joined.csv")
SEED=20261119
N_PER_STRATUM=100
BATCH_SIZE=20
TARGETS=("experimental_only","electronic_only","both","other")
API="https://api.jamendo.com/v3.0/tracks/"
CLIENT=os.environ.get("JAMENDO_CLIENT_ID","").strip()
if not CLIENT:
    raise SystemExit("JAMENDO_CLIENT_ID secret absent. No API calls made.")

def group(row):
    ex=row["experimental"]=="1"
    el=row["electronic"]=="1"
    return "both" if ex and el else "experimental_only" if ex else "electronic_only" if el else "other"

def sample():
    grouped=collections.defaultdict(list)
    with SOURCE.open(newline="",encoding="utf-8") as f:
        for row in csv.DictReader(f):
            grouped[group(row)].append({"track_id":row["track_id"],"artist_id":row["artist_id"],"cohort":group(row)})
    rng=random.Random(SEED)
    chosen=[]
    global_artists=set()
    for cohort in TARGETS:
        entries=sorted(grouped[cohort],key=lambda x:int(x["track_id"]))
        rng.shuffle(entries)
        used=set()
        sampled=[]
        for row in entries:
            if row["artist_id"] in used or row["artist_id"] in global_artists:continue
            used.add(row["artist_id"]);global_artists.add(row["artist_id"])
            sampled.append(row)
            if len(sampled)>=N_PER_STRATUM:break
        if len(sampled)<N_PER_STRATUM:
            raise ValueError(f"Insufficient distinct artists for {cohort}: {len(sampled)}")
        chosen.extend(sampled)
    with (ROOT/"sample_manifest.csv").open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=["track_id","artist_id","cohort"])
        w.writeheader();w.writerows(chosen)
    return chosen,{k:len(v) for k,v in grouped.items()}

def api_request(ids):
    query=urllib.parse.urlencode({
        "client_id":CLIENT,"format":"json","id":" ".join(ids),
        "limit":BATCH_SIZE,"type":"single albumtrack","include":"stats"})
    req=urllib.request.Request(API+"?"+query,headers={"User-Agent":"CORPACIAO-Research-Coverage-Audit/4.6"})
    with urllib.request.urlopen(req,timeout=35) as res:
        obj=json.load(res)
    h=obj.get("headers",{})
    if h.get("status")!="success" or h.get("code") not in (0,"0"):
        raise RuntimeError("Jamendo API returned "+str(h.get("code"))+": "+str(h.get("error_message")))
    records=obj.get("results")
    if not isinstance(records,list):raise ValueError("API response missing results")
    return records

def wilson(hit,total):
    if total==0:return [None,None]
    z=1.959963984540054
    p=hit/total
    a=1+z*z/total
    mid=(p+z*z/(2*total))/a
    h=z*math.sqrt(p*(1-p)/total+z*z/(4*total*total))/a
    return [round(max(0,mid-h),4),round(min(1,mid+h),4)]

def main():
    sample_rows,pop=sample()
    result={}
    errors=[]
    batches=0
    for start in range(0,len(sample_rows),BATCH_SIZE):
        ids=[r["track_id"] for r in sample_rows[start:start+BATCH_SIZE]]
        success=False
        for attempt in range(3):
            try:
                rows=api_request(ids)
                batch_set=set(ids)
                for row in rows:
                    track_id=str(row.get("id"))
                    if track_id not in batch_set:
                        raise ValueError("Returned ID not requested")
                    if track_id in result:raise ValueError("Duplicate API returned ID")
                    stats=row.get("stats")
                    result[track_id]={
                        "stats_present":isinstance(stats,dict),
                        "rate_listened_total":stats.get("rate_listened_total") if isinstance(stats,dict) else None,
                        "rate_downloads_total":stats.get("rate_downloads_total") if isinstance(stats,dict) else None,
                        "stats_keys":"|".join(sorted(stats.keys())) if isinstance(stats,dict) else ""
                    }
                success=True
                batches+=1
                break
            except (urllib.error.URLError,TimeoutError,RuntimeError) as e:
                if attempt==2:errors.append({"batch_start":start,"error":str(e)[:200]})
                else:time.sleep(2**attempt)
        if not success:
            # Never mark API errors as missing tracks.
            for track_id in ids:
                result[track_id]={"request_failed":True}
        time.sleep(.8)
    with (ROOT/"track_coverage.csv").open("w",newline="",encoding="utf8") as f:
        fields=["track_id","artist_id","cohort","request_failed","returned","stats_present",
                "rate_listened_total","rate_downloads_total","stats_keys"]
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
        for row in sample_rows:
            info=result.get(row["track_id"],{})
            w.writerow({**row,"request_failed":int(info.get("request_failed",False)),
                       "returned":int("stats_present" in info),
                       "stats_present":int(info.get("stats_present",False)),
                       "rate_listened_total":info.get("rate_listened_total"),
                       "rate_downloads_total":info.get("rate_downloads_total"),
                       "stats_keys":info.get("stats_keys","")})
    table=[]
    for cohort in TARGETS:
        group_rows=[x for x in sample_rows if x["cohort"]==cohort]
        valid=[x for x in group_rows if not result.get(x["track_id"],{}).get("request_failed",False)]
        returned=[x for x in valid if "stats_present" in result.get(x["track_id"],{})]
        valued=[x for x in returned if isinstance(result[x["track_id"]].get("rate_listened_total"),(int,float))]
        table.append({"cohort":cohort,"sampled":len(group_rows),
                     "successfully_queried":len(valid),"tracks_returned":len(returned),
                     "listening_rate_observed":len(valued),
                     "track_id_coverage":round(len(returned)/len(valid),4) if valid else None,
                     "track_id_coverage_wilson_95":wilson(len(returned),len(valid))})
    report={"project":"CORPACIAO","release":"4.6",
           "status":"VALID" if not errors else "PARTIAL_API_ERRORS",
           "timestamp_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
           "sampling_seed":SEED,"n_per_cohort_target":N_PER_STRATUM,
           "sampling":"deterministic random selection; no artist repeated within/across cohorts",
           "catalog_cohort_counts":pop,
           "results_by_cohort":table,"api_successful_batches":batches,
           "failed_batches":errors,
           "stat_definition_note":"rate_listened_total is returned by Jamendo API; it is not asserted to equal raw historical listener counts or FMA listens.",
           "sample_only":True,"no_reranking_outcome_test":True,
           "missing_tracks_not_imputed":True}
    (ROOT/"COVERAGE_REPORT.json").write_text(json.dumps(report,indent=2),encoding="utf8")
    print(json.dumps({"status":report["status"],"results_by_cohort":table,"failed_batches":errors},indent=2))
    if errors:raise SystemExit("API errors encountered; results are partial and not a valid coverage estimate.")
    if sum(x["tracks_returned"] for x in table)==0:raise SystemExit("No matching Jamendo track IDs.")

if __name__=="__main__":
    main()
