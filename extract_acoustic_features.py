#!/usr/bin/env python3
"""CORPACIAO: authenticated MTG-Jamendo acoustic-feature extraction.

Download only official AcousticBrainz JSON tars. This is a pre-outcome
feature-availability audit; there is no popularity estimate.
"""
import argparse, csv, hashlib, io, json, math, pathlib, re, tarfile, time, urllib.request

ROOT="https://raw.githubusercontent.com/MTG/mtg-jamendo-dataset/master/data/download/"
MIRRORS=[
 "https://cdn.freesound.org/mtg-jamendo/raw_30s/acousticbrainz/",
 "https://essentia.upf.edu/documentation/datasets/mtg-jamendo/raw_30s/acousticbrainz/"
]
FEATURE_PATHS=[
 "lowlevel.average_loudness", "lowlevel.dynamic_complexity",
 "lowlevel.dissonance.mean", "lowlevel.hfc.mean",
 "lowlevel.pitch_salience.mean", "lowlevel.spectral_centroid.mean",
 "lowlevel.spectral_complexity.mean", "lowlevel.spectral_decrease.mean",
 "lowlevel.spectral_energy.mean", "lowlevel.spectral_energyband_high.mean",
 "lowlevel.spectral_energyband_low.mean", "lowlevel.spectral_flux.mean",
 "lowlevel.spectral_kurtosis.mean", "lowlevel.spectral_rms.mean",
 "lowlevel.spectral_rolloff.mean", "lowlevel.spectral_skewness.mean",
 "lowlevel.spectral_spread.mean", "lowlevel.zerocrossingrate.mean",
 "rhythm.bpm", "rhythm.danceability", "rhythm.onset_rate",
 "tonal.chords_changes_rate", "tonal.chords_strength.mean",
 "tonal.hpcp_entropy.mean", "tonal.key_strength",
 "tonal.tuning_diatonic_strength", "tonal.tuning_equal_tempered_deviation",
 "tonal.tuning_nontempered_energy_ratio",
]
FEATURE_COLUMNS=[x.replace(".","__") for x in FEATURE_PATHS]
MAX_ARCHIVE_BYTES=100_000_000

def download(url, limit):
    req=urllib.request.Request(url,headers={"User-Agent":"CORPACIAO-MTG-feature-audit/1.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        data=r.read(limit+1)
    if len(data)>limit:raise ValueError("archive exceeds size limit")
    return data

def sha(data):return hashlib.sha256(data).hexdigest()

def nested(obj, path):
    for key in path.split("."):
        if not isinstance(obj,dict) or key not in obj:return ""
        obj=obj[key]
    if isinstance(obj,(int,float)) and not isinstance(obj,bool) and math.isfinite(obj):
        return format(obj,".10g")
    return ""

def parse_manifest(text):
    rows={}
    for line in text.splitlines():
        if not line.strip():continue
        digest,filename=line.split()
        if not re.fullmatch(r"[a-f0-9]{64}",digest) or not re.fullmatch(r"raw_30s_acousticbrainz-[0-9]{2}\.tar\.gz",filename):
            raise ValueError("unexpected manifest entry")
        rows[filename]=digest
    if len(rows)!=100:raise ValueError(f"Expected 100 archives, received {len(rows)}")
    return dict(sorted(rows.items()))

def run(shard,shards,out):
    manifest=parse_manifest(download(ROOT+"raw_30s_acousticbrainz_sha256_tars.txt",200_000).decode())
    selections=[(name,hash_) for i,(name,hash_) in enumerate(manifest.items()) if i%shards==shard]
    out.mkdir(parents=True,exist_ok=True)
    seen=set();archive_log=[];errors=[]
    csv_path=out/f"features_{shard:02d}.csv"
    with csv_path.open("w",newline="",encoding="utf-8") as f:
        writer=csv.writer(f);writer.writerow(["track_id","archive",*FEATURE_COLUMNS])
        for name,expected in selections:
            data=None
            failures=[]
            for base in MIRRORS:
                for attempt in range(2):
                    try:
                        candidate=download(base+name,MAX_ARCHIVE_BYTES)
                        if sha(candidate)!=expected:raise ValueError("official archive SHA256 mismatch")
                        data=candidate
                        break
                    except Exception as e:failures.append(str(e)[:150])
                    time.sleep(1)
                if data is not None:break
            if data is None:
                errors.append({"archive":name,"errors":failures})
                continue
            count=0
            with tarfile.open(fileobj=io.BytesIO(data),mode="r:gz") as tar:
                for item in tar:
                    if not item.isfile() or not item.name.endswith(".json"):continue
                    stem=pathlib.PurePosixPath(item.name).stem
                    if not re.fullmatch(r"[0-9]+",stem):raise ValueError(f"Unexpected JSON member {item.name}")
                    track_id=str(int(stem))
                    if track_id in seen:raise ValueError(f"Duplicate track {track_id}")
                    obj=json.load(tar.extractfile(item))
                    values=[nested(obj,p) for p in FEATURE_PATHS]
                    writer.writerow([track_id,name,*values])
                    seen.add(track_id);count+=1
            archive_log.append({"name":name,"sha256":expected,"bytes":len(data),"json_files":count})
            print(f"Validated {name}: {count} feature files",flush=True)
    report={"shard":shard,"shards":shards,"expected_archive_count":len(selections),
            "verified_archive_count":len(archive_log),"track_count":len(seen),
            "feature_columns":FEATURE_COLUMNS,"archives":archive_log,"download_errors":errors,
            "outcome_data_analyzed":False}
    (out/f"report_{shard:02d}.json").write_text(json.dumps(report,indent=2))
    if errors:raise RuntimeError(f"{len(errors)} archive downloads failed; see report")
    return report

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--shard",type=int,required=True)
    ap.add_argument("--shards",type=int,default=10)
    ap.add_argument("--out",type=pathlib.Path,default=pathlib.Path("acoustic_output"))
    a=ap.parse_args()
    if not 0<=a.shard<a.shards:ap.error("invalid shard")
    print(json.dumps({k:v for k,v in run(a.shard,a.shards,a.out).items() if k not in ("archives","feature_columns")},indent=2))
