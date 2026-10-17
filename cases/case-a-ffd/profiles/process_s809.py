import numpy as np

# Read the file, skip header
coords = []
with open('s809.dat', 'r') as f:
    lines = f.readlines()
    for line in lines[1:]:  # skip "NREL's S809 Airfoil" header
        parts = line.strip().split()
        if len(parts) == 2:
            coords.append([float(parts[0]), float(parts[1])])

coords = np.array(coords)

# Find leading edge index (minimum x value)
le_idx = np.argmin(coords[:, 0])
print(f"Leading edge found at index {le_idx}: x={coords[le_idx,0]}, y={coords[le_idx,1]}")

# Upper surface (SS): reverse so it goes LE -> TE
upper = coords[:le_idx+1][::-1]

# Lower surface (PS): already goes LE -> TE
lower = coords[le_idx:]

# Fix LE point to exactly (0, 0) on both
upper[0] = [0.0, 0.0]
lower[0] = [0.0, 0.0]

# Truncate at x = 0.998 (MD requirement: ~99.8% chord)
upper = upper[upper[:, 0] <= 0.998]
lower = lower[lower[:, 0] <= 0.998]

# Save in same format as NACA0012 profiles
np.savetxt('S809SS.profile', upper, fmt='%10.7f')
np.savetxt('S809PS.profile', lower, fmt='%10.7f')

print(f"S809SS.profile: {len(upper)} points, last x = {upper[-1,0]:.6f}")
print(f"S809PS.profile: {len(lower)} points, last x = {lower[-1,0]:.6f}")
print("Done")