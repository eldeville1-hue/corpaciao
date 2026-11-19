#!/usr/bin/env python3
"""Merge pilot52 shards and calculate validation metrics (no reranking)."""
import csv,json,pathlib,collections,math,hashlib
root=pathlib.Path("pilot52_shards")
out=pathlib.Path("pilot52_final");out.mkdir(exist_ok=True)
files=sorted(root.rglob("observed_*.csv"))
reps=sorted(root.rglob("report_*.json"))
if len(files)!=4 or len(reps)!=4:raise ValueError(f"Need 4 shards, got {len(files)} CSV and {len(reps)} reports")
reports=[json.loads(p.read_text()) for p in reps]
if {r["shard"] for r in reports}!={0,1,2,3}:raise ValueError("shard mismatch")
if any(r["api_errors"] for r in reports):raise ValueError("API errors: invalid pilot")
rows=[]
for f in files:
    with f.open(newline="",encoding="utf8") as input:rows.extend(csv.DictReader(input))
if len(rows)!=2000 or len({r["track_id"] for r in rows})!=2000:raise ValueError("missing or duplicate tracks")
def summarise(items):
    n=len(items);good=[r for r in items if r["status"]=="returned"]
    vals=[r for r in good if r["rate_listened_total"] not in ("",None)]
    p=len(good)/n if n else None
    ci=None
    if n:
        z=1.96;den=1+z*z/n
        cen=(p+z*z/(2*n))/den
        rad=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/den
        ci=[round(max(0,cen-rad),4),round(min(1,cen+rad),4)]
    return {"n":n,"returned":len(good),"listening_rate_observed":len(vals),
            "coverage":round(p,4) if p is not None else None,"wilson_95":ci}
groups=sorted({r["cohort"] for r in rows})
report={"release":"5.2","status":"COMPLETE","total":summarise(rows),
        "by_cohort":{k:summarise([r for r in rows if r["cohort"]==k]) for k in groups},
        "api_attempts":sum(r["sent_api_attempts"] for r in reports),
        "warnings_nonempty":sum(r["warnings_nonempty"] for r in reports),
        "method":"simple random 2,000 of 55,213; fixed seed; 4 shards, 20 IDs/batch, single albumtrack, id_asc",
        "limitations":["Current Jamendo engagement rate is not validated as an historical raw play count.",
                       "Nonreturn is missing, not 0.", "One-pass retrieval; rates reflect this protocol and timestamp.",
                       "Sample coverage alone does not validate full-list reranking."],
        "full_catalog_acquisition_executed":False,
        "popularity_reranking_executed":False}
with (out/"pilot_observations.csv").open("w",newline="",encoding="utf8") as f:
    w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(sorted(rows,key=lambda x:int(x["track_id"])))
report["sha256_observations"]=hashlib.sha256((out/"pilot_observations.csv").read_bytes()).hexdigest()
(out/"PILOT_52_REPORT.json").write_text(json.dumps(report,indent=2),encoding="utf8")
print(json.dumps(report,indent=2))
