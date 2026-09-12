import json
from collections import Counter
from dotenv import load_dotenv
from google import genai

load_dotenv()

client = genai.Client()
MODEL = "gemini-3.5-flash-lite"
TEMP = 0.7
ITERATIONS = 5  # Runs per strategy per review

# ANSI Colors
C_RESET = "\033[0m"
C_BOLD = "\033[1m"
C_DIM = "\033[2m"
C_CYAN = "\033[96m"
C_MAGENTA = "\033[95m"
C_GREEN = "\033[92m"
C_RED = "\033[91m"
C_YELLOW = "\033[93m"


def load_reviews():
    with open("data/reviews.json") as f:
        return json.load(f)


def generate(prompt):
    """Calls Gemini API with consistent model and temperature."""
    res = client.models.generate_content(
        model=MODEL,
        contents=prompt,
        config=genai.types.GenerateContentConfig(temperature=TEMP),
    )
    return res.text.strip() if res.text else ""


def build_prompts(review):
    """Returns (unconstrained_prompt, constrained_prompt) for a review."""
    unconstrained = f"Analyze the sentiment of the following review: {review}"
    constrained = f"""Analyze the sentiment of the following review: {review}

Output only a JSON object matching this schema:
```json
{{
    "sentiment": ("positive","negative","mixed"),
    "confidence": ("Low", "Medium", "High"),
    "key_aspects": list of exact phrases quoted directly from the review (no abstract summaries)
}}
```"""
    return unconstrained, constrained


def calculate_metrics(responses):
    """Calculates unique count and mode consistency percentage."""
    counts = Counter(responses)
    mode_count = counts.most_common(1)[0][1] if counts else 0
    return {
        "unique": len(counts),
        "consistency": (mode_count / len(responses)) * 100 if responses else 0.0,
        "total": len(responses),
    }


def run_strategy(name, prompt, color):
    """Executes N runs for a given prompt and collects responses."""
    print(f"{C_BOLD}{color}--- {name} ({ITERATIONS} runs) ---{C_RESET}")
    responses = []
    for i in range(ITERATIONS):
        resp = generate(prompt)
        responses.append(resp)
        preview = resp.replace("\n", " ")
        preview = preview[:57] + "..." if len(preview) > 60 else preview
        print(f"  {C_DIM}#{i+1:02d}{C_RESET} {color}●{C_RESET} {preview}")
    metrics = calculate_metrics(responses)
    return responses, metrics


def format_markdown_block(content, default_lang="text"):
    """Safely formats content in markdown code blocks, preventing broken nested backticks."""
    content = content.strip()
    if content.startswith("```") and content.endswith("```"):
        return content
    if "```" in content:
        return f"````{default_lang}\n{content}\n````"
    return f"```{default_lang}\n{content}\n```"


def save_markdown(filename, strategy_name, benchmark_data):
    """Saves prompts and responses to a clean markdown file."""
    with open(filename, "w", encoding="utf-8") as f:
        f.write(f"# {strategy_name}\n\n")
        for idx, item in enumerate(benchmark_data, 1):
            m = item["metrics"]
            f.write(f"## Review #{idx}\n\n> {item['review']}\n\n")
            f.write(f"- **Unique Responses:** {m['unique']} / {m['total']}\n")
            f.write(f"- **Consistency Score:** {m['consistency']:.1f}%\n\n")
            f.write(f"### Prompt\n\n{format_markdown_block(item['prompt'])}\n\n")
            f.write("### Responses\n\n")
            for r_idx, r in enumerate(item["responses"], 1):
                f.write(f"#### Run {r_idx}\n\n{format_markdown_block(r)}\n\n")
            f.write("---\n\n")


def print_summary_table(results):
    """Prints a clean aggregate summary table."""
    print(f"\n{C_YELLOW}{'=' * 72}{C_RESET}")
    print(f"{' ' * 22}{C_BOLD}{C_YELLOW}BENCHMARK EVALUATION SUMMARY{C_RESET}")
    print(f"{C_YELLOW}{'=' * 72}{C_RESET}")
    print(f"{C_BOLD}{'Review':<10} | {'Snippet':<24} | {'Unconstrained':<14} | {'Constrained':<12} | {'Delta Lift'}{C_RESET}")
    print(f"{C_DIM}{'-' * 72}{C_RESET}")

    total_u, total_c = 0.0, 0.0
    for idx, r in enumerate(results, 1):
        u_cons = r["unconstrained"]["metrics"]["consistency"]
        c_cons = r["constrained"]["metrics"]["consistency"]
        delta = c_cons - u_cons
        total_u += u_cons
        total_c += c_cons

        snippet = r["review"][:21] + "..." if len(r["review"]) > 24 else r["review"]
        d_color = C_GREEN if delta > 0 else (C_RED if delta < 0 else C_DIM)
        print(f"{f'Review {idx}':<10} | {C_DIM}{snippet:<24}{C_RESET} | {C_CYAN}{u_cons:>5.1f}%{'':<8}{C_RESET} | {C_MAGENTA}{c_cons:>5.1f}%{'':<6}{C_RESET} | {d_color}{delta:>+6.1f}%{C_RESET}")

    avg_u, avg_c = total_u / len(results), total_c / len(results)
    avg_delta = avg_c - avg_u
    avg_color = C_GREEN if avg_delta > 0 else C_DIM

    print(f"{C_DIM}{'-' * 72}{C_RESET}")
    print(f"{C_BOLD}{'AVERAGE':<10} | {'Across all reviews':<24} | {C_CYAN}{avg_u:>5.1f}%{'':<8}{C_RESET} | {C_MAGENTA}{avg_c:>5.1f}%{'':<6}{C_RESET} | {avg_color}{avg_delta:>+6.1f}%{C_RESET}")
    print(f"{C_YELLOW}{'=' * 72}{C_RESET}")

    if avg_c > avg_u:
        print(f"{C_BOLD}{C_GREEN}✔ VERDICT: Schema constraints reliably reduced non-determinism across reviews!{C_RESET}")
    print(f"{C_YELLOW}{'=' * 72}{C_RESET}\n")


if __name__ == "__main__":
    reviews = load_reviews()
    print(f"\n{C_BOLD}{C_YELLOW}=== LLM Non-Determinism Benchmark ({len(reviews)} reviews) ==={C_RESET}")
    print(f"{C_DIM}Model: {MODEL} | Temp: {TEMP} | Runs/Strategy: {ITERATIONS}{C_RESET}\n")

    results = []
    unconstrained_log, constrained_log = [], []

    for idx, review in enumerate(reviews, 1):
        print(f"{C_YELLOW}▶ [Review {idx}/{len(reviews)}]{C_RESET} \"{review}\"\n")
        u_prompt, c_prompt = build_prompts(review)

        u_responses, u_metrics = run_strategy("Strategy A: Unconstrained", u_prompt, C_CYAN)
        c_responses, c_metrics = run_strategy("Strategy B: Constrained", c_prompt, C_MAGENTA)
        print()

        results.append({
            "review": review,
            "unconstrained": {"prompt": u_prompt, "metrics": u_metrics, "responses": u_responses},
            "constrained": {"prompt": c_prompt, "metrics": c_metrics, "responses": c_responses},
        })
        unconstrained_log.append({"review": review, "prompt": u_prompt, "metrics": u_metrics, "responses": u_responses})
        constrained_log.append({"review": review, "prompt": c_prompt, "metrics": c_metrics, "responses": c_responses})

    print_summary_table(results)

    # Save Markdown & JSON logs
    save_markdown("output-unconstrained.md", "Strategy A: Unconstrained", unconstrained_log)
    save_markdown("output-constrained.md", "Strategy B: Constrained (JSON)", constrained_log)

    with open("output_results.json", "w", encoding="utf-8") as f:
        json.dump({"model": MODEL, "temperature": TEMP, "iterations": ITERATIONS, "results": results}, f, indent=2)

    print(f"{C_BOLD}Saved logs to:{C_RESET} output-unconstrained.md, output-constrained.md, output_results.json\n")
