# Test record — 2026-10-14

Environment: container, CPython 3.13, PyTorch 2.10 CPU (not the user's Mac).

- Unit/integration: `PYTHONPATH=src pytest -q` -> **8 passed**.
- Editable install verified using `python -m pip install --no-build-isolation --no-deps -e .`.
- `mirage-ot synthetic-fixture ...` -> successfully wrote dummy JSONL.
- `mirage-ot prepare ...` -> matrix `(65, 6, 8)` with 3 network and 3 process channels.
- `mirage-ot fit --epochs 2 --max-steps 12 --hidden 16 ...` -> successfully trained and saved weights.
- `mirage-ot evaluate ...` -> normalized MAE 0.49463 on the **same toy data**.
- `mirage-ot graph ...` -> 6 nodes and 12 directed display edges, JSON/GraphML/HTML exported.
- Test ZIP containing compressed dummy IPAL state and dummy PCAP -> read successfully in-place without extraction, physical.zip not read.
- A disposable orphan branch was created safely with `git worktree add --orphan -b mirage-ot` under Git 2.47.
- No real Sherlock v3 archive has been mounted or tested; no generalization, attack classification, incident analysis or link correctness result has been measured.
- Ollama was not called and no real LLM report was generated.

Nothing in this file should appear as effectiveness metrics in an academic paper.
