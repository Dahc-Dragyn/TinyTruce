import re

log_path = r"c:\Antigravity projects\TinyTruce\tinytruce_simulation.log"

try:
    with open(log_path, "r", encoding="utf-8") as f:
        content = f.read()
except UnicodeDecodeError:
    with open(log_path, "r", encoding="latin-1") as f:
        content = f.read()

# Look for [Donald J. Trump]'s action:
# 2026-03-02 10:42:33,581 - tinytroupe - DEBUG - [Donald J. Trump] Donald J. Trump's action: {'type': 'TALK', ...}
pattern = re.compile(r"\[Donald J. Trump\] Donald J. Trump's action: (\{.*?\})")
matches = pattern.findall(content)

print(f"Extracted {len(matches)} total successfully parsed actions for Donald J. Trump.\n")

if matches:
    print("--- Last 12 Actions ---")
    for i, m in enumerate(matches[-12:]):
        print(f"Action {i+1}: {m}\n")
else:
    # Try a broader search just for the name and the word action
    pattern2 = re.compile(r"\[Donald J. Trump\].*?action.*?\n(.*?)\n", re.IGNORECASE)
    matches2 = pattern2.findall(content)
    print(f"Broad search found {len(matches2)} matches.")
    for i, m in enumerate(matches2[-5:]):
        print(f"Broad Action {i+1}: {m}\n")
