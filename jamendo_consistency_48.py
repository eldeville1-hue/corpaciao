#!/usr/bin/env python3
"""CORPACIAO 4.8: controlled, paired Jamendo API retrieval consistency study.

Select fixed IDs from 4.7 typed/untyped recheck. Query the SAME IDs as
single, batches of 5, and batches of 20, twice in alternating order.
No missing observation is reinterpreted as zero listens.
"""
import collections,csv,datetime,json,math,os,pathlib,random,time,urllib.parse,urllib.request,urllib.error
ROOT=pathlib.Path("consistency_48");ROOT.mkdir(exist_ok=True)
CLIENT=os.getenv("JAMENDO_CLIENT_ID","").strip()
if not CLIENT:raise SystemExit("Missing GitHub Actions secret JAMENDO_CLIENT_ID")
BASE="https://api.jamendo.com/v3.0/tracks/"
SEED=2026111948
rng=random.Random(SEED)
def read(name):
    with open("prior47/"+name,newline="",encoding="utf8") as f:return {r["track_id"]:r for r in csv.DictReader(f)}
typed=read("prior_missing_typed.csv")
untyped=read("prior_missing_untyped.csv")
groups=collections.defaultdict(list)
for k,t in typed.items():
    u=untyped.get(k)
    if not u:raise ValueError("Prior check missing ID "+k)
    key=t["status"]+"|"+u["status"]
    if "api_error" in key:raise ValueError("Prior sample contained API errors")
    groups[key].append(k)
# Stable, predeclared allocation: 20 persistent; all 22 discordant; 18 recovered in both.
target={"not_returned|not_returned":20,"not_returned|returned":12,
        "returned|not_returned":10,"returned|returned":18}
selected=[]
for group,count in target.items():
    pool=sorted(groups[group],key=int)
    if len(pool)<count:raise ValueError(f"Too few IDs {group}: {len(pool)} < {count}")
    selected.extend({"track_id":k,"prior_class":group,"cohort":typed[k]["cohort"]} for k in rng.sample(pool,count))
selected.sort(key=lambda x:int(x["track_id"]))
ids=[x["track_id"] for x in selected]
def call(batch,typed_filter):
    params={"client_id":CLIENT,"format":"json","id":" ".join(batch),
            "limit":max(1,len(batch)),"include":"stats"}
    if typed_filter:params["type"]="single albumtrack"
    req=urllib.request.Request(BASE+"?"+urllib.parse.urlencode(params),
         headers={"User-Agent":"CORPACIAO-controlled-retrieval-consistency/4.8"})
    with urllib.request.urlopen(req,timeout=35) as f:obj=json.load(f)
    h=obj.get("headers",{})
    if h.get("status")!="success" or str(h.get("code"))!="0":
        raise RuntimeError("Jamendo response "+str(h.get("code"))+" "+str(h.get("error_message"))[:90])
    rows=obj.get("results")
    if not isinstance(rows,list):raise ValueError("No result list")
    returned={}
    for x in rows:
        tid=str(x.get("id"))
        if tid not in batch or tid in returned:raise ValueError("Unexpected or duplicated returned ID")
        st=x.get("stats")
        returned[tid]={"stats_present":int(isinstance(st,dict)),
           "rate_listened_total":st.get("rate_listened_total") if isinstance(st,dict) else "",
           "rate_downloads_total":st.get("rate_downloads_total") if isinstance(st,dict) else ""}
    return returned
records=[];batch_errors=[]
# First cycle small->large, second reverse, to reduce order/time confounding.
for cycle,settings in enumerate([[(1,False),(5,False),(20,False),(5,True),(20,True)],
                                  [(20,True),(5,True),(20,False),(5,False),(1,False)]],1):
    for size,typ in settings:
        shuffled=ids[:] 
        rng.shuffle(shuffled)
        for start in range(0,len(shuffled),size):
            group=shuffled[start:start+size]
            payload=None;error=""
            for attempt in range(3):
                try:
                    payload=call(group,typ);break
                except (urllib.error.URLError,TimeoutError,ValueError,RuntimeError) as e:
                    error=type(e).__name__+": "+str(e)[:160]
                    if attempt<2:time.sleep(1+attempt)
            if payload is None:batch_errors.append({"cycle":cycle,"batch_size":size,"typed":typ,
                                                    "batch_index":start//size,"error":error})
            for k in group:
                observed=payload.get(k,{}) if payload is not None else {}
                records.append({"track_id":k,"cycle":cycle,"batch_size":size,
                   "type_filter":int(typ),"status":"api_error" if payload is None else (
                       "returned" if k in payload else "not_returned"),**observed})
            time.sleep(.16)
    print("Completed cycle",cycle,flush=True)
with (ROOT/"retrieval_observations.csv").open("w",newline="",encoding="utf8") as f:
    fields=["track_id","cycle","batch_size","type_filter","status","stats_present",
            "rate_listened_total","rate_downloads_total"]
    w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(records)
with (ROOT/"sample_manifest.csv").open("w",newline="",encoding="utf8") as f:
    w=csv.DictWriter(f,fieldnames=["track_id","prior_class","cohort"]);w.writeheader();w.writerows(selected)
metrics=[]
for size,typ in [(1,False),(5,False),(20,False),(5,True),(20,True)]:
    row=[x for x in records if x["batch_size"]==size and x["type_filter"]==int(typ)]
    valid=[x for x in row if x["status"]!="api_error"]
    returned=[x for x in valid if x["status"]=="returned"]
    metrics.append({"batch_size":size,"type_filter":typ,"requests_over_two_cycles":len(row)//size,
            "track_observations":len(row),"valid_observations":len(valid),
            "returned":len(returned),
            "fraction_returned":round(len(returned)/len(valid),4) if valid else None})
def by_key(size,typ,cycle):
    return {x["track_id"]:x for x in records if x["batch_size"]==size and x["type_filter"]==int(typ) and x["cycle"]==cycle}
single=by_key(1,False,1)
pairs=[]
for size,typ in [(5,False),(20,False),(5,True),(20,True)]:
    other=by_key(size,typ,1)
    a=b=c=d=0
    for k in ids:
        x=single[k]["status"];y=other[k]["status"]
        if "api_error" in (x,y):continue
        if x=="returned" and y=="returned":a+=1
        elif x=="returned":b+=1
        elif y=="returned":c+=1
        else:d+=1
    pairs.append({"compare_to":"single_no_filter_cycle_1","batch_size":size,"type_filter":typ,
          "both_return":a,"single_only":b,"batch_only":c,"neither":d})
report={"release":"4.8","timestamp_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
  "selected_unique_tracks":len(ids),"previous_status_class_counts":dict(collections.Counter(r["prior_class"] for r in selected)),
  "selection_seed":SEED,"per_setting_summary":metrics,"paired_cycle1":pairs,
  "failed_api_batches":batch_errors,"two_cycles":True,
  "notes":["The sample is deliberately enriched for previously missing/discordant records and does not estimate catalog coverage.",
           "Comparisons are paired within track IDs, but request sequence and time effects remain possible.",
           "Jamendo rate_listened_total is not asserted to be a raw listening count.",
           "No popularity-aware reranking performed."] }
(ROOT/"RETRIEVAL_CONSISTENCY.json").write_text(json.dumps(report,indent=2),encoding="utf8")
print(json.dumps(report,indent=2))
if batch_errors:raise SystemExit("One or more API batches failed; see report")
