#!/usr/bin/env python3
"""CORPACIAO 6.2: independent-label transfer audit on frozen recommendations.

Instrument and mood/theme labels are official, separate MTG-Jamendo task annotations.
No new model training, no Jamendo API. This is cross-task annotation consistency,
NOT listener preference or an independent annotation source.
"""
import csv,json,hashlib,collections,random,pathlib,math,datetime
import numpy as np
from audit_cohorts import split
OUT=pathlib.Path("transfer62");OUT.mkdir(exist_ok=True)
PRIOR=pathlib.Path("prior60")
MODELS=["cosine_z","euclidean_z","manhattan_z","cosine_robust","uniform_random","supervised_ridge"]
files={m:(pathlib.Path("prior61/per_query_supervised_ridge.csv") if m=="supervised_ridge" else PRIOR/f"per_query_{m}.csv") for m in MODELS}
rows={}
for model,path in files.items():
    with path.open(newline="",encoding="utf-8") as f:rows[model]=list(csv.DictReader(f))
assert all(len(z)==800 for z in rows.values())
qids=[r["query_track"] for r in rows["cosine_z"]]
assert len(set(qids))==800
for model,z in rows.items():
    assert [r["query_track"] for r in z]==qids,model
    assert all(len(r["top10"].split("|"))==10 for r in z)
SOURCES={
 "instrument":("labels/autotagging_instrument.tsv","instrument---"),
 "moodtheme":("labels/autotagging_moodtheme.tsv","mood/theme---"),
}
# Parse official tsv: first 5 columns track, artist, album, path, duration; remaining labels.
def parse(path,prefix):
    annotations={};artists={}
    with open(path,encoding="utf-8-sig",newline="") as f:
        for i,parts in enumerate(csv.reader(f,delimiter="\t")):
            if not parts or parts[0].startswith("#") or parts[0].lower()=="track_id":continue
            if len(parts)<6:raise ValueError(f"Bad row {i}")
            tid=str(int(parts[0].removeprefix("track_")))
            if tid in annotations:raise ValueError("Duplicate track "+tid)
            # Retain exact task-specific tag prefix, strip only after prefix.
            tags=frozenset(s.strip().lower()[len(prefix):] for s in parts[5:] if s.strip().lower().startswith(prefix))
            annotations[tid]=tags
            artists[tid]=parts[1]
    return annotations,artists
D={};meta={}
for typ,(p,prefix) in SOURCES.items():
    tags,artists=parse(p,prefix)
    D[typ]=tags
    meta[typ]={"source":p,"sha256":hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest(),
               "records":len(tags),"nonempty_track_labels":sum(bool(v) for v in tags.values()),
               "unique_tags":len(set().union(*tags.values()))}
with open("input/acoustic_features_joined.csv",newline="",encoding="utf8") as f:
    catalog=list(csv.DictReader(f))
trainids={r["track_id"] for r in catalog if split(r["artist_id"],314159)=="train"}
assert len(trainids)==38200
test_lookup={r["track_id"]:r for r in catalog}
assert all(split(test_lookup[tid]["artist_id"],314159)=="test" for tid in qids)
# Align with query and recommendations, report absent/empty separately.
def score_one(model,typ,ann):
    result=[]
    for r in rows[model]:
        q=r["query_track"];ret=r["top10"].split("|")
        qt=ann.get(q,frozenset())
        annotated=int(q in ann)
        valid=int(bool(qt))
        positions=[ann.get(t,frozenset()) for t in ret]
        qualified=[(t,x) for t,x in zip(ret,positions) if qt and x]
        matched=sum(bool(qt&x) for _,x in qualified)
        result.append({"query_track":q,"query_artist":r["query_artist"],"cohort":r["cohort"],
            "query_annotation_present":annotated,"query_has_nonempty_labels":valid,
            "eligible_positions":len(qualified),"matched_positions":matched,
            "total_positions":10,"coverage_conditional_agreement":matched/len(qualified) if qualified else "",
            "fixed_denom_match_at10":matched/10,
            "fully_observed":int(valid and len(qualified)==10)})
    return result
result={}
for typ,ann in D.items():
    result[typ]={m:score_one(m,typ,ann) for m in MODELS}
    for model,z in result[typ].items():
        with (OUT/f"query_{typ}_{model}.csv").open("w",newline="",encoding="utf8") as f:
            w=csv.DictWriter(f,fieldnames=list(z[0]));w.writeheader();w.writerows(z)
# Exact training-catalog baseline conditional on nonempty labels; evaluate only queries
# for which task annotations exist. Distinguish missing-label observations.
expect={}
for typ,ann in D.items():
    eligible_train=[ann[tid] for tid in trainids if ann.get(tid)]
    assert eligible_train
    expect[typ]=float(np.mean([sum(bool(ann.get(qids[i],set())&x) for x in eligible_train)/len(eligible_train)
                              for i in range(len(qids)) if ann.get(qids[i])]))
# Cluster bootstrap paired, query-level fixed denominator (missing recommends count 0
# for rate but must separately report missingness, not a fully observed 'failure').
def summarize(typ,model):
    vals=result[typ][model]
    matched=sum(r["matched_positions"] for r in vals)
    eligible=sum(r["eligible_positions"] for r in vals)
    queries=sum(r["query_has_nonempty_labels"] for r in vals)
    return {"model":model,"nonempty_queries":queries,
       "eligible_labelled_positions":eligible,"total_positions":len(vals)*10,
       "conditional_tag_agreement":round(matched/eligible,5) if eligible else None,
       "matched_per_total_position":round(matched/(len(vals)*10),5),
       "fully_annotated_query_lists":sum(r["fully_observed"] for r in vals)}
summary={typ:[summarize(typ,m) for m in MODELS] for typ in D}
artists=sorted(set(r["query_artist"] for r in rows["cosine_z"]))
idx=collections.defaultdict(list)
for i,r in enumerate(rows["cosine_z"]):idx[r["query_artist"]].append(i)
bootstrap={}
for typ in D:
    baseline=np.array([r["fixed_denom_match_at10"] for r in result[typ]["cosine_z"]],float)
    bootstrap[typ]={}
    for model in MODELS[1:]:
        variant=np.array([r["fixed_denom_match_at10"] for r in result[typ][model]],float)
        diff=(variant-baseline)*100
        rng=random.Random(606200 + MODELS.index(model) + (100 if typ=="moodtheme" else 0))
        draws=[]
        for _ in range(1000):
            sampled=[rng.choice(artists) for _ in artists]
            indices=[i for a in sampled for i in idx[a]]
            draws.append(float(np.mean(diff[indices])))
        bootstrap[typ][model]={"paired_mean_pp":round(float(np.mean(diff)),4),
          "cluster_bootstrap_95_pp":[round(float(v),4) for v in np.quantile(draws,[.025,.975])]}
report={"release":"6.2","status":"COMPLETE","query_count":len(qids),
        "sources":meta,"summary":summary,
        "random_train_catalog_conditional_label_agreement":{k:round(v,5) for k,v in expect.items()},
        "paired_artist_cluster_intervals_fixed_denom":bootstrap,
        "methodology":["Frozen six rankings, identical 800 artist-disjoint queries.",
          "Tag sources are different annotation tasks on the same MTG-Jamendo corpus, so not truly independent provenance or listener judgments.",
          "Query tags and recommended-track tags must be nonempty to be an eligible comparison.",
          "Eligible-denominator conditional agreement excludes missing tags and may have model-dependent selection bias.",
          "Fixed-denominator matched-per-10 is a conservative annotation-availability metric, not true relevance.",
          "Models were not tuned on instrument or mood/theme test annotations.",
          "Ridge model was trained on genre labels and thus its transfer measures cross-task consistency, not preference relevance.",
          "No Jamendo statistics API and no popularity conclusions."]}
(OUT/"REPORT_62.json").write_text(json.dumps(report,indent=2),encoding="utf8")
with (OUT/"MODEL_SUMMARY.csv").open("w",newline="",encoding="utf8") as f:
    w=csv.writer(f);w.writerow(["task","model","nonempty_queries","eligible_positions","conditional_agreement","fixed_denom_match","fully_annotated_queries"])
    for typ,models in summary.items():
        for m in models:w.writerow([typ,m["model"],m["nonempty_queries"],m["eligible_labelled_positions"],m["conditional_tag_agreement"],m["matched_per_total_position"],m["fully_annotated_query_lists"]])
print(json.dumps(report,indent=2),flush=True)
