import re
import matplotlib.pyplot as plt

with open("logOpt.txt", "r") as f:
    text = f.read()

# Extract CD and CL values
cd_vals = [float(x) for x in re.findall(r"CD: (\S+) final:", text)]
cl_vals = [float(x) for x in re.findall(r"CL: (\S+) final:", text)]

# Filter out garbage startup values (keep only physically realistic ones)
cd_vals = [x for x in cd_vals if 0.001 < x < 0.1]
cl_vals = [x for x in cl_vals if -1.0 < x < 3.0]

baseline_cd = cd_vals[0]
optimized_cd = cd_vals[-1]
reduction = (baseline_cd - optimized_cd) / baseline_cd * 100

fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 7))
fig.suptitle("S809 Airfoil Optimization History\nRe=5e5, Target CL=0.4", fontsize=14)

ax1.plot(cd_vals, 'b-')
ax1.set_ylabel("CD")
ax1.set_xlabel("Flow Solution #")
ax1.grid(True)
ax1.axhline(y=baseline_cd, color='r', linestyle='--', label=f'Baseline CD={baseline_cd:.5f}')
ax1.axhline(y=optimized_cd, color='g', linestyle='--', label=f'Optimized CD={optimized_cd:.5f}')
ax1.legend()

ax2.plot(cl_vals, 'r-')
ax2.set_ylabel("CL")
ax2.set_xlabel("Flow Solution #")
ax2.grid(True)
ax2.axhline(y=0.4, color='k', linestyle='--', label='Target CL=0.4')
ax2.legend()

plt.tight_layout()
plt.savefig("optimization_history.png", dpi=150)
print("Saved optimization_history.png")
print(f"Baseline CD: {baseline_cd:.6f}")
print(f"Optimized CD: {optimized_cd:.6f}")
print(f"CD reduction: {reduction:.2f}%")
