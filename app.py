import subprocess
import os
import sys

os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.exit(subprocess.call(["npx", "tsx", "server/index.ts"]))
