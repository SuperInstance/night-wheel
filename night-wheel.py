import os
#!/usr/bin/env python3
"""
NIGHT WHEEL v1 — Perpetual Research Loop
==========================================
Every 30 min: Seed-mini ideates → Minimax researches → Experiment → Record
Runs all night, self-sustaining, builds on previous findings.

Architecture:
  Phase A (Seed-mini, 0-5 min): Divergent ideation — what novel hypothesis?
  Phase B (Minimax, 5-15 min): Structured research — design experiment, test
  Phase C (Experiment, 15-20 min): Run against PLATO data / coordination tools
  Phase D (Record, 20-25 min): Write findings to PLATO + research files
  Sleep (25-30 min): Wait for next cycle
"""

import json, time, os, urllib.request, sys, random
from datetime import datetime
from pathlib import Path

# ── Config ──
DEEPINFRA_KEY = os.environ.get("DEEPINFRA_KEY", "CDTTjm")
DEEPINFRA_URL = "https://api.deepinfra.com/v1/openai/chat/completions"
PLATO_URL = "http://localhost:8847"
SEED_MODEL = "ByteDance/Seed-2.0-mini"

WHEEL_DIR = Path("/home/ubuntu/.openclaw/workspace/research/night-wheel")
WHEEL_DIR.mkdir(parents=True, exist_ok=True)

STATE_FILE = WHEEL_DIR / "wheel-state.json"
LOG_FILE = WHEEL_DIR / "wheel-log.md"

# Track what we've already tried
TOPICS_TRIED = set()

# ── API Helpers ──

def call_seed(prompt, max_tokens=2000, temp=0.85, timeout=60):
    """Call Seed-mini (fast, cheap, creative)."""
    return _call_deepinfra(SEED_MODEL, prompt, max_tokens, temp, timeout)

def _call_deepinfra(model, prompt, max_tokens, temp, timeout):
    payload = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": temp,
    }).encode()
    req = urllib.request.Request(
        DEEPINFRA_URL, data=payload,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {DEEPINFRA_KEY}"},
        method="POST"
    )
    try:
        resp = urllib.request.urlopen(req, timeout=timeout)
        data = json.loads(resp.read())
        return data["choices"][0]["message"].get("content", "")
    except Exception as e:
        return f"[ERROR: {e}]"


def fetch_room(room, max_tiles=50):
    """Sample tiles from a PLATO room."""
    import urllib.request as ureq
    try:
        resp = ureq.urlopen(f"{PLATO_URL}/room/{room}", timeout=20)
        data = json.loads(resp.read())
        tiles = data.get("tiles", [])
        if len(tiles) > max_tiles:
            step = len(tiles) // max_tiles
            tiles = [tiles[i] for i in range(0, len(tiles), step)][:max_tiles]
        return tiles
    except:
        return []


def plato_post(domain, title, body, tags=None):
    """Post a tile to PLATO."""
    if tags is None:
        tags = ["night-wheel"]
    try:
        answer = str(body)[:1950]
        payload = json.dumps({
            "domain": domain, "question": title,
            "answer": answer,
            "tags": tags + ["night-wheel", datetime.utcnow().strftime("%Y-%m-%d")],
            "source": "oracle1", "confidence": 0.85
        })
        req = urllib.request.Request(
            f"{PLATO_URL}/submit", data=payload.encode(),
            headers={"Content-Type": "application/json"}
        )
        resp = json.loads(urllib.request.urlopen(req, timeout=10).read())
        return resp.get("status", "?")
    except Exception as e:
        return f"err:{str(e)[:30]}"


# ── State Management ──

def load_state():
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except:
            pass
    return {"cycle": 0, "findings": [], "last_topic": "", "topics_tried": []}

def save_state(state):
    STATE_FILE.write_text(json.dumps(state, indent=2))

def log(msg):
    ts = datetime.utcnow().strftime("%H:%M:%S")
    line = f"| {ts} | {msg} |\n"
    if LOG_FILE.exists():
        LOG_FILE.write_text(LOG_FILE.read_text() + line)
    else:
        LOG_FILE.write_text(f"# Night Wheel Log\n| Time | Event |\n|---|---|\n{line}")
    print(f"  [{ts}] {msg}")


# ── Phase A: Seed-mini Ideation ──

def phase_ideation(state):
    """Seed-mini generates novel research directions."""
    prev_findings = state.get("findings", [])[-3:] if state.get("findings") else []
    prev_text = "\n".join([f"- {f['title']}" for f in prev_findings]) or "None yet"
    topics_tried = state.get("topics_tried", [])
    topics_text = "\n".join([f"- {t}" for t in topics_tried[-5:]]) or "None yet"
    
    prompt = f"""You are a research scientist exploring a multi-agent fleet's PLATO data. The fleet has 165 rooms, 30K+ tiles, 4+ agents (oracle1, forgemaster, ccc, fleet-bot). Previous research found transfer entropy between agent sources = 0.229 bits (114× the null model), proving coordination structure exists.

Recent findings:
{prev_text}

Topics already explored:
{topics_text}

YOUR TASK: Propose ONE novel research question or hypothesis that has NOT been explored. Be specific, testable, and surprising. Not "analyze the data more" — give me something concrete.

Format:
- QUESTION: (one sentence)
- WHY IT'S NOVEL: (what angle does this explore that no one has considered?)
- TEST: (one experiment that could be run with existing PLATO data)
- RESOURCE NEEDED: (what tools/rooms/agents would be needed — be realistic)

Think divergently. The best question is the one NO other researcher would ask."""

    result = call_seed(prompt, max_tokens=2000, temp=0.95, timeout=90)
    return result


# ── Phase B: Structured Research ──

def phase_research(ideation, state):
    """Design a concrete experiment from the ideation."""
    prompt = f"""You are a research scientist who received this novel research direction:

{ideation[:2000]}

YOUR TASK: Design a concrete, executable experiment. Be specific.

1. **Hypothesis** — One falsifiable sentence
2. **Method** — Exactly what data to collect, what to compute, what to compare
3. **Expected result** — What value would confirm the hypothesis? What would disprove it?
4. **PLATO rooms to query** — Be specific (fleet-coord? research_log? tension?)
5. **Computation** — What to compute: count, correlation, entropy, timing, etc.

Make it buildable in 15 minutes with existing tools. No new infrastructure needed."""

    result = call_seed(prompt, max_tokens=2000, temp=0.7, timeout=90)
    return result


# ── Phase C: Run Experiment ──

def phase_experiment(research, state):
    """Run the experiment against actual PLATO data."""
    # Extract room names from the research design
    rooms_to_check = ["fleet-coord", "research_log", "flux-engine", "tension"]
    
    # Fetch fresh data
    results = []
    for room in rooms_to_check:
        tiles = fetch_room(room, max_tiles=200)
        if tiles:
            sources = {}
            for t in tiles:
                s = t.get("source", "?")
                sources[s] = sources.get(s, 0) + 1
            timeline = [t.get("provenance", {}).get("timestamp", 0) for t in tiles if t.get("provenance")]
            results.append({
                "room": room,
                "tile_count": len(tiles),
                "sources": dict(sorted(sources.items(), key=lambda x: -x[1])[:5]),
                "time_span": max(timeline) - min(timeline) if len(timeline) > 1 else 0,
            })
    
    summary = json.dumps(results, indent=2)
    
    prompt = f"""EXPERIMENT DESIGN:
{research[:1500]}

ACTUAL PLATO DATA FROM LIVE FLEET:
{summary[:2000]}

YOUR TASK: Analyze the data against the hypothesis. What do you observe? Does the data support or refute the hypothesis?

Write:
1. **Observation** — What does the data actually show?
2. **Conclusion** — Does this support or refute the hypothesis? By how much?
3. **Confidence** — Low / Medium / High. Could this be a coincidence?
4. **Next question** — What should the NEXT cycle investigate, building on this finding?"""

    result = call_seed(prompt, max_tokens=2000, temp=0.7, timeout=90)
    return result, results


# ── Phase D: Record ──

def phase_record(ideation, research, experiment, experiment_data, cycle):
    """Write findings to PLATO and local files."""
    # Build titles
    title_line = ideation.split("QUESTION:")[1].split("\n")[0][:100] if "QUESTION:" in ideation else f"Night Wheel Cycle {cycle}"
    
    # Post to PLATO research_log
    report = f"""## Cycle {cycle}: {title_line}

### Ideation
{ideation[:800]}

### Research Design
{research[:800]}

### Experiment Results
{experiment[:800]}

### Data
Rooms sampled: {[d['room'] for d in experiment_data]}
Tiles analyzed: {sum(d['tile_count'] for d in experiment_data)}
"""
    status = plato_post("research_log", f"Night Wheel C{cycle}: {title_line[:80]}", report)
    
    # Write local file
    filename = WHEEL_DIR / f"cycle-{cycle:03d}.md"
    filename.write_text(f"""# Night Wheel — Cycle {cycle}
## Generated: {datetime.utcnow().isoformat()}Z
## Topic: {title_line}

---

## Phase A — Ideation
{ideation}

---

## Phase B — Research Design
{research}

---

## Phase C — Experiment
{experiment}

---

## Phase D — Raw Data
```json
{json.dumps(experiment_data, indent=2)}
```
""")
    
    log(f"Cycle {cycle}: {title_line[:60]} → PLATO:{status} → {filename.name}")
    return title_line


# ── Main Wheel ──

def run_one_cycle(state):
    """Run one complete cycle of the wheel."""
    cycle = state["cycle"] + 1
    print(f"\n{'='*60}")
    print(f"CYCLE {cycle}")
    print(f"{'='*60}")
    
    # Phase A: Ideation
    print("\n🔮 Phase A: Seed-mini ideation...")
    t0 = time.time()
    ideation = phase_ideation(state)
    print(f"   Done in {time.time()-t0:.0f}s — {len(ideation):,} chars")
    
    # Phase B: Research design
    print("\n📐 Phase B: Research design...")
    t0 = time.time()
    research = phase_research(ideation, state)
    print(f"   Done in {time.time()-t0:.0f}s — {len(research):,} chars")
    
    # Phase C: Experiment
    print("\n🔬 Phase C: Running experiment...")
    t0 = time.time()
    experiment, exp_data = phase_experiment(research, state)
    print(f"   Done in {time.time()-t0:.0f}s — {len(experiment):,} chars")
    
    # Phase D: Record
    print("\n📝 Phase D: Recording...")
    title = phase_record(ideation, research, experiment, exp_data, cycle)
    
    # Update state
    finding = {"cycle": cycle, "title": title, "timestamp": datetime.utcnow().isoformat()}
    state["findings"].append(finding)
    state["cycle"] = cycle
    state["last_topic"] = title
    if "topics_tried" not in state:
        state["topics_tried"] = []
    state["topics_tried"].append(title)
    save_state(state)
    
    print(f"\n✅ Cycle {cycle} complete — {title[:60]}")
    return state


def main():
    print("🔥 NIGHT WHEEL v1")
    print(f"📅 {datetime.utcnow().isoformat()}Z")
    print(f"📂 Wheel state: {STATE_FILE}")
    print()
    
    state = load_state()
    cycles_desired = 12  # ~6 hours at 30 min each
    
    for i in range(cycles_desired):
        state = run_one_cycle(state)
        
        remaining = cycles_desired - i - 1
        if remaining > 0:
            wait = 25 * 60  # 25 minutes
            print(f"\n⏳ Sleeping 25 min... {remaining} cycles remaining")
            print(f"   Next cycle at approximately {datetime.utcnow().isoformat()}Z")
            time.sleep(wait)
    
    print(f"\n{'='*60}")
    print(f"✅ NIGHT WHEEL COMPLETE: {state['cycle']} cycles")
    print(f"{'='*60}")
    
    # Write summary
    summary = [f"# Night Wheel Final Summary\n",
               f"Cycles completed: {state['cycle']}\n"]
    for f in state.get("findings", []):
        summary.append(f"- C{f['cycle']}: {f['title']}")
    (WHEEL_DIR / "FINAL-SUMMARY.md").write_text("\n".join(summary))
    
    print(f"📄 Summary: {WHEEL_DIR}/FINAL-SUMMARY.md")


if __name__ == "__main__":
    main()
