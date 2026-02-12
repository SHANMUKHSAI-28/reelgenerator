"""
Module 6 — Approval Gate
============================
Manual review checkpoint before publishing.
Logs every generation with full audit trail.

Features:
- JSON log of every reel generation (script, assets, timings, status)
- Interactive approval prompt (approve / reject / re-generate)
- Audit log file per generation run
"""

import json
import logging
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import config

logger = logging.getLogger("ApprovalGate")


class GenerationLog:
    """Tracks and persists a full reel generation run."""

    def __init__(self, run_id: Optional[str] = None):
        self.run_id = run_id or datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        self.started_at = datetime.now(timezone.utc).isoformat()
        self.log_data = {
            "run_id": self.run_id,
            "started_at": self.started_at,
            "completed_at": None,
            "status": "in_progress",
            "pipeline_steps": {},
            "script": None,
            "assets": {
                "images": [],
                "narrations": [],
                "music": None,
                "output_video": None,
            },
            "timings": {},
            "approval": {
                "approved": None,
                "reviewed_at": None,
                "reviewer_notes": None,
            },
            "errors": [],
        }
        self._step_timers = {}

    def start_step(self, step_name: str):
        """Mark a pipeline step as started."""
        self._step_timers[step_name] = time.time()
        self.log_data["pipeline_steps"][step_name] = {
            "status": "running",
            "started_at": datetime.now(timezone.utc).isoformat(),
        }
        logger.info(f"▶ Step started: {step_name}")

    def complete_step(self, step_name: str, details: Optional[dict] = None):
        """Mark a pipeline step as completed."""
        elapsed = time.time() - self._step_timers.get(step_name, time.time())
        self.log_data["pipeline_steps"][step_name].update({
            "status": "completed",
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "duration_seconds": round(elapsed, 2),
            "details": details or {},
        })
        self.log_data["timings"][step_name] = round(elapsed, 2)
        logger.info(f"✅ Step completed: {step_name} ({elapsed:.1f}s)")

    def fail_step(self, step_name: str, error: str):
        """Mark a pipeline step as failed."""
        elapsed = time.time() - self._step_timers.get(step_name, time.time())
        self.log_data["pipeline_steps"][step_name].update({
            "status": "failed",
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "duration_seconds": round(elapsed, 2),
            "error": error,
        })
        self.log_data["errors"].append({
            "step": step_name,
            "error": error,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        logger.error(f"❌ Step failed: {step_name} — {error}")

    def set_script(self, script: dict):
        """Store the generated script."""
        self.log_data["script"] = script

    def set_assets(
        self,
        images: Optional[list] = None,
        narrations: Optional[list] = None,
        music: Optional[str] = None,
        output_video: Optional[str] = None,
    ):
        """Record generated asset paths."""
        if images:
            self.log_data["assets"]["images"] = [str(p) for p in images if p]
        if narrations:
            self.log_data["assets"]["narrations"] = [str(p) for p in narrations if p]
        if music:
            self.log_data["assets"]["music"] = str(music)
        if output_video:
            self.log_data["assets"]["output_video"] = str(output_video)

    def finalize(self, status: str = "completed"):
        """Finalize the log and save to disk."""
        self.log_data["completed_at"] = datetime.now(timezone.utc).isoformat()
        self.log_data["status"] = status

        # Calculate total duration
        if self.log_data["timings"]:
            self.log_data["total_duration_seconds"] = round(
                sum(self.log_data["timings"].values()), 2
            )

        self._save()

    def _save(self):
        """Persist log to JSON file."""
        config.LOGS_DIR.mkdir(parents=True, exist_ok=True)
        log_path = config.LOGS_DIR / f"run_{self.run_id}.json"
        with open(log_path, "w", encoding="utf-8") as f:
            json.dump(self.log_data, f, indent=2, ensure_ascii=False)
        logger.info(f"📋 Generation log saved: {log_path}")
        return log_path


def request_approval(
    output_video: Path,
    script: dict,
    gen_log: GenerationLog,
    auto_approve: bool = False
) -> bool:
    """
    Interactive approval gate.
    Shows summary and asks for human approval before marking as final.

    Args:
        output_video: Path to generated MP4
        script: The script that was used
        gen_log: The generation log for this run
        auto_approve: Skip manual review (for automated pipelines)

    Returns:
        True if approved, False if rejected
    """
    print("\n" + "═" * 60)
    print("🎬  REEL GENERATION COMPLETE — APPROVAL GATE")
    print("═" * 60)
    print(f"\n📄 Title:    {script.get('title', 'Untitled')}")
    print(f"💫 Emotion:  {script.get('emotional_core', 'N/A')}")
    print(f"🎵 Tone:     {script.get('audio_tone', 'N/A')}")
    print(f"🎞️  Scenes:   {len(script.get('scenes', []))}")

    total_duration = sum(s.get("duration", 0) for s in script.get("scenes", []))
    print(f"⏱️  Duration: {total_duration:.1f}s")
    print(f"\n📁 Output:   {output_video}")

    file_size = output_video.stat().st_size / (1024 * 1024) if output_video.exists() else 0
    print(f"📦 Size:     {file_size:.1f} MB")

    print("\n📝 Scenes:")
    for scene in script.get("scenes", []):
        print(f"   {scene['scene_number']}. [{scene.get('duration', 0)}s] "
              f"\"{scene.get('text_overlay', '')}\"")

    timings = gen_log.log_data.get("timings", {})
    if timings:
        print("\n⏰ Pipeline Timings:")
        for step, seconds in timings.items():
            print(f"   {step:<25} {seconds:.1f}s")

    errors = gen_log.log_data.get("errors", [])
    if errors:
        print(f"\n⚠️  Warnings/Errors: {len(errors)}")
        for err in errors:
            print(f"   - [{err['step']}] {err['error']}")

    print("\n" + "─" * 60)

    if auto_approve:
        logger.info("Auto-approve mode: approved")
        gen_log.log_data["approval"] = {
            "approved": True,
            "reviewed_at": datetime.now(timezone.utc).isoformat(),
            "reviewer_notes": "Auto-approved",
        }
        gen_log.finalize("approved")
        print("✅ Auto-approved\n")
        return True

    # Interactive approval
    while True:
        choice = input("\n🔍 Action: [A]pprove  [R]eject  [V]iew script details → ").strip().upper()

        if choice == "A":
            notes = input("   Notes (optional): ").strip() or "Approved by reviewer"
            gen_log.log_data["approval"] = {
                "approved": True,
                "reviewed_at": datetime.now(timezone.utc).isoformat(),
                "reviewer_notes": notes,
            }
            gen_log.finalize("approved")
            print("\n✅ REEL APPROVED — Ready for publishing!")
            return True

        elif choice == "R":
            reason = input("   Rejection reason: ").strip() or "Rejected by reviewer"
            gen_log.log_data["approval"] = {
                "approved": False,
                "reviewed_at": datetime.now(timezone.utc).isoformat(),
                "reviewer_notes": reason,
            }
            gen_log.finalize("rejected")
            print("\n❌ REEL REJECTED")
            return False

        elif choice == "V":
            print("\n" + json.dumps(script, indent=2))

        else:
            print("   Invalid choice. Enter A, R, or V.")


def cleanup_temp_files():
    """Remove temporary files after approval/rejection."""
    if config.TEMP_DIR.exists():
        shutil.rmtree(config.TEMP_DIR)
        config.TEMP_DIR.mkdir(parents=True, exist_ok=True)
        logger.info("🗑️  Temp files cleaned up")


# ─── Standalone test ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, format=config.LOG_FORMAT)

    log = GenerationLog()
    log.start_step("test_step")
    time.sleep(0.1)
    log.complete_step("test_step", {"detail": "test"})
    log.finalize("test_completed")
    print(f"Log saved: {config.LOGS_DIR}")
