#!/usr/bin/env python3
"""CORPACIAO 6.0: independent acoustic metric benchmark, 800 fixed 5.9 queries.

Controlled comparisons: standardized cosine (5.9 reconstruction), z-Euclidean,
z-Manhattan, train-only robust-scaled cosine, uniformly random catalogue.
No popularity measurements and no new Jamendo API requests.
"""
import csv,collections,hashlib,json,math,random,pathlib,os,datetime
os.environ["OPENBLAS_NUM_THREADS"]="1";os.environ["OMP_NUM_THREADS"]="1"
import numpy as np
from scipy.spatial.distance import cdist
from audit_cohorts import split
from extract_acoustic_features import FEATURE_COLUMNS
ROOT=pathlib.Path("benchmark_60");ROOT.mkdir(exist_ok=True)
SRC=pathlib.Path("input/acoustic_features_joined.csv")
OLD=pathlib.Path("prior59/per_query_full28.csv")
with OLD.open(newline="",encoding="utf-8") as f:original=list(csv.DictReader(f))
assert len(original)==800
qids=[r["query_track"] for r in original]
assert len(set(qids))==800
def coh(r):
    e=r["experimental"]=="1";l=r["electronic"]=="1"
    return "both" if e and l else "experimental_only" if e else "electronic_only" if l else "other"
records=[]
with SRC.open(newline="",encoding="utf-8") as f:
    for row in csv.DictReader(f):
        values=[float(row[k]) for k in FEATURE_COLUMNS]
        if not all(math.isfinite(x) for x in values):raise ValueError("Nonfinite")
        records.append({"track":row["track_id"],"artist":row["artist_id"],"tags":frozenset(x for x in row["genre_tags"].split("|") if x),"cohort":coh(row),"split":split(row["artist_id"],314159),"features":values})
assert len(records)==55213
byid={r["track"]:r for r in records}
train=sorted((r for r in records if r["split"]=="train"),key=lambda x:int(x["track"]))
qs=[byid[t] for t in qids]
assert all(r["split"]=="test" for r in qs)
assert not ({r["artist"] for r in train}&{r["artist"] for r in qs})
assert all(q["cohort"]==o["cohort"] for q,o in zip(qs,original))
X=np.asarray([r["features"] for r in train],np.float32)
Q=np.asarray([r["features"] for r in qs],np.float32)
mean=X.mean(0);sd=X.std(0)
assert np.all(sd>1.e-10)
Z=np.clip((X-mean)/sd,-20,20)
T=np.clip((Q-mean)/sd,-20,20)
med=np.median(X,axis=0);q25=np.percentile(X,25,axis=0);q75=np.percentile(X,75,axis=0)
iqr=np.maximum(q75-q25,1.e-8)
R=np.clip((X-med)/iqr,-20,20)
U=np.clip((Q-med)/iqr,-20,20)
def norm(a):
    return a/np.maximum(np.linalg.norm(a,axis=1,keepdims=True),1.e-12)
def build(name):
    if name=="cosine_z":
        A=norm(Z);B=norm(T)
    elif name=="cosine_robust":
        A=norm(R);B=norm(U)
    else:A=B=None
    rng=random.Random(606000)
    outputs=[]
    for start in range(0,len(qs),20):
        end=min(start+20,len(qs))
        if name in ("cosine_z","cosine_robust"):
            dist=-(B[start:end]@A.T)
        elif name=="euclidean_z":
            dist=cdist(T[start:end],Z,metric="sqeuclidean")
        elif name=="manhattan_z":
            dist=cdist(T[start:end],Z,metric="cityblock")
        elif name=="uniform_random":
            dist=None
        else:raise ValueError(name)
        for k,q in enumerate(qs[start:end]):
            if name=="uniform_random":
                ix=rng.sample(range(len(train)),10)
            else:
                d=dist[k]
                ix=np.argpartition(d,9)[:10]
                ix=sorted(ix,key=lambda i:(float(d[i]),int(train[i]["track"])))
            chosen=[train[i] for i in ix]
            assert len({r["track"] for r in chosen})==10
            assert not any(r["artist"]==q["artist"] for r in chosen)
            agree=sum(bool(q["tags"]&r["tags"]) for r in chosen)
            outputs.append({"query_track":q["track"],"query_artist":q["artist"],"cohort":q["cohort"],
                            "shared_hits":agree,"genre_agreement":agree/10,
                            "distinct_artists":len({r["artist"] for r in chosen}),
                            "top10":"|".join(r["track"] for r in chosen),
                            "top10_artists":"|".join(r["artist"] for r in chosen)})
    return outputs
models=["cosine_z","euclidean_z","manhattan_z","cosine_robust","uniform_random"]
results={name:build(name) for name in models}
# A hard internal audit, not an assumption that prior artifact is identical.
matched=0
for old,new in zip(original,results["cosine_z"]):
    if old["top10"]==new["top10"]:matched+=1
# Do not silently claim reconstruction if numerical implementation differs.
for name,rows in results.items():
    with (ROOT/f"per_query_{name}.csv").open("w",encoding="utf8",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
def describe(name):
    rows=results[name]
    counts=collections.Counter(a for r in rows for a in r["top10_artists"].split("|"))
    top100=sum(v for _,v in counts.most_common(100))/(len(rows)*10)
    baseline=results["cosine_z"]
    overlap=np.mean([len(set(x["top10"].split("|"))&set(y["top10"].split("|")))/10 for x,y in zip(rows,baseline)])
    return {"model":name,"mean_any_shared_genre":round(float(np.mean([r["genre_agreement"] for r in rows])),5),
      "mean_distinct_artists_per_list":round(float(np.mean([r["distinct_artists"] for r in rows])),4),
      "unique_exposed_artists":len(counts),
      "top100_artist_exposure_fraction":round(top100,5),
      "top10_overlap_with_cosine_z":round(float(overlap),5),
      "cohort_agreement":{co:round(float(np.mean([r["genre_agreement"] for r in rows if r["cohort"]==co])),5)
                        for co in ["experimental_only","electronic_only","both","other"]}}
summary=[describe(name) for name in models]
artists=sorted({r["artist"] for r in qs})
indices=collections.defaultdict(list)
for i,r in enumerate(qs):indices[r["artist"]].append(i)
boot=random.Random(606009)
interval={}
for name in models[1:]:
    diff=np.asarray([a["genre_agreement"]-b["genre_agreement"] for a,b in zip(results[name],results["cosine_z"])])
    sampled=[]
    for iteration in range(1500):
        chosen=[boot.choice(artists) for _ in artists]
        idx=[i for artist in chosen for i in indices[artist]]
        sampled.append(float(np.mean(diff[idx]))*100)
    interval[name]={"paired_mean_pp":round(float(diff.mean()*100),3),
       "artist_cluster_bootstrap_95_pp":[round(float(v),3) for v in np.quantile(sampled,[.025,.975])]}
# Exact fixed-query expected random agreement from training catalogue, not a monte carlo surrogate.
expected=np.mean([sum(bool(q["tags"]&r["tags"]) for r in train)/len(train) for q in qs])
report={"release":"6.0","status":"COMPLETE",
 "input_sha256":hashlib.sha256(SRC.read_bytes()).hexdigest(),
 "query_artifact_sha256":hashlib.sha256(OLD.read_bytes()).hexdigest(),
 "training_tracks":len(train),"query_tracks":len(qs),"query_artists":len(artists),
 "same_order_query_ids_as_59":True,"cosine_z_identical_top10_lists_vs_59":matched,
 "cosine_z_top10_lists_total":len(qs),
 "fixed_query_uniform_expected_agreement":round(float(expected),6),
 "models":summary,"paired_cluster_intervals":interval,
 "algorithm":"exact top10; clip [-20,20], train-only scaling; Euclidean/Manhattan unnormalized after z-scoring; cosine uses row-normalized vectors; uniform catalogue sample has no user-history filtering",
 "notes":["800 stratified fixed queries; not the historical full 4.1 test cohort.",
          "Shared genre labels are proxy annotations, not human relevance.",
          "Uniform random is a sanity comparator, not a competitive recommender.",
          "Popularity signals were not accessed or estimated.","Metric comparisons are exploratory, with no test tuning."]}
(ROOT/"BENCHMARK_60_REPORT.json").write_text(json.dumps(report,indent=2),encoding="utf8")
with (ROOT/"MODEL_SUMMARY.csv").open("w",newline="",encoding="utf8") as f:
    cols=["model","mean_any_shared_genre","mean_distinct_artists_per_list","unique_exposed_artists","top100_artist_exposure_fraction","top10_overlap_with_cosine_z"]
    w=csv.DictWriter(f,fieldnames=cols);w.writeheader()
    for r in summary:w.writerow({c:r[c] for c in cols})
print(json.dumps(report,indent=2),flush=True)
