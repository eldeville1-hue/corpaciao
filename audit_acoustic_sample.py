#!/usr/bin/env python3
"""Audit ONE official MTG-Jamendo AcousticBrainz tar archive. No raw audio or features uploaded."""
import csv,hashlib,io,json,os,pathlib,re,sys,tarfile,urllib.request
BASE="https://raw.githubusercontent.com/MTG/mtg-jamendo-dataset/master/data/"
MIRRORS=["https://cdn.freesound.org/mtg-jamendo/raw_30s/acousticbrainz/",
         "https://essentia.upf.edu/documentation/datasets/mtg-jamendo/raw_30s/acousticbrainz/"]
MAX_BYTES=150_000_000

def get(url,limit=MAX_BYTES):
    req=urllib.request.Request(url,headers={"User-Agent":"CORPACIAO-research-audit/1.0"})
    with urllib.request.urlopen(req,timeout=35) as res:
        data=res.read(limit+1)
    if len(data)>limit:raise ValueError("Download exceeds safety limit")
    return data

def digest(b):return hashlib.sha256(b).hexdigest()

def main():
    out=pathlib.Path("acoustic_audit");out.mkdir(exist_ok=True)
    manifest=get(BASE+"download/raw_30s_acousticbrainz_sha256_tars.txt",200_000).decode()
    rows=[x.split() for x in manifest.splitlines() if x.strip()]
    name="raw_30s_acousticbrainz-00.tar.gz"
    expected=dict((n,h) for h,n in rows)[name]
    genre=get(BASE+"autotagging_genre.tsv",15_000_000).decode("utf-8-sig")
    genre_rows=list(csv.reader(io.StringIO(genre),delimiter="\t"))
    ids={str(int(r[0].removeprefix("track_"))) for r in genre_rows if len(r)>=6 and re.fullmatch(r"(?:track_)?[0-9]+",r[0].strip())}
    report={"archive":name,"expected_sha256":expected,"official_archives_in_manifest":len(rows),
            "cohort_track_ids":len(ids),"max_download_bytes":MAX_BYTES,
            "results_are":"feature availability/coverage, not recommendation outcomes"}
    archive=None;errors=[]
    for mirror in MIRRORS:
        try:
            archive=get(mirror+name)
            if digest(archive)!=expected:raise ValueError("SHA256 mismatch")
            report["successful_mirror"]=mirror
            break
        except Exception as e:errors.append({"mirror":mirror,"error":str(e)[:300]})
    report["mirror_errors"]=errors
    if archive is None:
        report["status"]="DOWNLOAD_FAILED"
    else:
        report["status"]="VERIFIED"
        report["archive_bytes"]=len(archive)
        report["download_sha256"]=digest(archive)
        matched=set();seen=set();json_count=0;examples=[]
        with tarfile.open(fileobj=io.BytesIO(archive),mode="r:gz") as tar:
            for member in tar:
                if not member.isfile() or not member.name.endswith(".json"):continue
                json_count+=1
                stem=pathlib.PurePosixPath(member.name).stem
                numeric=re.findall(r"\d+",stem)
                if numeric:
                    tid=numeric[-1];seen.add(tid)
                    if tid in ids:matched.add(tid)
                if len(examples)<3:
                    f=tar.extractfile(member)
                    if f:
                        obj=json.load(f)
                        examples.append({"member_path":member.name,"top_keys":list(obj.keys())[:25],
                                         "lowlevel_keys":list(obj.get("lowlevel",{}).keys())[:25] if isinstance(obj,dict) else []})
        report.update(json_files=json_count,unique_numeric_stem_ids=len(seen),
                      ids_joining_genre_catalog=len(matched),sample_feature_structure=examples)
    (out/"ACOUSTIC_AUDIT.json").write_text(json.dumps(report,indent=2),encoding="utf8")
    print(json.dumps(report,indent=2))
    if archive is None:sys.exit(1)

if __name__=="__main__":main()
