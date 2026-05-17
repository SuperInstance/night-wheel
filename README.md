# night-wheel

Perpetual research loop for multi-agent fleet analysis. Runs autonomous cycles of:
- **Phase A** (Seed-mini): Divergent ideation — proposes novel research questions
- **Phase B** (Seed-mini): Structured research design — formulates hypothesis, method, expected result
- **Phase C** (Seed-mini): Experiment — queries live PLATO data, computes metrics, tests hypothesis
- **Phase D** (Recording): Writes findings to PLATO research_log + local files

## Dependencies

- Python 3.10+
- `DEEPINFRA_KEY` environment variable (for Seed-2.0-mini API)
- Access to a PLATO room server at localhost:8847 (optional — runs without it)

## Usage

```bash
export DEEPINFRA_KEY="your-key"
python3 night-wheel.py
```

Runs 12 cycles (~6 hours) by default. Each cycle takes ~2 min, sleeps 25 min between.

## Output

```
research/night-wheel/
  cycle-001.md    — full cycle report
  wheel-state.json — current research state
  FINAL-SUMMARY.md — all findings compiled
```

## Shell Loading

```python
from plato_shell_bridge import PlatoShell
shell = PlatoShell("agent-shell")
shell.load_tool("night-wheel")
```

## License

MIT — Part of the Cocapn Fleet Intelligence System
