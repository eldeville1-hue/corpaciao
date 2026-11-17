#!/usr/bin/env python3
"""Pre-outcome feasibility audit for MTG-Jamendo genre TSV."""
import argparse, collections, csv, hashlib, json, pathlib, sys

def digest(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for chunk in iter(lambda:f.read(1048576),b""):
            h.update(chunk)
    return h.hexdigest()

def parse(path):
    tracks={}; issues=[]; counts=collections.Counter()
    with open(path,encoding="utf-8-sig",newline="") as f:
        for line,parts in enumerate(csv.reader(f,delimiter="\t"),1):
            if not parts or not parts[0].strip() or parts[0].lstrip().startswith("#"):
                continue
            if parts[0].strip().lower() in {"track_id","trackid"}:
                continue
            if len(parts)<6:
                issues.append({"line":line,"error":"too_few_fields"});continue
            tid,artist,album=map(str.strip,parts[:3])
            if not tid or not artist:
                issues.append({"line":line,"error":"missing_track_or_artist_id"});continue
            if tid in tracks:
                issues.append({"line":line,"error":"duplicate_track_id","track_id":tid});continue
            tags={s.strip().lower()[8:] for s in parts[5:] if s.strip().lower().startswith("genre---")}
            tracks[tid]={"track_id":tid,"artist_id":artist,"album_id":album,"genre_tags":tags}
            counts.update(tags)
    return tracks,issues,counts

def cohort(tags):
    ex="experimental" in tags; el="electronic" in tags
    return "both" if ex and el else "experimental_only" if ex else "electronic_only" if el else "other"

def split(artist,seed):
    u=int(hashlib.sha256(f"{seed}|{artist}".encode()).hexdigest()[:15],16)/float(16**15)
    return "train" if u<.70 else "development" if u<.85 else "test"

def summarize(rows):
    return {"tracks":len(rows),"artists":len({x["artist_id"] for x in rows}),"albums":len({x["album_id"] for x in rows})}

def audit(path,out,seed=314159):
    out.mkdir(parents=True,exist_ok=True)
    tracks,issues,counts=parse(path)
    report={"source":{"filename":path.name,"bytes":path.stat().st_size,"sha256":digest(path)},
            "input_rows_accepted":len(tracks),"input_error_count":len(issues),
            "input_errors":issues[:100],"top_20_genre_tags":counts.most_common(20),
            "split_seed":seed,"split_rule":"SHA256(seed|artist_id), train/development/test 70/15/15"}
    if issues or not tracks:
        report.update(status="INVALID_INPUT",study_admitted=False)
        (out/"COHORT_AUDIT.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
        raise ValueError("Input malformed or empty; see COHORT_AUDIT.json")
    groups=collections.defaultdict(list); splits=collections.defaultdict(list)
    rows=list(tracks.values())
    with (out/"cohorts.csv").open("w",newline="",encoding="utf-8") as f:
        w=csv.writer(f);w.writerow(["track_id","artist_id","album_id","cohort","artist_split","genre_tag_count"])
        for r in rows:
            c=cohort(r["genre_tags"]);s=split(r["artist_id"],seed)
            groups[c].append(r);splits[(s,c)].append(r)
            w.writerow([r["track_id"],r["artist_id"],r["album_id"],c,s,len(r["genre_tags"])])
    names=["experimental_only","electronic_only","both","other"]
    artist_splits=collections.defaultdict(set)
    for r in rows:artist_splits[r["artist_id"]].add(split(r["artist_id"],seed))
    report.update(status="COHORT_AUDITED",all_tracks=summarize(rows),
        experimental_tag=summarize([r for r in rows if "experimental" in r["genre_tags"]]),
        electronic_tag=summarize([r for r in rows if "electronic" in r["genre_tags"]]),
        cohorts={c:summarize(groups[c]) for c in names},
        split_cohorts={s:{c:summarize(splits[(s,c)]) for c in names} for s in ["train","development","test"]},
        artist_split_leakage_count=sum(len(v)>1 for v in artist_splits.values()),
        popularity_measure_available=False,acoustic_feature_vectors_available=False,study_admitted=False,
        next_gate="Acquire measured listening counts and track-level acoustic vectors; resolve multi-label evaluation")
    (out/"COHORT_AUDIT.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    return report

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--genre",required=True,type=pathlib.Path)
    p.add_argument("--out",type=pathlib.Path,default=pathlib.Path("audit_output"))
    p.add_argument("--seed",type=int,default=314159)
    args=p.parse_args()
    try:
        result=audit(args.genre,args.out,args.seed)
        print(json.dumps({"status":result["status"],"all_tracks":result["all_tracks"],"experimental":result["experimental_tag"],"electronic":result["electronic_tag"],"artist_split_leakage_count":result["artist_split_leakage_count"]},indent=2))
    except Exception as e:
        print("AUDIT FAILED:",e,file=sys.stderr);sys.exit(1)
