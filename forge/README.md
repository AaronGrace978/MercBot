# mercury-forge

Prompt-driven application forge: build templates, the prompt-to-app synthesizer, offline site and WebGL generators,
and the HTTP / stdio bridge server the MercBot desktop app talks to.

Depends on `mercury-runtime`, which depends on `mercury-harness`.

```bash
pip install -e . -e runtime -e forge
mercury templates
mercury build --prompt "..."
mercury serve
```
