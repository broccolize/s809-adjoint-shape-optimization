# Archived solver evidence

The `.txt.gz` files decompress byte-for-byte to the original local logs. SHA-256 hashes and original relative filenames are recorded in `data/source-manifest.json`. Optimizer receipts are retained as small plain-text files. The repository preparation did not rerun the solvers.

Raw logs include their original runtime paths and timestamps. Those are artifact metadata, not a reconstructed calendar of project work. The root audit tool reads compressed logs directly, matches physical coefficients to optimizer states, and checks saved sweep JSON against printed outputs. This establishes artifact consistency; it does not certify convergence, geometry correspondence or physical accuracy.
