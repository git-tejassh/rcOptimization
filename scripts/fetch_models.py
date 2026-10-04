"""Download models.zip from MODELS_URL (direct link or Google Drive share link) and unpack it into the repo.

Usage:  MODELS_URL=<link> python scripts/fetch_models.py      (does nothing when the models are already present)
"""
import os
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

if __name__ == "__main__":
    if (ROOT / "models" / "surrogate_A.joblib").exists() and (ROOT / "models" / "surrogate_B.joblib").exists():
        print("models already present")
        raise SystemExit(0)
    url = os.environ.get("MODELS_URL", "")
    if not url:
        raise SystemExit("set MODELS_URL to the link of models.zip (see docs/DEPLOY.md), or train with `python -m rcopt.cli phase3`")
    target = ROOT / "models.zip"
    if "drive.google.com" in url:
        import gdown  # pip install gdown

        gdown.download(url, str(target), quiet=False, fuzzy=True)
    else:
        urllib.request.urlretrieve(url, target)
    with zipfile.ZipFile(target) as z:
        z.extractall(ROOT)
    target.unlink()
    print("models unpacked into models/")
