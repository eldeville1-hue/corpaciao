#!/usr/bin/env python3
"""CORPACIAO 5.0 - fresh-catalog paired Jamendo API retrieval crossover.

Feasibility only. Collect no popularity-reranking outcomes.
One stable random sample of 120 IDs (excludes prior 4.6/4.7 samples).
Within six fixed 20-track blocks, counterbalance the order of 20-ID
requests with/without explicit id_asc, repeat twice; additionally
probe a preselected 24-track single-ID panel across both cycles.
"""
import collections,csv,datetime,hashlib,json,math,os,pathlib,random,time,urllib.parse,urllib.request,urllib.error
OUT=pathlib.Path("retrieval_50");OUT.mkdir(exist_ok=True)
CLIENT=os.getenv("JAMENDO_CLIENT_ID","").strip()
if not CLIENT:raise SystemExit("Missing secret JAMENDO_CLIENT_ID")
SEED=2026111950
API="https://api.jamendo.com/v3.0/tracks/"
rng=random.Random(SEED)
def read_csv(path):
    with open(path,encoding="utf8",newline="") as f:return list(csv.DictReader(f))
catalog=read_csv("input/acoustic_features_joined.csv")
old1=read_csv("prior46/sample_manifest.csv")
old2=read_csv("prior47/catalog_random_400.csv")
exclude={r["track_id"] for r in old1+old2}
pool=sorted((r for r in catalog if r["track_id"] not in exclude),key=lambda r:int(r["track_id"]))
sample=rng.sample(pool,120)
rng.shuffle(sample)
panel={r["track_id"] for r in rng.sample(sample,24)}
def cohort(r):
    e=r["experimental"]=="1";l=r["electronic"]=="1"
    return "both" if e and l else "experimental_only" if e else "electronic_only" if l else "other"
manifest=[{"track_id":r["track_id"],"artist_id":r["artist_id"],"cohort":cohort(r),"single_panel":int(r["track_id"] in panel)} for r in sample]
blocks=[[r["track_id"] for r in sample[j:j+20]] for j in range(0,120,20)]
assert all(len(b)==20 for b in blocks)
with (OUT/"sample_manifest.csv").open("w",newline="",encoding="utf8") as f:
    w=csv.DictWriter(f,fieldnames=list(manifest[0]));w.writeheader();w.writerows(manifest)
obs=[];headers=[];failures=[]
def fetch(ids,order):
    args={"client_id":CLIENT,"format":"json","id":" ".join(ids),
          "type":"single albumtrack","limit":200,"include":"stats"}
    if order:args["order"]="id_asc"
    url=API+"?"+urllib.parse.urlencode(args)
    req=urllib.request.Request(url,headers={"User-Agent":"CORPACIAO-research-retrieval-crossover/5.0"})
    with urllib.request.urlopen(req,timeout=40) as resp:result=json.load(resp)
    h=result.get("headers",{})
    if h.get("status")!="success" or str(h.get("code"))!="0":
        raise ValueError("Jamendo API error "+str(h.get("code"))+" "+str(h.get("error_message"))[:120])
    rows=result.get("results")
    if not isinstance(rows,list):raise ValueError("Missing results array")
    mapped={}
    for row in rows:
        tid=str(row.get("id"))
        if tid not in ids or tid in mapped:raise ValueError("Unexpected/duplicated response ID")
        st=row.get("stats")
        mapped[tid]={"stats_present":int(isinstance(st,dict)),
                     "rate_listened_total":st.get("rate_listened_total") if isinstance(st,dict) else None}
    return mapped,{"api_results_count":h.get("results_count"),"warnings":str(h.get("warnings",""))[:500]}
def run(ids,cycle,block,method):
    result=None;err=None;meta={}
    for retry in range(3):
        try:
            result,meta=fetch(ids,method=="sorted20")
            break
        except (TimeoutError,ValueError,urllib.error.URLError) as exc:
            err=f"{type(exc).__name__}: {exc}"[:240]
            if retry<2:time.sleep(1+retry)
    headers.append({"cycle":cycle,"block":block,"method":method,"requested":len(ids),
                    "returned":len(result) if result is not None else None,**meta})
    if result is None:failures.append({"cycle":cycle,"block":block,"method":method,"error":err})
    for t in ids:
        value=result.get(t) if result is not None else None
        obs.append({"cycle":cycle,"block":block,"method":method,"track_id":t,
                    "status":"api_error" if result is None else "returned" if value is not None else "not_returned",
                    "stats_present":value["stats_present"] if value is not None else "",
                    "rate_listened_total":value["rate_listened_total"] if value is not None else ""})
    time.sleep(.25)
# Opposite per-block arm orders, with cycle-2 reversal, to reduce time confounding.
for cycle in (1,2):
    sequence=list(range(6))
    rng.shuffle(sequence)
    for block_id in sequence:
        batch=blocks[block_id]
        arms=["sorted20","unsorted20"] if (block_id+cycle)%2==0 else ["unsorted20","sorted20"]
        for arm in arms:run(batch,cycle,block_id,arm)
    singles=sorted(panel,key=int);rng.shuffle(singles)
    for t in singles:run([t],cycle,-1,"single")
    print("Completed cycle",cycle,flush=True)
with (OUT/"observations.csv").open("w",newline="",encoding="utf8") as f:
    fields=["cycle","block","method","track_id","status","stats_present","rate_listened_total"]
    w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(obs)
(OUT/"request_metadata.json").write_text(json.dumps(headers,indent=2),encoding="utf8")
def rowmap(method,cycle):return {r["track_id"]:r for r in obs if r["cycle"]==cycle and r["method"]==method}
summaries=[];repeat=[]
for arm in ["sorted20","unsorted20","single"]:
    rows=[r for r in obs if r["method"]==arm]
    valid=[r for r in rows if r["status"]!="api_error"]
    returned=[r for r in valid if r["status"]=="returned"]
    a=rowmap(arm,1);b=rowmap(arm,2)
    common=set(a)&set(b)
    comparable=[k for k in common if a[k]["status"]!="api_error" and b[k]["status"]!="api_error"]
    summaries.append({"method":arm,"valid_track_observations":len(valid),
                      "returned":len(returned),"fraction_returned":round(len(returned)/len(valid),5) if valid else None,
                      "unique_returned":len({r["track_id"] for r in returned})})
    repeat.append({"method":arm,"comparable":len(comparable),
                   "same_return_status":sum(a[k]["status"]==b[k]["status"] for k in comparable)})
def pair(cycle):
    x=rowmap("sorted20",cycle);y=rowmap("unsorted20",cycle)
    counter=collections.Counter()
    for k in x:
        if x[k]["status"]=="api_error" or y[k]["status"]=="api_error":continue
        counter[(x[k]["status"],y[k]["status"])]+=1
    return {"cycle":cycle,**{"sorted_and_unsorted":counter[("returned","returned")],
      "sorted_only":counter[("returned","not_returned")],
      "unsorted_only":counter[("not_returned","returned")],
      "neither":counter[("not_returned","not_returned")]}}
changes={}
for arm in ["sorted20","unsorted20","single"]:
    grouped=collections.defaultdict(set)
    for r in obs:
        if r["method"]==arm and r["status"]=="returned" and r["rate_listened_total"]!="":
            grouped[r["track_id"]].add(str(r["rate_listened_total"]))
    changes[arm]=sum(len(vals)>1 for vals in grouped.values())
report={"release":"5.0","status":"COMPLETE" if not failures else "PARTIAL_API_ERRORS",
        "timestamp_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "sampling":"fresh simple random 120 tracks from full feature-joined catalog, excluding the 4.6 and 4.7 samples",
        "catalog_rows":len(catalog),"excluded_previous_track_ids":len(exclude),
        "seed":SEED,"sampled":len(sample),"single_panel":len(panel),
        "request_params":"both track types; include stats; limit 200; <=20 IDs per batch",
        "method_summaries":summaries,"within_method_repeatability":repeat,
        "paired_comparison":[pair(1),pair(2)],"rate_value_changes":changes,
        "failed_requests":failures,"request_headers_observed":len(headers),
        "methodology_limits":["The two request configurations remain sequential; order is balanced across six blocks and reversed between cycles.",
          "Single-ID observations are a prespecified 24-track subpanel, not an independent random catalog sample.",
          "No missing observation is treated as zero listens; rate_listened_total definition and historical comparability unverified.",
          "No popularity-driven recommendations tested."]}
(OUT/"REPORT_50.json").write_text(json.dumps(report,indent=2),encoding="utf8")
print(json.dumps(report,indent=2))
if failures:raise SystemExit("Some API requests failed; inspect partial report")
