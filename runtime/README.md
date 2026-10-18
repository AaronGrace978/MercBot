# mercury-runtime

Frontier agent runtime for the Mercury flywheel: provider adapters (Google, Anthropic, OpenAI, xAI, Ollama Cloud),
the workspace toolbox and iteration limiter, the teacher-model card validator, and the `--no-pack` A/B control group.

Depends on `mercury-harness` (the flywheel). If `mercury-forge` is installed the runtime also handles
"build me an app" tasks through it; without it those tasks run as ordinary agent loops.

```bash
pip install -e . -e runtime
mercury run --task "..." --mode live
mercury run --no-pack --model gpt-4o-mini --mode live --task "..."
```
