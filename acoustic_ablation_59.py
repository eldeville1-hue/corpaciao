#!/usr/bin/env python3
"""CORPACIAO 5.9 — prespecified acoustic feature ablation.

Real MTG-Jamendo features; train-only standardization; artist-disjoint test.
This is a new controlled *cosine* benchmark, NOT reconstruction of 4.1 ranking
unless independently verified. No Jamendo API/popularity access.
"""
import csv,collections,hashlib,json,math,os,pathlib,random,datetime
os.environ["OPENBLAS_NUM_THREADS"]="1"
os.environ["OMP_NUM_THREADS"]="1"
import numpy as np
from audit_cohorts import split
from extract_acoustic_features import FEATURE_COLUMNS
SEED=2026112959
ROOT=pathlib.Path("ablation_59");ROOT.mkdir(exist_ok=True)
SRC=pathlib.Path("input/acoustic_features_joined.csv")
def coh(r):
    e=r["experimental"]=="1";l=r["electronic"]=="1"
    return "both" if e and l else "experimental_only" if e else "electronic_only" if l else "other"
records=[]
with SRC.open(newline="",encoding="utf-8") as f:
    for r in csv.DictReader(f):
        vals=[float(r[k]) for k in FEATURE_COLUMNS]
        if not all(math.isfinite(x) for x in vals):raise ValueError("Invalid feature vector")
        records.append({"track":r["track_id"],"artist":r["artist_id"],"split":split(r["artist_id"],314159),
          "tags":frozenset(x for x in r["genre_tags"].split("|") if x),"cohort":coh(r),"values":vals})
if len(records)!=55213:raise ValueError(f"Unexpected tracks {len(records)}")
by_split=collections.Counter(r["split"] for r in records)
train=[r for r in records if r["split"]=="train"]
test=[r for r in records if r["split"]=="test"]
print("SPLITS",dict(by_split),flush=True)
if len(train)<30000 or len(test)<6000:raise ValueError("Unexpected split")
if set(x["artist"] for x in train)&set(x["artist"] for x in test):raise ValueError("Artist leakage")
rng=random.Random(SEED)
by_cohort=collections.defaultdict(list)
for r in test:by_cohort[r["cohort"]].append(r)
quotas={"experimental_only":100,"electronic_only":200,"both":100,"other":400}
queries=[]
for k,q in quotas.items():
    if len(by_cohort[k])<q:raise ValueError(f"Insufficient {k}")
    queries.extend(rng.sample(by_cohort[k],q))
rng.shuffle(queries)
if len({r["track"] for r in queries})!=800:raise ValueError("Duplicate query")
train_x=np.asarray([r["values"] for r in train],dtype=np.float32)
test_x=np.asarray([r["values"] for r in queries],dtype=np.float32)
means=train_x.mean(0);sd=train_x.std(0)
if (sd<1e-10).any():raise ValueError("Constant features")
train_z=np.clip((train_x-means)/sd,-20,20)
query_z=np.clip((test_x-means)/sd,-20,20)
corr=np.corrcoef(train_z.T)
retain=[]
pruned=[]
for i in range(len(FEATURE_COLUMNS)):
    strongly=[j for j in retain if abs(corr[i,j])>0.95]
    if strongly:pruned.append({"removed":FEATURE_COLUMNS[i],"correlated_with":FEATURE_COLUMNS[strongly[0]],"train_abs_r":round(float(abs(corr[i,strongly[0]])),6)})
    else:retain.append(i)
groups={"lowlevel":[i for i,k in enumerate(FEATURE_COLUMNS) if k.startswith("lowlevel__")],
        "rhythm":[i for i,k in enumerate(FEATURE_COLUMNS) if k.startswith("rhythm__")],
        "tonal":[i for i,k in enumerate(FEATURE_COLUMNS) if k.startswith("tonal__")]}
if any(not v for v in groups.values()):raise ValueError("Empty feature group")
def weights(name):
    w=np.zeros(len(FEATURE_COLUMNS),dtype=np.float32)
    if name=="full28":w[:]=1
    elif name=="correlation_pruned":w[retain]=1
    elif name=="equal_group_weights":
        for idx in groups.values():w[idx]=1/math.sqrt(len(idx))
    elif name in groups:w[groups[name]]=1
    else:raise ValueError(name)
    return w
def normalize(x):
    norm=np.linalg.norm(x,axis=1,keepdims=True)
    return x/np.maximum(norm,1e-12)
def estimate(name):
    w=weights(name)
    a=normalize(train_z*w);b=normalize(query_z*w)
    # Exact cosine nearest neighbors, 50-query chunks, deterministic ties by track ID.
    score_names=np.array([int(r["track"]) for r in train])
    order=np.argsort(score_names,kind="stable")
    a=a[order]
    train_ordered=[train[j] for j in order]
    output=[]
    for offset in range(0,len(b),50):
        cosine=b[offset:offset+50] @ a.T
        for local,one in enumerate(cosine):
            i=offset+local
            # Query-artist exclusion even though split should ensure it.
            matches=np.argpartition(-one,9)[:10]
            matches=sorted(matches,key=lambda idx:(-float(one[idx]),int(train_ordered[idx]["track"])))
            q=queries[i]
            same=[int(bool(q["tags"]&train_ordered[t]["tags"])) for t in matches]
            artists=[train_ordered[t]["artist"] for t in matches]
            output.append({"query_track":q["track"],"query_artist":q["artist"],
                "cohort":q["cohort"],"agreement":sum(same)/10,
                "diversity":len(set(artists)),"top10":"|".join(train_ordered[t]["track"] for t in matches),
                "shared_hits":sum(same)})
    return output
names=["full28","correlation_pruned","equal_group_weights","lowlevel","rhythm","tonal"]
results={name:estimate(name) for name in names}
for name,rows in results.items():
    with (ROOT/f"per_query_{name}.csv").open("w",newline="",encoding="utf8") as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
baseline=results["full28"]
def metrics(name):
    rows=results[name]
    exposure=collections.Counter(t for r in rows for t in r["top10"].split("|"))
    overlap=np.mean([len(set(x["top10"].split("|"))&set(y["top10"].split("|")))/10 for x,y in zip(rows,baseline)])
    return {"model":name,"feature_count":int(np.count_nonzero(weights(name))),
        "shared_genre_agreement":round(float(np.mean([r["agreement"] for r in rows])),5),
        "distinct_artists_per_list":round(float(np.mean([r["diversity"] for r in rows])),5),
        "top10_overlap_with_full28":round(float(overlap),5),
        "cohorts":{c:round(float(np.mean([r["agreement"] for r in rows if r["cohort"]==c])),5) for c in quotas}}
summary=[metrics(x) for x in names]
# Cluster bootstrap paired difference by query artist, no test-data tuning.
artists=sorted({r["artist"] for r in queries})
indices=collections.defaultdict(list)
for j,r in enumerate(queries):indices[r["artist"]].append(j)
boot=random.Random(202611295901)
intervals={}
for name in names[1:]:
    diff=np.asarray([r["agreement"]-base["agreement"] for r,base in zip(results[name],baseline)])
    draws=[]
    for iteration in range(1000):
        sampled=[boot.choice(artists) for _ in artists]
        idx=[j for artist in sampled for j in indices[artist]]
        draws.append(float(np.mean(diff[idx])))
    intervals[name]={"paired_mean_pp":round(float(diff.mean()*100),3),
       "artist_cluster_bootstrap_95_pp":[round(float(v)*100,3) for v in np.quantile(draws,[.025,.975])]}
hashval=hashlib.sha256(SRC.read_bytes()).hexdigest()
report={"release":"5.9","status":"COMPLETE","input_sha256":hashval,
  "tracks":len(records),"artist_disjoint_splits":dict(by_split),"sample_test_queries":len(queries),
  "sampling_seed":SEED,"sampled_cohort_sizes":quotas,"train_artists":len({x["artist"] for x in train}),
  "query_artists":len(artists),"feature_count":len(FEATURE_COLUMNS),
  "pruned_count":len(pruned),"pruned_feature_pairs":pruned,
  "groups":{k:len(v) for k,v in groups.items()},
  "algorithm":"train-only z-score clipping [-20,20], unit-normalized weighted features, exact cosine top10",
  "models":summary,"paired_artist_cluster_intervals":intervals,
  "interpretation":["This is a new stratified query sample, not the full Release 4.1 8549-query benchmark.",
    "Equal-group weighting changes geometry; all ablations use same sampled queries and candidate set.",
    "No baseline matching claim against the historical 4.1 report without independent reconstruction.",
    "Genre agreement is label overlap, not human relevance; artist exposure is not popularity.",
    "No Jamendo API usage or popularity inference."]}
(ROOT/"ABLATION_59_REPORT.json").write_text(json.dumps(report,indent=2),encoding="utf8")
with (ROOT/"MODEL_SUMMARY.csv").open("w",newline="",encoding="utf8") as f:
    cols=["model","feature_count","shared_genre_agreement","distinct_artists_per_list","top10_overlap_with_full28"]
    w=csv.DictWriter(f,fieldnames=cols);w.writeheader();w.writerows({k:r[k] for k in cols} for r in summary)
print(json.dumps({"status":"COMPLETE","models":summary,"intervals":intervals},indent=2),flush=True)
