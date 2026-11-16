"""Print exact SHA-256 for the committed source file, without normalization."""
from pathlib import Path
import hashlib
p = Path(__file__).resolve().parents[1] / 'contracts' / 'gainlock.py'
print(f'{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.as_posix()}')
