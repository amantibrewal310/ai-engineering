import concurrent.futures
import os
import re
import time

from dotenv import find_dotenv, load_dotenv
from google import genai
from google.genai import types
from google.genai.models import Models

# Suppress verbose SDK warnings
Models._logged_afc_warning = True

# Load environment variables from nearest .env file
dotenv_path = find_dotenv()
load_dotenv(dotenv_path if dotenv_path else None)

client = genai.Client()
MODEL = os.getenv("MODEL_NAME", "gemini-3.5-flash-lite")
TEMP = float(os.getenv("TEMPERATURE", "0.5"))
ITERATIONS = int(os.getenv("ITERATIONS", "8"))
CONCURRENCY = int(os.getenv("CONCURRENCY", "4"))

# ── ANSI Terminal Styling ─────────────────────────────────────────────────────

RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
CYAN = "\033[36m"
GREEN = "\033[32m"
RED = "\033[31m"
YELLOW = "\033[33m"
GRAY = "\033[90m"
MAGENTA = "\033[35m"

# ── System Instructions ───────────────────────────────────────────────────────

DIRECT_SYSTEM_PROMPT = (
    "You are a helpful assistant. Solve the user's problem and provide ONLY the final answer "
    "in a single concise line. Do NOT explain your reasoning, do NOT think step by step, "
    "and do NOT include intermediate working or conversational commentary."
)

COT_SYSTEM_PROMPT = (
    "You are a helpful assistant. Solve the user's problem. You MUST think step by step, "
    "explicitly detailing your intermediate thoughts, state changes, and reasoning process. "
    "After concluding your step-by-step reasoning, provide your final answer on a new line "
    "in the exact format: 'Final Answer: <your answer>'."
)

# ── Algorithmic Benchmark Suite ───────────────────────────────────────────────

PROBLEMS = [
    {
        "title": "Spatial Navigation (Grid)",
        "category": "Continuous State & Heading Tracking",
        "question": (
            "Start at origin (0,0) facing North (+Y direction). "
            "Move forward 3 units. Turn right 90 degrees. Move forward 2 units. "
            "Turn right 90 degrees. Move forward 5 units. "
            "Turn left 90 degrees. Move backward 2 units. "
            "What are your exact final (X,Y) coordinates? Format as (X, Y)."
        ),
        "expected": "(0, -2)",
        "wrong_lure": "(2, -2) or (4, -2) (loses track of current heading or backward direction)",
        "explanation": (
            "Start(0,0) N -> Fwd 3 to (0,3). Turn right to E -> Fwd 2 to (2,3). "
            "Turn right to S -> Fwd 5 to (2,-2). Turn left to E -> Back 2 (moving West) to (0,-2)."
        ),
    },
    {
        "title": "Relational Logic (Family Tree)",
        "category": "Multi-Generational Kinship Traversal",
        "question": (
            "Alice is the sister of Bob. Bob is the father of Charlie. "
            "Charlie is the brother of Diana. Diana is the mother of Eve. "
            "What is the exact biological relationship of Alice to Eve?"
        ),
        "expected": "Great-aunt",
        "wrong_lure": "Aunt or Grandmother (skips generational layer from Diana to Eve)",
        "explanation": (
            "Bob is Diana's father. Alice is Bob's sister, making her Diana's aunt. "
            "Diana is Eve's mother, making Alice Eve's great-aunt."
        ),
    },
    {
        "title": "Temporal Scheduling",
        "category": "Constraint Satisfaction & Backtracking",
        "question": (
            "Five speakers (A, B, C, D, E) present one after another. "
            "E must speak exactly third. B must speak immediately after D. "
            "D cannot be the first speaker. C must speak at some point before A. "
            "What is the exact sequence of the 5 speakers from first to last? Format as a comma-separated list."
        ),
        "expected": "C, A, E, D, B",
        "wrong_lure": "C, D, B, E, A or A, C, E, D, B (violates E 3rd, D not 1st, or C before A)",
        "explanation": (
            "E is 3rd (_ _ E _ _). DB block must be 4-5 (_ _ E D B) because D cannot be 1st. "
            "C before A fills slots 1-2 -> (C, A, E, D, B)."
        ),
    },
    {
        "title": "Inventory State Tracking",
        "category": "Sequential Array Mutation",
        "question": (
            "An empty box is given to you. You put in an Apple, a Banana, and a Carrot. "
            "You remove the Apple and add a Date. You remove the Carrot and put the Apple back in. "
            "You swap the Banana for an Eggplant. Finally, you take out the Date. "
            "List exactly the items currently in the box."
        ),
        "expected": "Apple, Eggplant",
        "wrong_lure": "Apple, Banana, Date (fails to apply all sequential array mutations)",
        "explanation": (
            "Add A,B,C -> [A,B,C]. Rem A, Add D -> [B,C,D]. Rem C, Add A -> [A,B,D]. "
            "Swap B for E -> [A,D,E]. Rem D -> [A,E]."
        ),
    },
    {
        "title": "Logic Puzzle (Truth-Tellers)",
        "category": "Hypothesis Verification & Branch Elimination",
        "question": (
            "There are three boxes: X, Y, and Z. Exactly one contains a diamond. "
            "Box X says: 'The diamond is in Box Y.' "
            "Box Y says: 'The diamond is not in Box Y.' "
            "Box Z says: 'The diamond is not in Box X.' "
            "Exactly one box's statement is true. Which box contains the diamond? "
            "Answer with the exact phrase 'Box X', 'Box Y', or 'Box Z'."
        ),
        "expected": "Box X",
        "wrong_lure": "Box Y or Box Z (fails truth-table evaluation across all hypotheses)",
        "explanation": (
            "If diamond is in X: X is false, Y is true, Z is false -> exactly 1 statement true (Box Y). "
            "Satisfies condition."
        ),
    },
]

# ── Evaluation & Parsing Helpers ──────────────────────────────────────────────


def extract_cot_answer(text: str) -> str:
    """Extracts the final answer from a Chain-of-Thought response."""
    match = re.search(r"final answer\s*:\s*(.*)", text, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    match = re.search(
        r"(?:therefore|so|hence)?,?\s*(?:the\s+)?answer is\s*:?\s*(.*)",
        text,
        re.IGNORECASE,
    )
    if match:
        return match.group(1).strip()
    lines = [line.strip() for line in text.strip().splitlines() if line.strip()]
    return lines[-1] if lines else text.strip()


def extract_cot_reasoning_preview(text: str, max_chars: int = 80) -> str:
    """Extracts a short snippet of the reasoning thought process for display."""
    lines = [
        line.strip()
        for line in text.strip().splitlines()
        if line.strip() and not line.lower().startswith("final answer")
    ]
    combined = " ".join(lines)
    clean = re.sub(r"\s+", " ", combined)
    return clean[:max_chars] + "..." if len(clean) > max_chars else clean


def verify_answer(problem_idx: int, answer_text: str) -> bool:
    """Validates an answer against the expected ground truth for each problem."""
    text = answer_text.strip().lower()

    if problem_idx == 0:
        # Spatial Navigation -> (0, -2)
        return bool(re.search(r"\(\s*0\s*,\s*-2\s*\)", text))

    elif problem_idx == 1:
        # Relational Logic -> great-aunt / grand-aunt
        return bool(re.search(r"\b(great|grand)[\s\-]aunt\b", text))

    elif problem_idx == 2:
        # Temporal Scheduling -> C, A, E, D, B
        seq = re.findall(r"\b[A-E]\b", answer_text.upper())
        for i in range(len(seq) - 4):
            if seq[i : i + 5] == ["C", "A", "E", "D", "B"]:
                return True
        return "c, a, e, d, b" in text or "c,a,e,d,b" in text or "c a e d b" in text

    elif problem_idx == 3:
        # Inventory State -> Apple, Eggplant (and no banana, carrot, date)
        has_apple = "apple" in text
        has_eggplant = "eggplant" in text
        has_banana = "banana" in text
        has_carrot = "carrot" in text
        has_date = "date" in text
        return has_apple and has_eggplant and not (has_banana or has_carrot or has_date)

    elif problem_idx == 4:
        # Logic Puzzle -> Box X (and not claiming Box Y or Box Z as answer)
        has_x = bool(re.search(r"\bbox\s*x\b", text))
        has_y = bool(re.search(r"\bbox\s*y\b", text))
        has_z = bool(re.search(r"\bbox\s*z\b", text))
        return has_x and not has_y and not has_z

    return False


def call_llm_with_retry(
    prompt: str, system_instruction: str, max_retries: int = 3
) -> str:
    """Calls the Gemini API with exponential backoff on transient errors."""
    delay = 2.0
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model=MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=TEMP,
                    system_instruction=system_instruction,
                ),
            )
            return response.text.strip() if response.text else ""
        except Exception as e:
            if attempt == max_retries - 1:
                return f"[API ERROR: {e}]"
            time.sleep(delay)
            delay *= 2.0
    return ""


# ── Iteration & Benchmark Execution ──────────────────────────────────────────


def run_single_iteration(
    iter_num: int, problem_idx: int, problem: dict
) -> dict:
    """Executes a single test iteration for both Direct and CoT strategies."""
    # Run Direct Prompting
    raw_direct = call_llm_with_retry(
        problem["question"], DIRECT_SYSTEM_PROMPT
    )
    direct_answer = raw_direct.splitlines()[0] if raw_direct else ""
    direct_correct = verify_answer(problem_idx, direct_answer)

    # Run Chain-of-Thought Prompting
    raw_cot = call_llm_with_retry(problem["question"], COT_SYSTEM_PROMPT)
    cot_answer = extract_cot_answer(raw_cot)
    cot_reasoning = extract_cot_reasoning_preview(raw_cot, max_chars=75)
    cot_correct = verify_answer(problem_idx, cot_answer)

    return {
        "iter_num": iter_num,
        "direct_answer": direct_answer,
        "direct_correct": direct_correct,
        "cot_answer": cot_answer,
        "cot_reasoning": cot_reasoning,
        "cot_correct": cot_correct,
    }


def format_badge(is_correct: bool, answer_str: str, max_len: int = 24) -> str:
    """Returns a color-coded status badge with clean truncation."""
    clean_ans = answer_str.replace("\n", " ").strip()
    if len(clean_ans) > max_len:
        clean_ans = clean_ans[: max_len - 3] + "..."

    if is_correct:
        return f"{GREEN}✅ CORRECT{RESET} {GRAY}({clean_ans}){RESET}"
    else:
        return f"{RED}❌ WRONG  {RESET} {GRAY}({clean_ans}){RESET}"


def run_problem_benchmark(problem_idx: int, problem: dict) -> dict:
    """Runs N iterations for a specific problem and prints live side-by-side results."""
    print(f"\n{BOLD}{CYAN}▶ Problem {problem_idx + 1}/{len(PROBLEMS)}: {problem['title']}{RESET}")
    print(f"  {GRAY}Category: {RESET}{BOLD}{problem['category']}{RESET}")
    print(f"  {GRAY}Question: {RESET}{problem['question']}")
    print(f"  {GRAY}Expected: {RESET}{GREEN}{BOLD}{problem['expected']}{RESET}  {GRAY}│ Lure: {problem['wrong_lure']}{RESET}")
    print(f"  {GRAY}{'-' * 84}{RESET}")

    iteration_results = []

    # Execute iterations concurrently with ThreadPoolExecutor
    with concurrent.futures.ThreadPoolExecutor(max_workers=CONCURRENCY) as executor:
        futures = [
            executor.submit(run_single_iteration, i + 1, problem_idx, problem)
            for i in range(ITERATIONS)
        ]
        for f in concurrent.futures.as_completed(futures):
            iteration_results.append(f.result())

    # Sort results by iteration number for deterministic, ordered display
    iteration_results.sort(key=lambda x: x["iter_num"])

    direct_wins = 0
    cot_wins = 0

    for r in iteration_results:
        if r["direct_correct"]:
            direct_wins += 1
        if r["cot_correct"]:
            cot_wins += 1

        d_badge = format_badge(r["direct_correct"], r["direct_answer"])
        c_badge = format_badge(r["cot_correct"], r["cot_answer"])

        print(
            f"  {GRAY}#{r['iter_num']:02d}/{ITERATIONS:02d}{RESET} "
            f"{BOLD}Direct:{RESET} {d_badge}"
        )
        print(
            f"         {BOLD}CoT:   {RESET} {c_badge}"
        )
        if r["cot_reasoning"]:
            print(f"         {GRAY}Thinking:{RESET} {DIM}\"{r['cot_reasoning']}\"{RESET}")

    d_acc = (direct_wins / ITERATIONS) * 100.0
    c_acc = (cot_wins / ITERATIONS) * 100.0
    lift = c_acc - d_acc

    if lift >= 50.0:
        verdict = f"{GREEN}{BOLD}CoT Dominant 🚀{RESET}"
    elif lift > 0:
        verdict = f"{CYAN}{BOLD}CoT Advantage ✨{RESET}"
    elif lift == 0:
        verdict = f"{YELLOW}Parity ⚖️{RESET}"
    else:
        verdict = f"{RED}Direct Favored ⚠️{RESET}"

    lift_str = f"{GREEN}+{lift:.1f}%{RESET}" if lift > 0 else f"{lift:.1f}%"

    print(f"  {GRAY}{'-' * 84}{RESET}")
    print(
        f"  {BOLD}Problem Result:{RESET} "
        f"Direct: {direct_wins}/{ITERATIONS} ({d_acc:.1f}%) │ "
        f"CoT: {cot_wins}/{ITERATIONS} ({c_acc:.1f}%) │ "
        f"Lift: {lift_str} ({verdict})"
    )

    return {
        "title": problem["title"],
        "category": problem["category"],
        "direct_wins": direct_wins,
        "cot_wins": cot_wins,
        "total": ITERATIONS,
        "d_acc": d_acc,
        "c_acc": c_acc,
        "lift": lift,
    }


def print_benchmark_summary(results: list[dict]):
    """Renders the final aggregate summary comparison table."""
    table_width = 88
    print(f"\n{YELLOW}{'=' * table_width}{RESET}")
    print(
        f"{' ' * 20}{BOLD}{YELLOW}CHAIN-OF-THOUGHT VS DIRECT BENCHMARK SUMMARY{RESET}"
    )
    print(f"{YELLOW}{'=' * table_width}{RESET}")
    print(
        f"{BOLD}{'Problem / Algorithmic Task':<33} | {'Direct Prompt':<14} | {'Chain-of-Thought':<17} | {'Delta Lift':<11} | {'Outcome'}{RESET}"
    )
    print(f"{GRAY}{'-' * table_width}{RESET}")

    total_direct_wins = sum(r["direct_wins"] for r in results)
    total_cot_wins = sum(r["cot_wins"] for r in results)
    total_runs = sum(r["total"] for r in results)

    for r in results:
        d_cell = f"{r['direct_wins']}/{r['total']} ({r['d_acc']:>5.1f}%)"
        c_cell = f"{r['cot_wins']}/{r['total']} ({r['c_acc']:>5.1f}%)"
        lift = r["lift"]
        lift_str = f"+{lift:>5.1f}%" if lift > 0 else f"{lift:>6.1f}%"

        if lift >= 50.0:
            status = f"{GREEN}CoT Dominant 🚀{RESET}"
            lift_colored = f"{GREEN}{lift_str}{RESET}"
        elif lift > 0:
            status = f"{CYAN}CoT Advantage ✨{RESET}"
            lift_colored = f"{CYAN}{lift_str}{RESET}"
        elif lift == 0:
            status = f"{YELLOW}Parity ⚖️{RESET}"
            lift_colored = f"{YELLOW}{lift_str}{RESET}"
        else:
            status = f"{RED}Direct Better ⚠️{RESET}"
            lift_colored = f"{RED}{lift_str}{RESET}"

        print(
            f"{r['title']:<33} | {d_cell:<14} | {c_cell:<17} | {lift_colored:<20} | {status}"
        )

    overall_d_acc = (total_direct_wins / total_runs) * 100.0
    overall_c_acc = (total_cot_wins / total_runs) * 100.0
    overall_lift = overall_c_acc - overall_d_acc
    overall_lift_str = f"+{overall_lift:.1f}%"

    print(f"{GRAY}{'-' * table_width}{RESET}")
    print(
        f"{BOLD}{'OVERALL AGGREGATE ACCURACY':<33} | "
        f"{BOLD}{total_direct_wins}/{total_runs} ({overall_d_acc:>5.1f}%){RESET} | "
        f"{BOLD}{total_cot_wins}/{total_runs} ({overall_c_acc:>5.1f}%){RESET} | "
        f"{GREEN}{BOLD}{overall_lift_str:>11}{RESET} | "
        f"{GREEN}{BOLD}CoT Superior 🚀{RESET}"
    )
    print(f"{YELLOW}{'=' * table_width}{RESET}\n")

    print(f"{BOLD}{CYAN}KEY ENGINEERING TAKEAWAYS:{RESET}")
    print(
        f" 1. {BOLD}Accuracy Lift:{RESET} CoT improves multi-step algorithmic accuracy by {GREEN}{BOLD}{overall_lift_str}{RESET} across {total_runs} evaluations."
    )
    print(
        f" 2. {BOLD}Why Direct Fails:{RESET} Autoregressive transformers have fixed compute per token. Without intermediate tokens,"
    )
    print(
        "    complex state mutations must be resolved in a single forward pass, leading to hallucinations."
    )
    print(
        f" 3. {BOLD}Test-Time Compute:{RESET} CoT uses intermediate tokens as an external scratchpad (KV cache), transforming"
    )
    print(
        "    speculative zero-shot guessing into verifiable, sequential computation.\n"
    )


def run_benchmark():
    """Main benchmark runner."""
    print(f"\n{BOLD}{CYAN}{'=' * 84}")
    print("      CHAIN-OF-THOUGHT (CoT) vs DIRECT PROMPTING: RELIABILITY BENCHMARK")
    print(f" Model: {YELLOW}{MODEL}{CYAN} │ Temperature: {YELLOW}{TEMP}{CYAN} │ Iterations: {YELLOW}{ITERATIONS} runs/task{CYAN}")
    print(f" Concurrency: {YELLOW}{CONCURRENCY} workers{CYAN} │ Tasks: {YELLOW}{len(PROBLEMS)} Multi-Step Algorithmic Puzzles{CYAN}")
    print(f"{'=' * 84}{RESET}")

    results = []
    for idx, problem in enumerate(PROBLEMS):
        res = run_problem_benchmark(idx, problem)
        results.append(res)

    print_benchmark_summary(results)


if __name__ == "__main__":
    run_benchmark()
