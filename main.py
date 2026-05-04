import os
import sys

ROOT = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(ROOT, "src"))

from phantasm.cli import main

if __name__ == "__main__":
    main()
