# Engineering Learnings: LLM Non-Determinism & Variance

A comprehensive log of insights, failure modes, and mental models discovered while designing and benchmarking this prototype.

---

## 1. The Core Problem: Determinism in Probabilistic Systems

In traditional software, functions are deterministic:
> `Input X` ➔ `f(X)` ➔ `Output Y`

LLMs break this foundation. They are autoregressive token predictors governed by conditional probability:
> `P(Token_t | Token_1, Token_2, ..., Token_{t-1})`

Even with a fixed prompt, low temperatures, and identical inputs, non-determinism naturally occurs because:
1. **Sampling Stochasticity:** If temperature > 0, the model samples from a probability distribution over the entire vocabulary.
2. **GPU Concurrency:** Non-associative floating-point addition across distributed GPU clusters can lead to slight numerical variations in logit calculations, occasionally flipping the top token.
3. **Open-Ended Degrees of Freedom:** Natural language offers dozens of syntactically different ways to express identical semantic thoughts.

In production pipelines, downstream parsers, APIs, and databases require strict, reliable contracts. **Variance is often a production bug.**

---

## 2. The Mental Model: The Funnel of Probability

Text generation is an autoregressive branching tree:

```
[Start]
  │
  ├── ("The") ──> ("sentiment") ──> ("is mixed...")  [Divergent Path A]
  │
  ├── ("Overall") ──> (",") ──> ("the review...")    [Divergent Path B]
  │
  └── ("Based") ──> ("on") ──> ("the text...")       [Divergent Path C]
```

* **Unconstrained Prompting (Wide Funnel):** At token 1, the model has thousands of viable starting tokens. Because generation is autoregressive, whichever token is picked sets off a cascading domino effect, resulting in completely different sentence structures.
* **Constrained Prompting (Narrow Funnel):** Forcing a strict contract prunes the branching tree at the root. Token 1 must be `{`, token 2 must be `"sentiment": "`, and token 3 is restricted to a tight enum set (`positive`, `negative`, `mixed`). The wide probability landscape collapses into a narrow corridor.

---

## 3. The Iterative Journey & Failure Modes

During this prototype, we walked through three distinct iterations before achieving true determinism:

### Failure Mode 1: The "Entropy Leak" in Schemas (Consistency: ~20%)
* **Schema attempted:**
  ```json
  {
    "sentiment": "positive" | "negative" | "neutral",
    "confidence": number, // 0-100
    "reason": "text"
  }
  ```
* **What went wrong:**
  * `"confidence": number` — The model randomly guessed floating numbers (e.g., 75, 80, 85).
  * `"reason": "text"` — Asking for open-ended natural language explanations invited infinite linguistic variation.
* **Lesson:** Simply wrapping an output in JSON syntax does **not** make it deterministic. If the schema contains open-ended text fields, you are inviting entropy directly into your structure.

---

### Failure Mode 2: The Abstract Taxonomy Leak (Consistency: ~40%)
* **Schema attempted:**
  ```json
  {
    "sentiment": ("positive", "negative", "mixed"),
    "confidence": ("Low", "Medium", "High"),
    "key_aspects": list of strings
  }
  ```
* **What went wrong:**
  * For Review 1 (smartphone specs like *"camera quality"*, *"battery life"*), consistency was high (80%) because the nouns were explicit in the text.
  * For Review 2 (*"Bus left on time..."*) and Review 3 (*"hotel room smelled..."*), consistency collapsed to **40%**.
  * The model attempted to invent abstract category tags and alternated between synonyms:
    * `"punctuality"` vs `"departure time"`
    * `"driver behavior"` vs `"driver politeness"`
    * `"reception availability"` vs `"reception responsiveness"`
* **Lesson:** When a field asks for conceptual aspects without strict grounding, the model acts as an unconstrained taxonomy engine, introducing high semantic variance across runs.

---

### The Breakthrough: Verbatim Anchoring & Enums (Consistency: 100%)
* **Schema updated:**
  ```json
  {
    "sentiment": ("positive", "negative", "mixed"),
    "confidence": ("Low", "Medium", "High"),
    "key_aspects": list of exact phrases quoted directly from the review (no abstract summaries)
  }
  ```
* **The Result:**
  * Review 1 (Mixed): **100.0% Consistency** (was 20% in unconstrained)
  * Review 2 (Positive): **100.0% Consistency** (was 20% in unconstrained)
  * Review 3 (Negative): **100.0% Consistency** (was 20% in unconstrained)
  * **Overall Lift:** **+80.0%**
* **Lesson:** Forcing the model to extract **exact quoted substrings** rather than inventing abstract tags eliminates synonym ambiguity and locks the token path into a deterministic output.

---

## 4. Benchmark Summary Across 3 Review Archetypes

| Review Type | Review Text Snippet | Strategy A (Unconstrained) | Strategy B (Constrained) | Delta Lift |
| :--- | :--- | :---: | :---: | :---: |
| **Review 1 (Mixed)** | *"The new smartphone is amazing, camera quality is top-notch but battery..."* | 20.0% | **100.0%** | **+80.0%** |
| **Review 2 (Positive)** | *"Bus left on time, seats were clean and the driver was polite..."* | 20.0% | **100.0%** | **+80.0%** |
| **Review 3 (Negative)** | *"The hotel room smelled of damp and nobody answered the reception..."* | 20.0% | **100.0%** | **+80.0%** |
| **AVERAGE** | **Across all 3 reviews** | **20.0%** | **100.0%** | **+80.0%** |

---

## 5. Summary of Rules for Production AI Engineering

1. **Never use free-form text fields if you need raw string determinism:** Replace `"reason": string` with predefined enums or categorical flags.
2. **Anchor extracted entities to source text:** Instruct the model to extract *"exact verbatim substrings"* rather than generating conceptual labels.
3. **Use categorical enums instead of continuous numbers:** Replace arbitrary ratings (`0-100`) with discrete buckets (`"Low" | "Medium" | "High"`).
4. **Isolate prompt effects by testing at non-zero temperature:** Running tests at `temperature = 0.7` proves whether your prompt constraints are truly pruning degrees of freedom, rather than relying on `temperature = 0.0` as a crutch.
5. **Differentiate Syntactic vs. Semantic Evaluation:**
   * *Syntactic Determinism:* Exact raw string/JSON match across runs.
   * *Semantic Determinism:* Invariance of the underlying decision (e.g. sentiment verdict), even if phrasing varies slightly.
