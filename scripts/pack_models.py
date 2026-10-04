"""Pack the trained surrogates into models.zip (upload it to Google Drive / a GitHub release for teammates and for deployment)."""
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILES = ["models/surrogate_A.joblib", "models/surrogate_B.joblib", "models/manifest.json"]

if __name__ == "__main__":
    out = ROOT / "models.zip"
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for f in FILES:
            if not (ROOT / f).exists():
                raise SystemExit(f"{f} is missing: run `python -m rcopt.cli phase3` first")
            z.write(ROOT / f, f)
    print(f"wrote {out} ({out.stat().st_size / 1e6:.0f} MB)")
