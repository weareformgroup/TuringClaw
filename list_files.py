import os
import glob

downloads = os.path.expandvars(r'C:\Users\Administrator\Downloads')
print(f"Downloads path: {downloads}")
print(f"Exists: {os.path.exists(downloads)}")

files = glob.glob(downloads + r'\*')
print(f"Files: {len(files)}")

for f in files[:30]:
    print(os.path.basename(f))
