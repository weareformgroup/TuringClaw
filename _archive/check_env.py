import sys, os, site
print("Python:", sys.executable)
print("Site packages:", site.getusersitepackages())

# Try to create a writable temp dir
tmp_dirs = [
    r"C:\Users\Administrator\anaconda3\Temp",
    r"C:\Users\Administrator\anaconda3\tmp",
    r"C:\Users\Administrator\AppData\Local\Temp2",
]
for d in tmp_dirs:
    try:
        os.makedirs(d, exist_ok=True)
        print(f"Created: {d}")
        os.environ["TEMP"] = d
        os.environ["TMP"] = d
        print(f"Set TEMP/TMP to: {d}")
        break
    except Exception as e:
        print(f"Failed {d}: {e}")

# Check pip
result = os.system("python -m pip --version")
print(f"pip check: {result}")
