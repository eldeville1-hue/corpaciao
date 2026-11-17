#!/usr/bin/env python3
"""Merge official acoustic feature extracts against official genre metadata."""
import csv,hashlib,io,json,pathlib,sys,urllib.request,collections,math
from extract_acoustic_features import FEATURE_COLUMNS

URL="https://raw.githubusercontent.com/MTG/mtg-jamendo-dataset/master/data/autotagging_genre.tsv"
def sha(p):
    h=hashlib.sha256()
    with open(p,"rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""):h.update(b)
    return h.hexdigest()

def load_genres(path):
    result={}
    with path.open(encoding="utf-8-sig",newline="") as f:
        for r in csv.reader(f,delimiter="\t"):
            if not r or r[0].lower()=="track_id" or r[0].startswith("#"):continue
            if len(r)<6:raise ValueError(f"Bad metadata row: {r[:2]}")
            t=str(int(r[0].removeprefix("track_")))
            if t in result:raise ValueError(f"duplicate metadata track {t}")
            tags=sorted({s.removeprefix("genre---").lower().strip() for s in r[5:] if s.lower().startswith("genre---")})
            result[t]={"artist_id":r[1],"album_id":r[2],"genre_tags":"|".join(tags),
                       "experimental":int("experimental" in tags),"electronic":int("electronic" in tags)}
    return result

def main():
    root=pathlib.Path("acoustic_output")
    out=pathlib.Path("merged_acoustic");out.mkdir(parents=True,exist_ok=True)
    files=sorted(root.rglob("features_*.csv"));reports=sorted(root.rglob("report_*.json"))
    if len(files)!=10 or len(reports)!=10:raise RuntimeError(f"Missing shards: {len(files)} CSV, {len(reports)} reports")
    logs=[json.loads(p.read_text()) for p in reports]
    if set(j["shard"] for j in logs)!=set(range(10)):raise RuntimeError("duplicate/missing shards")
    if sum(j["verified_archive_count"] for j in logs)!=100:raise RuntimeError("not all 100 archives verified")
    urllib.request.urlretrieve(URL,out/"genre_source.tsv")
    genres=load_genres(out/"genre_source.tsv")
    seen=set();matched=set();completeness=collections.Counter();matched_groups=collections.Counter()
    cols=["track_id","artist_id","album_id","genre_tags","experimental","electronic",*FEATURE_COLUMNS]
    with (out/"acoustic_features_joined.csv").open("w",newline="",encoding="utf-8") as o:
        writer=csv.DictWriter(o,fieldnames=cols);writer.writeheader()
        for file in files:
            with file.open(newline="",encoding="utf-8") as f:
                reader=csv.DictReader(f)
                if reader.fieldnames!=["track_id","archive",*FEATURE_COLUMNS]:raise RuntimeError("feature schema mismatch")
                for r in reader:
                    t=r["track_id"]
                    if t in seen:raise RuntimeError(f"Duplicate feature track across archives: {t}")
                    seen.add(t)
                    if t not in genres:continue
                    matched.add(t)
                    g=genres[t]
                    writer.writerow({"track_id":t,**g,**{k:r[k] for k in FEATURE_COLUMNS}})
                    for k in FEATURE_COLUMNS:
                        if r[k]!="":completeness[k]+=1
                    grp="both" if g["experimental"] and g["electronic"] else "experimental_only" if g["experimental"] else "electronic_only" if g["electronic"] else "other"
                    matched_groups[grp]+=1
    report={"status":"SUCCESS","metadata_tracks":len(genres),
            "feature_track_ids":len(seen),"matched_tracks":len(matched),
            "metadata_coverage_percent":round(100*len(matched)/len(genres),3),
            "target_genre_coverage":{"experimental":sum(genres[t]["experimental"] for t in matched),
                                     "electronic":sum(genres[t]["electronic"] for t in matched)},
            "matched_cohorts":dict(matched_groups),
            "feature_completeness":{k:{"present":completeness[k],"share":round(completeness[k]/max(1,len(matched)),4)} for k in FEATURE_COLUMNS},
            "source_genre_sha256":sha(out/"genre_source.tsv"),"joined_table_sha256":sha(out/"acoustic_features_joined.csv"),
            "source_archive_count":100,"historical_popularity_available":False,"confirmatory_results_generated":False,
            "next_gate":"Measured track-level popularity + preregistered external recommendation protocol"}
    (out/"FEATURE_COVERAGE_REPORT.json").write_text(json.dumps(report,indent=2))
    print(json.dumps({k:v for k,v in report.items() if k!="feature_completeness"},indent=2))
    if len(matched)<40_000:raise RuntimeError("Insufficient feature/genre join coverage")
if __name__=="__main__":main()
