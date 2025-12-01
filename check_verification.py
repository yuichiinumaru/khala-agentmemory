import os

files = [
    "khala/application/verification/debate_system.py",
    "khala/application/verification/self_verification.py",
    "khala/application/verification/verification_gate.py"
]

found = []
for f in files:
    if os.path.exists(f):
        found.append(f)

print(found)
