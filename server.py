
import os
import tempfile
import traceback
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS

# birdnetlib provides a clean Python interface to BirdNET-Analyzer

from birdnetlib import Recording
from birdnetlib.analyzer import Analyzer

app = Flask(**name**)
CORS(app)  # Allow requests from React Native / Expo dev server

# Load the BirdNET model once at startup (heavy — ~500ms)

print("Loading BirdNET model…")
analyzer = Analyzer()
print("BirdNET model loaded.")

# —————————————————————————

# Health check

# —————————————————————————

@app.route("/health", methods=["GET"])
def health():
return jsonify({"status": "ok", "model": "BirdNET-Analyzer"})

# —————————————————————————

# Bird identification

# —————————————————————————

@app.route("/identify", methods=["POST"])
def identify():
"""
Accepts a multipart audio file upload plus optional metadata.

```
Form fields:
    audio       — audio file (wav, mp3, flac, m4a)
    lat         — float, player latitude  (optional but improves accuracy)
    lon         — float, player longitude (optional but improves accuracy)
    min_conf    — float 0–1, minimum confidence threshold (default 0.25)

Returns:
    {
        "success": true,
        "detections": [
            {
                "common_name":    "American Robin",
                "scientific_name": "Turdus migratorius",
                "confidence":     0.87,
                "start_time":     0.0,
                "end_time":       3.0
            },
            ...
        ],
        "top": { ...highest confidence detection... } | null
    }
"""
# -- Validate file upload --
if "audio" not in request.files:
    return jsonify({"success": False, "error": "No audio file provided."}), 400

audio_file = request.files["audio"]
if audio_file.filename == "":
    return jsonify({"success": False, "error": "Empty filename."}), 400

# -- Parse optional metadata --
try:
    lat = float(request.form.get("lat", -1))
    lon = float(request.form.get("lon", -1))
    min_conf = float(request.form.get("min_conf", 0.25))
except ValueError:
    return jsonify({"success": False, "error": "Invalid lat/lon/min_conf values."}), 400

# -- Save to temp file (birdnetlib needs a file path) --
suffix = os.path.splitext(audio_file.filename)[-1] or ".wav"
with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
    tmp_path = tmp.name
    audio_file.save(tmp_path)

try:
    # -- Run BirdNET analysis --
    week = datetime.now().isocalendar()[1] // 2  # week 1–26 for BirdNET
    recording = Recording(
        analyzer,
        tmp_path,
        lat=lat if lat != -1 else None,
        lon=lon if lon != -1 else None,
        week_48=week,
        min_conf=min_conf,
    )
    recording.analyze()

    # -- Format detections --
    detections = []
    for d in recording.detections:
        detections.append({
            "common_name":     d["common_name"],
            "scientific_name": d["scientific_name"],
            "confidence":      round(d["confidence"], 4),
            "start_time":      d["start_time"],
            "end_time":        d["end_time"],
        })

    # Sort by confidence descending
    detections.sort(key=lambda x: x["confidence"], reverse=True)

    # Deduplicate by species (keep highest confidence per species)
    seen = {}
    for d in detections:
        key = d["scientific_name"]
        if key not in seen or d["confidence"] > seen[key]["confidence"]:
            seen[key] = d
    unique_detections = list(seen.values())

    top = unique_detections[0] if unique_detections else None

    return jsonify({
        "success":    True,
        "detections": unique_detections,
        "top":        top,
        "count":      len(unique_detections),
    })

except Exception as e:
    traceback.print_exc()
    return jsonify({"success": False, "error": str(e)}), 500

finally:
    # Always clean up temp file
    try:
        os.unlink(tmp_path)
    except OSError:
        pass
```

# —————————————————————————

# Entry point

# —————————————————————————

if **name** == "**main**":
port = int(os.environ.get("PORT", 5000))
print(f"Aviara BirdNET server running on port {port}")
app.run(host="0.0.0.0", port=port, debug=False)
