"""Control group: the identical task with and without the operating pack.

The pack arm runs the Mercury system prompt plus retrieved cards. The control arm
runs the same model on the same task with no system prompt at all (the message is
omitted rather than sent empty, since some providers reject an empty system block).
Each arm gets its own copy of the workspace so the second run never inherits the
first run's edits, and neither arm is captured into the store, so a student run
cannot teach the flywheel it is being measured against.
"""

from __future__ import annotations

import json
import shutil
import time
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from mercury.grade import BehaviorReport, grade_delta
from mercury.tiers import ModelTier, classify_model

if TYPE_CHECKING:
    from mercury.runtime import AgentRunResult, MercuryAgentRuntime

AB_LOG_NAME = "ab_log.jsonl"
_SANDBOX_IGNORE = (
    ".git",
    ".mercury",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    "target",
    "dist",
    "workspaces",
)


@dataclass
class ABResult:
    task: str
    model: str
    mode_used: str
    with_pack: "AgentRunResult"
    control: "AgentRunResult"
    sandbox_dir: str = ""
    measurable: bool = True
    caveat: str = ""

    @property
    def pack_grade(self) -> BehaviorReport:
        return self.with_pack.grade

    @property
    def control_grade(self) -> BehaviorReport:
        return self.control.grade

    def as_dict(self) -> dict[str, Any]:
        delta = grade_delta(self.control_grade, self.pack_grade)
        return {
            "task": self.task,
            "model": self.model,
            "tier": classify_model(self.model).value,
            "mode_used": self.mode_used,
            "measurable": self.measurable,
            "caveat": self.caveat,
            "sandbox_dir": self.sandbox_dir,
            "pack_card_ids": self.with_pack.injected_pack.card_ids if self.with_pack.injected_pack else [],
            "pack": self.pack_grade.as_dict(),
            "control": self.control_grade.as_dict(),
            "delta": {
                "score": round(delta.score_delta, 4),
                "policy": round(delta.policy_delta, 4),
                "competence": round(delta.competence_delta, 4),
                "newly_passed": delta.newly_passed,
                "newly_failed": delta.newly_failed,
            },
        }

    def summary(self) -> str:
        pack, ctrl = self.pack_grade, self.control_grade
        rows = [
            ("overall", ctrl.score, pack.score),
            ("policy floor", ctrl.policy_score, pack.policy_score),
            ("competence ceiling", ctrl.competence_score, pack.competence_score),
        ]
        lines = [
            f"A/B on {self.model} ({self.mode_used} mode): control = no system prompt, pack = Mercury prompt + cards",
            f"  {'':<20}{'control':>9}{'pack':>9}{'delta':>9}",
        ]
        for label, before, after in rows:
            lines.append(f"  {label:<20}{before:>9.0%}{after:>9.0%}{after - before:>+9.0%}")
        for label, report in (("control", ctrl), ("pack", pack)):
            if report.hard_failed:
                lines.append(f"  {label}: HARD FAIL (outcome contradicts process)")
        delta = grade_delta(ctrl, pack)
        if delta.newly_passed:
            lines.append(f"  newly passed with pack: {', '.join(delta.newly_passed)}")
        if delta.newly_failed:
            lines.append(f"  newly failed with pack: {', '.join(delta.newly_failed)}")
        if not self.measurable:
            lines.append(f"  NOT MEASURABLE: {self.caveat}")
        elif self.caveat:
            lines.append(f"  note: {self.caveat}")
        return "\n".join(lines)

    def log(self, store_path: str | Path) -> Path:
        path = Path(store_path) / AB_LOG_NAME
        path.parent.mkdir(parents=True, exist_ok=True)
        record = {"ts": time.time(), **self.as_dict()}
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, default=str) + "\n")
        return path


def run_ab(
    runtime: "MercuryAgentRuntime",
    task: str,
    *,
    model: str,
    mode: str = "auto",
    max_steps: int = 12,
    api_keys: dict[str, str] | None = None,
    sandbox_root: str | Path | None = None,
) -> ABResult:
    """Run `task` twice (pack, then control) in isolated workspace copies and grade both."""
    source = runtime.workspace_root
    base = Path(sandbox_root) if sandbox_root is not None else Path(runtime.harness.store.path) / "ab"
    run_dir = base / f"run_{int(time.time() * 1000)}"
    saved_workspace = runtime.workspace_root
    saved_rejected = list(runtime.rejected_pathways)

    skip_roots = {Path(runtime.harness.store.path).resolve(), base.resolve()}
    static_ignore = shutil.ignore_patterns(*_SANDBOX_IGNORE)

    def ignore(directory: str, names: list[str]) -> set[str]:
        skipped = set(static_ignore(directory, names))
        skipped.update(name for name in names if (Path(directory) / name).resolve() in skip_roots)
        return skipped

    def arm(name: str, *, control: bool) -> "AgentRunResult":
        target = run_dir / name
        shutil.copytree(source, target, ignore=ignore, dirs_exist_ok=True)
        runtime.reset_iteration_state()
        runtime.rejected_pathways = [] if control else list(saved_rejected)
        runtime.recovery_injections = []
        return runtime.run(
            task,
            model=model,
            mode=mode,
            max_steps=max_steps,
            workspace_root=target,
            api_keys=api_keys,
            auto_capture=False,
            control=control,
            allow_student=True,
        )

    try:
        with_pack = arm("pack", control=False)
        control = arm("control", control=True)
    finally:
        runtime.workspace_root = saved_workspace
        runtime.rejected_pathways = saved_rejected
        runtime.reset_iteration_state()

    caveats: list[str] = []
    measurable = True
    for label, result in (("pack", with_pack), ("control", control)):
        if result.mode_used != "live":
            measurable = False
            caveats.append(
                f"{label} arm ran in `{result.mode_used}` mode, which does not call the model; "
                "both arms would be identical by construction. Use --mode live with API credentials"
            )
            break
    if measurable and classify_model(model) is ModelTier.FRONTIER:
        caveats.append("model is frontier tier, so the pack is not designed for it; use a lesser or capable model")
    return ABResult(
        task=task,
        model=model,
        mode_used=with_pack.mode_used,
        with_pack=with_pack,
        control=control,
        sandbox_dir=str(run_dir),
        measurable=measurable,
        caveat="; ".join(caveats),
    )
