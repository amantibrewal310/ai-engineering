# ai-engineering

Hands-on practice implementations of applied AI engineering topics — prompting, retrieval,
agent loops, multi-agent systems, evaluation, and production concerns. Python throughout.

Each topic gets small, runnable examples. The point is to build the thing rather than read
about it.

## Topics

**01 — Prompting**
Stochastic behaviour of LLMs · chain-of-thought and few-shot prompting · prompt failure modes ·
structured outputs · prompting reliably

**02 — Tool Use and RAG**
Tool schema design · parallel tool calls · hybrid search and metadata filtering · re-ranking
(cross-encoders and bi-encoders) · query rewriting · semantic caching

**03 — Agent Loops**
Observe-think-act · ReAct · plan-and-execute · Ralph loop · checkpoint and resume ·
human in the loop

**04 — Multi-Agent Systems and Memory**
Memory architecture · working memory budgeting · summarization and write strategies ·
orchestrator + specialist · critic + refiner · mixture of agents · deadlocks

**05 — Evaluation and Safety**
What makes a good eval · LLM-as-judge · where to place evals · human evals · exploratory and
adversarial evals · regression harnesses

**06 — Production**
Self-evolving agents · prompt caching · observability · common gotchas

## Structure

```
.
├── 01-prompting/
├── 02-tools-and-rag/
├── 03-agent-loops/
├── 04-multi-agent-and-memory/
├── 05-evaluation/
├── 06-production/
└── system-designs/     # end-to-end design write-ups
```

Every example directory carries its own README covering what it does, how to run it, and what
I took away from it.

## Running things

Python 3.14. Dependencies and setup are documented per example.

## License

MIT
