import argparse
import hashlib
import json
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

MODEL_CANDIDATES = {
    "mobilenet_v2_feature_vector": {
        "url": (
            "https://tfhub.dev/tensorflow/lite-model/"
            "mobilenet_v2_1.0_224/1/metadata/1?lite-format=tflite"
        ),
        "filename": "mobilenet_v2_1.0_224_feature_vector.tflite",
        "notes": (
            "Official TensorFlow Hub TFLite model. Experimental candidate for "
            "future object-gate backend evaluation."
        ),
    }
}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Fetch an experimental local object-gate model."
    )
    parser.add_argument(
        "--candidate",
        choices=sorted(MODEL_CANDIDATES),
        default="mobilenet_v2_feature_vector",
        help="Named model candidate to fetch.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(ROOT / "models" / "object_gate"),
        help="Directory for downloaded model artifact.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite an existing model file.",
    )
    args = parser.parse_args()

    candidate = MODEL_CANDIDATES[args.candidate]
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    model_path = output_dir / candidate["filename"]
    manifest_path = output_dir / "manifest.json"

    if model_path.exists() and not args.force:
        print(f"model_path={model_path}")
        print("status=already_present")
        return 0

    with urllib.request.urlopen(candidate["url"], timeout=60) as response:
        payload = response.read()

    model_path.write_bytes(payload)
    sha256 = hashlib.sha256(payload).hexdigest()
    manifest = {
        "candidate": args.candidate,
        "source_url": candidate["url"],
        "model_path": str(model_path),
        "sha256": sha256,
        "notes": candidate["notes"],
    }
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    print(f"model_path={model_path}")
    print(f"manifest_path={manifest_path}")
    print(f"sha256={sha256}")
    print("status=downloaded")
    print(
        "next=export PHASMID_OBJECT_MODEL_PATH="
        + str(model_path)
        + " and set PHASMID_EXPERIMENTAL_OBJECT_MODEL=1"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
