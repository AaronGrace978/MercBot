"""Command-line interface for the Mercury flywheel."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from mercury.demo import frontier_auth_fix, frontier_pytest_fix, lesser_auth_fail
from mercury.harness import MercuryHarness


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(
        prog="mercury",
        description="Capture frontier agent operations and embed them into lesser-model sessions.",
    )
    parser.add_argument("--store", default=".mercury", help="Knowledge store directory (default: .mercury)")
    parser.add_argument(
        "--validate-cards",
        action="store_true",
        help="Gate every new card on a teacher-model check against its source trace (one call per card)",
    )
    parser.add_argument(
        "--teacher-model",
        default="gemini-4-argon-high",
        help="Frontier model used by --validate-cards (default: gemini-4-argon-high)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("init", help="Create an empty knowledge store")

    capture = sub.add_parser("capture", help="Ingest a frontier (or other) agent trace JSON file")
    capture.add_argument("trace", help="Path to a Mercury, OpenAI, or Cursor-like trace JSON file")
    capture.add_argument("--teacher", action="store_true", help="Treat this trace as a teacher even if the model is not frontier")

    sub.add_parser("distill", help="Re-distill every stored trace into operational cards")

    pack = sub.add_parser("pack", help="Print a Frontier Operating Pack for a lesser-model task")
    pack.add_argument("--task", required=True, help="The student model's upcoming task")
    pack.add_argument("--model", default="gpt-4o-mini", help="Student model name")
    pack.add_argument("--error", dest="error", default=None, help="Optional current error signature")
    pack.add_argument(
        "--format",
        choices=("markdown", "cursor-rule", "json", "sft", "dpo"),
        default="markdown",
    )

    reinforce = sub.add_parser(
        "reinforce",
        help="Reinforce or decay operational cards based on a student run outcome",
    )
    reinforce.add_argument("cards", nargs="+", help="Card IDs injected into the student run")
    outcome_group = reinforce.add_mutually_exclusive_group(required=True)
    outcome_group.add_argument("--success", action="store_true", help="Student run succeeded")
    outcome_group.add_argument("--failure", action="store_true", help="Student run failed")

    contrast = sub.add_parser("contrast", help="Distill divergence between a failed lesser run and a successful frontier run")
    contrast.add_argument("student", help="Failed lesser-model trace JSON")
    contrast.add_argument("teacher", help="Successful frontier trace JSON")

    sub.add_parser("status", help="Show store statistics")
    grade = sub.add_parser(
        "grade",
        help="Deterministically grade how a trace operated (policy floor + competence ceiling)",
    )
    grade.add_argument("trace", help="Path to a Mercury, OpenAI, or Cursor-like trace JSON file")
    grade.add_argument(
        "--compare",
        dest="compare",
        default=None,
        help="Optional second trace: print grade delta (after − before). First trace is before.",
    )
    grade.add_argument("--json", action="store_true", help="Print the grade as JSON")
    demo = sub.add_parser("demo", help="Run the built-in frontier → lesser flywheel on fixture traces")
    demo.add_argument("--json", action="store_true", help="Print pack as JSON")

    models_cmd = sub.add_parser(
        "models",
        help="List strictly FRONTIER models (Google Gemini Argon, Ollama Cloud, Anthropic, OpenAI, xAI)",
    )
    models_cmd.add_argument(
        "--provider",
        default=None,
        help="Filter by provider (google, ollama_cloud, anthropic, openai, xai)",
    )
    models_cmd.add_argument("--json", action="store_true", help="Print frontier models as JSON")

    run_cmd = sub.add_parser(
        "run",
        help="Run the Mercury Frontier Agent Runtime on a task",
    )
    run_cmd.add_argument("--task", required=True, help="Task for the frontier agent runtime")
    run_cmd.add_argument(
        "--model",
        default="gemini-4-argon-high",
        help="Frontier model ID (default: gemini-4-argon-high)",
    )
    run_cmd.add_argument(
        "--mode",
        choices=("auto", "live", "synth"),
        default="auto",
        help="Execution mode (auto, live provider, or synth trajectory)",
    )
    run_cmd.add_argument("--json", action="store_true", help="Print full run telemetry as JSON")

    templates_cmd = sub.add_parser(
        "templates",
        help="List full-stack & agent Application Build Templates available in MercBot App Forge",
    )
    templates_cmd.add_argument("--json", action="store_true", help="Print templates as JSON")

    build_cmd = sub.add_parser(
        "build",
        help="Scaffold, customize, and verify an application from a prompt or MercBot Build Template",
    )
    build_cmd.add_argument(
        "--template",
        default="auto",
        help="Template ID (auto, custom-prompt-app, acid-synth-web, neon-vault-api, tauri-punk-starter, frontier-agent-cli, cyber-kanban-board)",
    )
    build_cmd.add_argument("--name", default="", help="Custom project name / title")
    build_cmd.add_argument("--prompt", default="", help="Custom feature / architecture brief")
    build_cmd.add_argument(
        "--model",
        default="gemini-4-argon-high",
        help="Frontier model ID (default: gemini-4-argon-high)",
    )
    build_cmd.add_argument(
        "--output-dir",
        default="workspaces",
        help="Output workspace parent directory (default: workspaces)",
    )
    build_cmd.add_argument(
        "--spec",
        default="",
        help="Optional path to a local SPEC.md architectural manifest to anchor verification against",
    )
    build_cmd.add_argument("--launch", action="store_true", help="Immediately launch the built application after verification")
    build_cmd.add_argument("--json", action="store_true", help="Print full build artifact as JSON")

    launch_cmd = sub.add_parser(
        "launch",
        help="Launch a built application from workspaces/ in a window or open its folder",
    )
    launch_cmd.add_argument(
        "app",
        nargs="?",
        default="",
        help="Project slug or directory name in workspaces/ (defaults to most recently built app)",
    )
    launch_cmd.add_argument("--folder", action="store_true", help="Open workspace directory in file explorer instead of launching app")
    launch_cmd.add_argument("--output-dir", default="workspaces", help="Workspaces parent directory (default: workspaces)")
    launch_cmd.add_argument("--json", action="store_true", help="Print launch result as JSON")

    serve_cmd = sub.add_parser("serve", help="Start the local MercBot HTTP bridge server")
    serve_cmd.add_argument("--host", default="127.0.0.1", help="Bind host (default: 127.0.0.1)")
    serve_cmd.add_argument("--port", type=int, default=8765, help="Bind port (default: 8765)")

    bridge_cmd = sub.add_parser("bridge", help="Single-shot JSON bridge for Tauri desktop IPC")
    bridge_cmd.add_argument(
        "action",
        choices=("state", "run", "build", "launch", "templates", "contrast", "pack", "reinforce", "seed"),
    )
    bridge_cmd.add_argument("--payload", default="{}", help="JSON payload string")
    bridge_cmd.add_argument("--stream", action="store_true", help="Stream NDJSON chunks before final result")

    sub.add_parser("bridge-worker", help="Persistent asynchronous stdio JSON-RPC worker process for desktop IPC")

    args = parser.parse_args(argv)
    validator = None
    if args.validate_cards:
        from mercury.validate import TeacherCardValidator

        validator = TeacherCardValidator(args.teacher_model)
    harness = MercuryHarness.init(args.store, card_validator=validator)

    if args.command == "init":
        print(f"Initialized Mercury store at {Path(args.store).resolve()}")
        return 0

    if args.command == "capture":
        trace = harness.capture(args.trace, force_teacher=args.teacher)
        stats = harness.stats()
        print(f"Captured {trace.id} ({trace.model}, {trace.tier.value}, {trace.outcome.status.value})")
        print(f"Store now has {stats['traces']} traces and {stats['cards']} cards")
        _print_validation(harness)
        return 0

    if args.command == "distill":
        count = harness.distill_all()
        print(f"Distilled {count} operational cards")
        _print_validation(harness)
        return 0

    if args.command == "pack":
        pack_obj = harness.pack(args.task, model=args.model, error_signature=args.error)
        _print_pack(pack_obj, args.format)
        return 0

    if args.command == "reinforce":
        updated = harness.record_outcome(args.cards, succeeded=bool(args.success))
        state = "succeeded" if args.success else "failed"
        print(f"Recorded {state} outcome across {updated} card(s)")
        return 0

    if args.command == "contrast":
        cards = harness.contrast(args.student, args.teacher)
        print(f"Wrote {len(cards)} contrastive/teacher cards")
        _print_validation(harness)
        return 0

    if args.command == "grade":
        from mercury.grade import grade_delta, grade_trace
        from mercury.traceio import load_trace

        if args.compare:
            delta = grade_delta(load_trace(args.trace), load_trace(args.compare))
            if args.json:
                json.dump(delta.as_dict(), sys.stdout, indent=2)
                sys.stdout.write("\n")
            else:
                print(delta.summary())
                print()
                print("Before:")
                print(delta.before.summary())
                print()
                print("After:")
                print(delta.after.summary())
            return 0

        report = grade_trace(load_trace(args.trace))
        if args.json:
            json.dump(report.as_dict(), sys.stdout, indent=2)
            sys.stdout.write("\n")
        else:
            print(report.summary())
        return 0

    if args.command == "status":
        stats = harness.stats()
        print(json.dumps(stats, indent=2, default=str))
        return 0

    if args.command == "demo":
        return _run_demo(harness, as_json=args.json)

    if args.command == "models":
        from mercury.providers import list_frontier_models

        models = list_frontier_models(args.provider)
        if args.json:
            json.dump([m.model_dump() for m in models], sys.stdout, indent=2)
            sys.stdout.write("\n")
        else:
            print(f"MERCURY FRONTIER MODEL CATALOG ({len(models)} frontier models):")
            for m in models:
                cloud_tag = " [OLLAMA CLOUD]" if m.is_ollama_cloud else ""
                print(f"  - {m.id:<26} | {m.provider_label:<14} | {m.name}{cloud_tag}")
        return 0

    if args.command == "run":
        from mercury.runtime import MercuryAgentRuntime

        runtime = MercuryAgentRuntime(harness, store_path=args.store)
        result = runtime.run(args.task, model=args.model, mode=args.mode)
        if args.json:
            json.dump(result.as_dict(), sys.stdout, indent=2, default=str)
            sys.stdout.write("\n")
        else:
            print(f"Ran {result.model_spec.name} ({result.model_spec.id}) in {result.mode_used} mode")
            print(f"Trace: {result.trace.id} | Distilled {len(result.distilled_cards)} card(s)")
            print(result.grade.summary())
            print()
            print(result.final_response)
        return 0

    if args.command == "templates":
        from mercury.templates import list_build_templates

        templates = list_build_templates()
        if args.json:
            json.dump([t.model_dump() for t in templates], sys.stdout, indent=2)
            sys.stdout.write("\n")
        else:
            print(f"MERCBOT APPLICATION FORGE TEMPLATES ({len(templates)} templates):")
            for t in templates:
                print(f"  - {t.id:<22} | {t.category:<18} | {t.name}")
                print(f"    Stack: {', '.join(t.stack)} | Run: {t.run_hint}")
        return 0

    if args.command == "build":
        from mercury.runtime import MercuryAgentRuntime
        from mercury.templates import infer_template_from_prompt, launch_built_app

        tpl_id = args.template
        proj_name = args.name
        if tpl_id in ("auto", "prompt", "freeform", ""):
            tpl_id, inferred_name = infer_template_from_prompt(args.prompt or args.name or "Acid 303 Synth")
            if not proj_name:
                proj_name = inferred_name

        runtime = MercuryAgentRuntime(harness, store_path=args.store)
        if args.spec:
            spec_src = Path(args.spec)
            if spec_src.is_file():
                from mercury.templates import _slugify, get_build_template

                tmpl_obj = get_build_template(tpl_id)
                slug = _slugify(proj_name or tmpl_obj.name)
                dest_dir = Path(args.output_dir).resolve() / slug
                dest_dir.mkdir(parents=True, exist_ok=True)
                (dest_dir / "SPEC.md").write_text(spec_src.read_text(encoding="utf-8"), encoding="utf-8")

        res = runtime.build_template(
            tpl_id,
            project_name=proj_name,
            custom_prompt=args.prompt,
            model=args.model,
            output_root=args.output_dir,
        )
        art = res["artifact"]
        if args.launch:
            res["launch"] = launch_built_app(art["project_slug"], target="window", output_root=args.output_dir)
        if args.json:
            json.dump(res, sys.stdout, indent=2, default=str)
            sys.stdout.write("\n")
        else:
            spec_ver = art.get("spec_verification") or {}
            print(f"FORGED APPLICATION: {art['project_name']} ({art['template_name']})")
            print(f"Output Dir : {art['output_dir']}")
            print(f"Model      : {art['model']} | Trace: {art['trace_id']}")
            print(f"Files      : {', '.join(art['files_written'])}")
            if spec_ver:
                print(f"SPEC.md    : {spec_ver.get('summary', 'VERIFIED')} ({spec_ver.get('manifest_path', 'SPEC.md')})")
            print(f"Verified   : {'PASS' if art['verification_passed'] else 'FAIL'}")
            print(f"Verify Out : {art['verification_output']}")
            print(f"Launch Cmd : mercury launch {art['project_slug']}")
            if args.launch and "launch" in res:
                print(f"Launched   : {res['launch']['message']}")
        return 0

    if args.command == "launch":
        from mercury.templates import launch_built_app, list_built_apps

        slug = args.app.strip()
        if not slug:
            built = list_built_apps(args.output_dir)
            if not built:
                print("No forged applications found in workspaces/. Run `mercury build --prompt \"...\"` first.", file=sys.stderr)
                return 1
            slug = str(built[0]["project_slug"])
        info = launch_built_app(
            slug,
            target="folder" if args.folder else "window",
            output_root=args.output_dir,
        )
        if args.json:
            json.dump(info, sys.stdout, indent=2, default=str)
            sys.stdout.write("\n")
        else:
            print(f"LAUNCHED: {info['message']}")
            print(f"Path    : {info['launched_path']}")
        return 0

    if args.command == "serve":
        from mercury.server import serve_http

        harness.close()
        serve_http(host=args.host, port=args.port, store_path=args.store)
        return 0

    if args.command == "bridge":
        from mercury.server import MercuryBridge
        from mercury.templates import list_build_templates

        harness.close()
        bridge = MercuryBridge(store_path=args.store)
        payload = json.loads(args.payload) if args.payload else {}

        def _emit_ndjson_chunk(chunk: dict) -> None:
            if args.stream:
                sys.stdout.write(json.dumps({"stream_chunk": chunk}, default=str) + "\n")
                sys.stdout.flush()

        if args.action == "state":
            out = bridge.get_state()
        elif args.action == "run":
            out = bridge.run_agent(payload, on_stream=_emit_ndjson_chunk if args.stream else None)
        elif args.action == "build":
            out = bridge.build_app(payload, on_stream=_emit_ndjson_chunk if args.stream else None)
        elif args.action == "launch":
            out = bridge.launch_app(payload)
        elif args.action == "templates":
            out = {"templates": [t.model_dump() for t in list_build_templates()]}
        elif args.action == "contrast":
            out = bridge.run_contrast(payload)
        elif args.action == "pack":
            out = bridge.compile_pack(payload)
        elif args.action == "reinforce":
            out = bridge.reinforce_card(payload)
        else:
            out = bridge.seed_default_traces()
        json.dump(out, sys.stdout, default=str)
        sys.stdout.write("\n")
        sys.stdout.flush()
        return 0

    if args.command == "bridge-worker":
        from mercury.server import run_stdio_bridge_worker

        harness.close()
        run_stdio_bridge_worker(store_path=args.store)
        return 0

    return 1


def _print_validation(harness: MercuryHarness) -> None:
    if harness.card_validator is None:
        return
    counts = harness.validation_summary()
    print(
        f"Card validation: {counts['confirmed']} confirmed, "
        f"{counts['unconfirmed']} flagged (confidence halved), {counts['rejected']} discarded"
    )


def _print_pack(pack, fmt: str) -> None:
    if fmt == "markdown":
        sys.stdout.write(pack.render())
        return
    if fmt == "cursor-rule":
        sys.stdout.write(pack.as_cursor_rule())
        return
    if fmt == "sft":
        json.dump(pack.as_finetune_rows(), sys.stdout, indent=2)
        sys.stdout.write("\n")
        return
    if fmt == "dpo":
        json.dump(pack.as_dpo_rows(), sys.stdout, indent=2)
        sys.stdout.write("\n")
        return
    payload = {
        "task": pack.task,
        "model": pack.model,
        "tier": pack.tier.value,
        "cards": [card.model_dump() for card in pack.cards],
        "scores": pack.scores,
    }
    json.dump(payload, sys.stdout, indent=2)
    sys.stdout.write("\n")


def _run_demo(harness: MercuryHarness, *, as_json: bool) -> int:
    teacher = frontier_auth_fix()
    extra = frontier_pytest_fix()
    student = lesser_auth_fail()
    harness.capture(teacher)
    harness.capture(extra)
    harness.contrast(student, teacher)
    pack = harness.pack(
        "Users bounce back to /login after authenticating. Fix the redirect bug.",
        model="gpt-4o-mini",
        languages=["typescript"],
    )
    stats = harness.stats()
    if as_json:
        json.dump(
            {"stats": stats, "pack": [card.title for card in pack.cards], "markdown": pack.render()},
            sys.stdout,
            indent=2,
        )
        sys.stdout.write("\n")
    else:
        print("Mercury demo: frontier traces captured, knowledge embedded, lesser-model pack follows.\n")
        print(f"Store: {stats['traces']} traces, {stats['cards']} cards, kinds={stats['by_kind']}")
        print()
        sys.stdout.write(pack.render())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
