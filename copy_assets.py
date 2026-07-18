import shutil
import os

src1 = r"C:\Users\Dell 5490T\.gemini\antigravity-ide\brain\c7ac0849-c5e9-4389-bfb5-9a70c5219110\hero_automation_1784407004780.png"
src2 = r"C:\Users\Dell 5490T\.gemini\antigravity-ide\brain\c7ac0849-c5e9-4389-bfb5-9a70c5219110\schema_isolation_1784407017066.png"

dest1 = r"d:\pydata2.0\pydatahackethon\frontend\public\hero_automation.png"
dest2 = r"d:\pydata2.0\pydatahackethon\frontend\public\schema_isolation.png"

for src, dest in [(src1, dest1), (src2, dest2)]:
    if os.path.exists(src):
        shutil.copy2(src, dest)
        print(f"Copied {src} to {dest}")
    else:
        print(f"Source not found: {src}")
