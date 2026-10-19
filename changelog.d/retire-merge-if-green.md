### Removed
- `.github/merge-if-green.sh`, which refused any head behind `main` and so the
  second merge of every train. The merge train (`.github/merge-train.py`)
  holds the checks it made, and nothing in the library or its exports changes
  (#155).
