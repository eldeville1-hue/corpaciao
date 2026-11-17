#!/usr/bin/env python3
"""Small, documented TEST-ID feasibility probe. NOT bulk statistics acquisition."""
import json, pathlib, urllib.parse, urllib.request, datetime
ids=["1133100","1375200","1273900","101900","1333600"]
report={"purpose":"API access, ID mapping and stats schema feasibility ONLY",
        "client_id_source":"Jamendo authentication docs - published testing read ID",
        "requested_track_ids":ids,"records":[],"api_endpoint":"https://api.jamendo.com/v3.0/tracks/",
        "test_only":True,"bulk_data_access_authorized":False,
        "timestamp_utc":datetime.datetime.now(datetime.timezone.utc).isoformat()}
for track_id in ids:
    params=urllib.parse.urlencode({"client_id":"709fa152","format":"json","id":track_id,"limit":1,"include":"stats","type":"single albumtrack"})
    url="https://api.jamendo.com/v3.0/tracks/?"+params
    row={"requested_track_id":track_id}
    try:
        req=urllib.request.Request(url,headers={"User-Agent":"CORPACIAO-feasibility-test/0.1"})
        with urllib.request.urlopen(req,timeout=25) as response:
            data=json.load(response)
        header=data.get("headers",{})
        row["api_status"]=header.get("status")
        row["api_code"]=header.get("code")
        row["api_error"]=header.get("error_message")
        row["returned_count"]=len(data.get("results",[]))
        if data.get("results"):
            hit=data["results"][0]
            row["returned_track_id"]=str(hit.get("id"))
            row["id_exact_match"]=str(hit.get("id"))==track_id
            row["stats_field_present"]="stats" in hit
            row["stats_keys"]=list(hit.get("stats",{})) if isinstance(hit.get("stats"),dict) else []
            row["stats_preview"]={k:v for k,v in hit.get("stats",{}).items() if k.startswith("listens") or k.startswith("downloads")} if isinstance(hit.get("stats"),dict) else None
    except Exception as e:
        row["network_or_api_error"]=str(e)[:500]
    report["records"].append(row)
out=pathlib.Path("jamendo_api_probe");out.mkdir(exist_ok=True)
(out/"API_FEASIBILITY.json").write_text(json.dumps(report,indent=2),encoding="utf8")
print(json.dumps(report,indent=2))
