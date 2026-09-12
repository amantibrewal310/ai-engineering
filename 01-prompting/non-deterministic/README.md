# LLM Non-Determinism & Variance Prototype

This prototype demonstrates a core challenge in applied AI: **Non-Determinism**. Even with the exact same prompt, parameters, and model, Large Language Models (LLMs) can produce varying outputs across multiple runs.

In production systems, variance is often an interface bug. If downstream microservices, databases, or parsers expect a specific format or exact keywords, slight linguistic variations will break your pipeline.

---

## The Concept

This experiment tests and measures how prompt constraints can collapse output variance across different sentiment types:

1. **Strategy A (Unconstrained Prompting):** Asking the LLM to analyze sentiment without prescribing format constraints.
2. **Strategy B (Constrained Prompting):** Using strict schema instructions (JSON with enums and verbatim quoted phrases) to anchor the model into a deterministic state.

### Why does this happen?
LLMs are probabilistic autoregressive token predictors. When prompts are open-ended, the model faces a high-entropy probability distribution with many valid paths. By anchoring the output to a strict schema and verbatim source text, we prune the branching tree at token 1, forcing generation through a narrow, predictable corridor.

---

## Dataset

The benchmark tests three distinct review archetypes in [data/reviews.json](data/reviews.json):

1. **Review 1 (Mixed / Nuanced):** Smartphone review with conflicting camera vs. battery sentiments.
2. **Review 2 (Unambiguous Positive):** Bus journey with positive punctuality, driver, and cleanliness.
3. **Review 3 (Unambiguous Negative):** Hotel stay with damp room and unresponsive staff.

---

## Setup

1. **Package Manager:** This repository uses [`uv`](https://docs.astral.sh/uv/) for Python and virtual environment management.
2. **Sync Dependencies:** From the repository root, install and sync the dependencies:
   ```bash
   uv sync
   ```
3. **API Key:** Add your Gemini API key in your `.env` file:
   ```bash
   GEMINI_API_KEY="your_api_key_here"
   ```

---

## Running the Prototype

Execute the benchmark script using `uv`:

```bash
uv run python main.py
```

---

## Benchmark Results

Evaluated with `gemini-3.5-flash-lite` at `temperature = 0.7` across 5 runs per strategy:

| Review | Category / Snippet | Unconstrained | Constrained | Delta Lift |
| :--- | :--- | :---: | :---: | :---: |
| **Review 1** | *The new smartphone is amazing, camera quality...* | 20.0% | **100.0%** | **+80.0%** |
| **Review 2** | *Bus left on time, seats were clean and driver...* | 20.0% | **100.0%** | **+80.0%** |
| **Review 3** | *The hotel room smelled of damp and nobody...* | 20.0% | **100.0%** | **+80.0%** |
| **AVERAGE** | **Across all 3 reviews** | **20.0%** | **100.0%** | **+80.0%** |

```text
✔ VERDICT: Schema constraints reliably reduced non-determinism across reviews!
```

---

## Evaluation Metrics

* **Unique Responses:** The number of distinct strings generated across N iterations.
* **Consistency Score:** The percentage of runs matching the modal (most frequent) response:
  > `(Count of Most Common Response / Total Runs) × 100%`
* **Delta Lift:** The difference in consistency score:
  > `Constrained Consistency - Unconstrained Consistency`

---

## Output Artifacts

Running the prototype generates:
* **[output-unconstrained.md](output-unconstrained.md):** Raw outputs and prompts for Strategy A across all reviews.
* **[output-constrained.md](output-constrained.md):** Raw outputs and prompts for Strategy B across all reviews.
* **[output_results.json](output_results.json):** Full machine-readable export with metadata, metrics, and raw response arrays.

For a detailed breakdown of failure modes (e.g., why `"reason": text` or abstract taxonomy tags cause 60% variance leaks), see **[LEARNINGS.md](LEARNINGS.md)**.
