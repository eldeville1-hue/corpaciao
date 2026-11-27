#!/usr/bin/env python3
"""CORPACIAO 6.1: label-supervised ridge content model and numerical mismatch audit.
A train-genre-supervised model is scored on genre agreement: this intentionally
measures label retrieval, NOT an independent recommendation relevance benchmark.
"""
import csv,json,hashlib,collections,math,pathlib,random,os
os.environ["OPENBLAS_NUM_THREADS"]="1";os.environ["OMP_NUM_THREADS"]="1"
import numpy as np
from sklearn.linear_model import Ridge
from audit_cohorts import split
from extract_acoustic_features import FEATURE_COLUMNS
OUT=pathlib.Path("research61");OUT.mkdir(exist_ok=True)
def load(p):
    with open(p,encoding="utf-8",newline="") as f:return list(csv.DictReader(f))
old=load("prior59/per_query_full28.csv")
cos=load("prior60/per_query_cosine_z.csv")
assert len(old)==len(cos)==800
assert [r["query_track"] for r in old]==[r["query_track"] for r in cos]
mismatch=[]
for a,b in zip(old,cos):
    aa=a["top10"].split("|");bb=b["top10"].split("|")
    if aa!=bb:
        mismatch.append({"query_track":a["query_track"],"query_artist":a["query_artist"],
                          "first_disagree_rank":next(i+1 for i,(u,v) in enumerate(zip(aa,bb)) if u!=v),
                          "original_top10":aa,"recomputed_top10":bb,
                          "same_set":set(aa)==set(bb)})
data=load("input/acoustic_features_joined.csv")
assert len(data)==55213
byid={r["track_id"]:r for r in data}
train=[r for r in data if split(r["artist_id"],314159)=="train"]
dev=[r for r in data if split(r["artist_id"],314159)=="development"]
query=[byid[r["query_track"]] for r in old]
assert len(train)==38200 and len(dev)==8464
assert all(split(r["artist_id"],314159)=="test" for r in query)
trainartists={r["artist_id"] for r in train}
devartists={r["artist_id"] for r in dev}
testartists={r["artist_id"] for r in query}
assert not (trainartists&devartists or trainartists&testartists or devartists&testartists)
def matrix(rows):
    v=np.asarray([[float(r[k]) for k in FEATURE_COLUMNS] for r in rows],dtype=np.float64)
    assert np.isfinite(v).all()
    return v
X=matrix(train);D=matrix(dev);Q=matrix(query)
mu=X.mean(axis=0);sd=X.std(axis=0)
assert np.all(sd>1.e-10)
trainz=np.clip((X-mu)/sd,-20,20)
devz=np.clip((D-mu)/sd,-20,20)
testz=np.clip((Q-mu)/sd,-20,20)
tags=sorted({x for r in train for x in r["genre_tags"].split("|") if x})
print("Number of train tags",len(tags),flush=True)
tag_index={x:i for i,x in enumerate(tags)}
def labels(rows):
    Y=np.zeros((len(rows),len(tags)),dtype=np.float32)
    for i,r in enumerate(rows):
        for tag in r["genre_tags"].split("|"):
            if tag in tag_index:Y[i,tag_index[tag]]=1
    return Y
Y=labels(train)
YD=labels(dev)
YQ=labels(query)
# Freeze a small dev-only alpha sweep by optimizing mean average precision
# of tag prediction (not recommendation outcomes).
alphas=[100.0,1000.0,10000.0]
dev_scores=[]
for alpha in alphas:
    model=Ridge(alpha=alpha)
    model.fit(trainz,Y)
    pred=np.clip(model.predict(devz),0,1)
    # macro across queried tracks: recall@5 of true tags, without tuning on test.
    top=np.argpartition(-pred,4,axis=1)[:,:5]
    recall=sum(np.sum(YD[i,top[i]])/max(1,np.sum(YD[i])) for i in range(len(dev)))
    dev_scores.append({"alpha":alpha,"mean_true_genre_recall_at_5":round(float(recall/len(dev)),6)})
chosen=max(dev_scores,key=lambda x:(x["mean_true_genre_recall_at_5"],-x["alpha"]))["alpha"]
model=Ridge(alpha=chosen).fit(trainz,Y)
P=np.clip(model.predict(trainz),0,1).astype(np.float32)
T=np.clip(model.predict(testz),0,1).astype(np.float32)
# Positive predictions only, then row L2 normalization. Keep training label labels only for evaluation.
def norm(arr):return arr/np.maximum(np.linalg.norm(arr,axis=1,keepdims=True),1.e-9)
P=norm(P);T=norm(T)
order=np.argsort(np.asarray([int(r["track_id"]) for r in train]))
P=P[order];sortedtrain=[train[i] for i in order]
result=[]
for pos in range(0,len(query),20):
    sims=T[pos:pos+20]@P.T
    for i,sc in enumerate(sims):
        qi=pos+i; r=query[qi]
        ids=np.argpartition(-sc,9)[:10]
        ids=sorted(ids,key=lambda x:(-float(sc[x]),int(sortedtrain[x]["track_id"])))
        rec=[sortedtrain[x] for x in ids]
        assert len({x["track_id"] for x in rec})==10
        assert all(x["artist_id"]!=r["artist_id"] for x in rec)
        qtags=set(r["genre_tags"].split("|"))
        hits=sum(bool(qtags&set(x["genre_tags"].split("|"))) for x in rec)
        result.append({"query_track":r["track_id"],"query_artist":r["artist_id"],
          "cohort":old[qi]["cohort"],"shared_hits":hits,"genre_agreement":hits/10,
          "distinct_artists":len({x["artist_id"] for x in rec}),
          "top10":"|".join(x["track_id"] for x in rec),
          "top10_artists":"|".join(x["artist_id"] for x in rec)})
with (OUT/"per_query_supervised_ridge.csv").open("w",encoding="utf8",newline="") as f:
    writer=csv.DictWriter(f,fieldnames=list(result[0]));writer.writeheader();writer.writerows(result)
baseagreement=np.asarray([float(x["genre_agreement"]) for x in cos])
learnedagreement=np.asarray([float(x["genre_agreement"]) for x in result])
diff=learnedagreement-baseagreement
cohorts=["experimental_only","electronic_only","both","other"]
metrics={}
for cohort in cohorts:
    indices=[i for i,r in enumerate(result) if r["cohort"]==cohort]
    metrics[cohort]={"queries":len(indices),"supervised_agreement":round(float(learnedagreement[indices].mean()),5),
                   "cosine_agreement":round(float(baseagreement[indices].mean()),5),
                   "difference_pp":round(float(diff[indices].mean()*100),3)}
artists=sorted(set(r["artist_id"] for r in query))
byartist=collections.defaultdict(list)
for i,r in enumerate(query):byartist[r["artist_id"]].append(i)
rng=random.Random(606101)
draws=[]
for j in range(1500):
    sampled=[rng.choice(artists) for _ in artists]
    ix=[i for a in sampled for i in byartist[a]]
    draws.append(float(np.mean(diff[ix])*100))
overlap=np.mean([len(set(x["top10"].split("|"))&set(y["top10"].split("|")))/10 for x,y in zip(result,cos)])
# Numerical reconstruction audit for discrepant track. Force double precision and compare
# score of listed candidates under two baseline train-order standardizations.
audit=[]
for m in mismatch:
    q=byid[m["query_track"]]
    qi=np.asarray([float(q[k]) for k in FEATURE_COLUMNS],dtype=np.float64)
    train_old=np.asarray([[float(r[k]) for k in FEATURE_COLUMNS] for r in train],np.float32)
    train_sorted=train_old[np.argsort(np.asarray([int(r["track_id"]) for r in train]))]
    for label,arr in [("train_file_order",train_old),("sorted_train_order",train_sorted)]:
        mm=arr.mean(0);ss=arr.std(0)
        qz=np.clip((qi.astype(np.float32)-mm)/ss,-20,20)
        qn=qz/max(float(np.linalg.norm(qz)),1.e-12)
        tr=np.clip((arr-mm)/ss,-20,20)
        tr/=np.maximum(np.linalg.norm(tr,axis=1,keepdims=True),1.e-12)
        score=tr@qn
        row=[train[i] for i in range(len(train))] if label=="train_file_order" else sortedtrain
        scores={x["track_id"]:float(score[i]) for i,x in enumerate(row) if x["track_id"] in set(m["original_top10"]+m["recomputed_top10"])}
        audit.append({"query_track":m["query_track"],"scaling_order":label,"candidate_scores":scores})
report={"release":"6.1","status":"COMPLETE","input_tracks":len(data),"train_tracks":len(train),"dev_tracks":len(dev),
        "test_queries":len(query),"disjoint_artists":True,"train_genre_tags":len(tags),
        "developer_only_alpha_selection":dev_scores,"selected_alpha":chosen,
        "learned_method":"Ridge regression genre-label predictions from acoustic features, trained on training artists only; selected regularization by development tag recall@5",
        "genre_agreement_target_also_used_in_supervision":True,
        "supervised_agreement":round(float(learnedagreement.mean()),5),
        "cosine_z_agreement":round(float(baseagreement.mean()),5),
        "paired_mean_pp":round(float(diff.mean()*100),3),
        "artist_bootstrap_95_pp":[round(float(v),3) for v in np.quantile(draws,[.025,.975])],
        "top10_overlap_with_cosine":round(float(overlap),5),
        "learned_mean_distinct_artists":round(float(np.mean([r["distinct_artists"] for r in result])),5),
        "per_cohort":metrics,"old_vs_new_cosine_discrepancies":mismatch,
        "cosine_discrepancy_count":len(mismatch),"cosine_discrepancy_score_audit":audit,
        "source_sha256":hashlib.sha256(pathlib.Path("input/acoustic_features_joined.csv").read_bytes()).hexdigest(),
        "limitations":["Genre-supervised label prediction evaluated by genre overlap: advantage is expected, not evidence of human relevance.",
          "No listener feedback, no popularity measurements, no Jamendo API requests.",
          "Exactly 800 fixed stratified queries shared with 5.9/6.0; exploratory comparison.",
          "Numerical stability investigation is diagnostic; do not infer the cause if score gaps inconclusive."]}
(OUT/"REPORT_61.json").write_text(json.dumps(report,indent=2),encoding="utf8")
with (OUT/"MODEL_SUMMARY.csv").open("w",newline="",encoding="utf8") as f:
    w=csv.writer(f);w.writerow(["model","genre_agreement","mean_distinct_artists","overlap_with_cosine"])
    w.writerow(["cosine_z",report["cosine_z_agreement"],"",1])
    w.writerow(["supervised_ridge",report["supervised_agreement"],report["learned_mean_distinct_artists"],report["top10_overlap_with_cosine"]])
print(json.dumps({k:v for k,v in report.items() if k not in ("cosine_discrepancy_score_audit",)},indent=2),flush=True)
