import json
import csv
import sys
from pathlib import Path


def load(path):
    with open(path) as f:
        return json.load(f)


def check_frame_mismatch(event_data, track_data):
    issues = []
    ef = event_data["metadata"]["total_frames"]
    tf = track_data["max_frames"]
    if ef != tf:
        issues.append(("frame_count_mismatch", "", "", f"event={ef}, track={tf}"))
    return issues


def check_event_ranges(event_data):
    issues = []
    total = event_data["metadata"]["total_frames"]
    events = event_data["events"]

    for p in events.get("passes", []):
        s, e = p["pass_start"], p["pass_end"]
        if s >= e:
            issues.append(("bad_pass_range", p["id"], s, f"{s} >= {e}"))
        if e > total:
            issues.append(("pass_out_of_range", p["id"], e, f"end={e} > total={total}"))

    for d in events.get("dribbles", []):
        s, e = d["dribble_start"], d["dribble_end"]
        if s >= e:
            issues.append(("bad_dribble_range", d["id"], s, f"{s} >= {e}"))

    for ib in events["inbound"].get("inbound_list", []):
        s, e = ib["start_frame"], ib["end_frame"]
        if s >= e:
            issues.append(("bad_inbound_range", "", s, f"{s} >= {e}"))
        roles = {p["role"]: p["track_id"] for p in ib.get("player_info", [])}
        if roles.get("passer") == roles.get("receiver"):
            issues.append(("self_pass_inbound", "", s, "passer == receiver"))

    return issues


def check_track_ids_exist(event_data, track_data):
    issues = []
    valid_ids = {t["track_id"] for t in track_data["tracks"]}
    events = event_data["events"]

    for ib in events["inbound"].get("inbound_list", []):
        for p in ib.get("player_info", []):
            if p["track_id"] not in valid_ids:
                issues.append(("orphan_track_id", "", ib["start_frame"],
                               f"track_id={p['track_id']} not in tracks"))
    return issues


def check_single_ball_carrier(track_data):
    issues = []
    frame_carriers = {}
    for t in track_data["tracks"]:
        for f in t["frames"]:
            if f.get("ball_carrier"):
                frame_carriers.setdefault(f["frame_num"], []).append(t["track_id"])

    for frame, carriers in frame_carriers.items():
        if len(carriers) > 1:
            issues.append(("multiple_ball_carriers", "", frame, f"track_ids={carriers}"))
    return issues


def check_bbox_bounds(track_data, width=1280, height=720):
    issues = []
    for t in track_data["tracks"]:
        for f in t["frames"]:
            x, y, w, h = f["x"], f["y"], f["w"], f["h"]
            if x < 0 or y < 0 or x + w > width or y + h > height:
                issues.append(("bbox_out_of_bounds", t["track_id"], f["frame_num"],
                               f"bbox=({x},{y},{w},{h})"))
    return issues


def check_low_confidence(track_data, threshold=0.5):
    issues = []
    for t in track_data["tracks"]:
        for f in t["frames"]:
            if f["conf"] < threshold:
                issues.append(("low_confidence", t["track_id"], f["frame_num"],
                               f"conf={f['conf']}"))
    return issues


def check_missing_frames(track_data):
    issues = []
    for t in track_data["tracks"]:
        frames = sorted(f["frame_num"] for f in t["frames"])
        if not frames:
            continue
        expected = set(range(frames[0], frames[-1] + 1))
        missing = expected - set(frames)
        if missing:
            issues.append(("missing_frames", t["track_id"], frames[0],
                           f"missing {len(missing)} frames between {frames[0]}-{frames[-1]}"))
    return issues


def main():
    if len(sys.argv) < 3:
        print("Usage: python possession_qa.py <event.json> <track.json>")
        return

    event_path, track_path = sys.argv[1], sys.argv[2]
    clip = Path(event_path).stem.replace("_event", "")

    event_data = load(event_path)
    track_data = load(track_path)

    issues = []
    issues += check_frame_mismatch(event_data, track_data)
    issues += check_event_ranges(event_data)
    issues += check_track_ids_exist(event_data, track_data)
    issues += check_single_ball_carrier(track_data)
    issues += check_bbox_bounds(track_data)
    issues += check_low_confidence(track_data)
    issues += check_missing_frames(track_data)

    if not issues:
        print(f"{clip}: OK - no issues found")
        return

    with open("qa_report.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["clip", "issue_type", "event_id", "frame", "detail"])
        for itype, eid, frame, detail in issues:
            w.writerow([clip, itype, eid, frame, detail])

    print(f"{clip}: {len(issues)} issue(s) found -> qa_report.csv")
    counts = {}
    for itype, *_ in issues:
        counts[itype] = counts.get(itype, 0) + 1
    for k, v in counts.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()