"""GUIDE Phần 6a - Thử thách mở rộng: Tiến hóa tại thời điểm chạy (hot-path).

Cho phép tác tử tự tạo hoặc cập nhật skill trong thư mục skills/ trong lúc thực thi tác vụ.
Kết quả được lưu tại thư mục riêng `results-6a/` để không làm ảnh hưởng đến kết quả chính.
"""
import argparse
import json
import shutil
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

from deepagents import create_deep_agent
from langchain_core.callbacks import UsageMetadataCallbackHandler
from langchain_core.messages import AIMessage

from .agent import BASE_PROMPT, make_backend
from .grading import grade
from .model import make_model
from .runner import render_trace
from .tasks import ROOT, get_task, hash_dir, list_tasks, prepare_sandbox

HOTPATH_SKILLS_NOTE = (
    " Skills are in the folder skills/ (one sub-folder per skill with a SKILL.md). "
    "You are encouraged to read existing skills in skills/ and follow them. "
    "Crucially, you are also empowered to create or update skills: whenever you identify a reusable rule, "
    "convention, or edge-case checklist, write it to skills/<skill-name>/SKILL.md (with YAML frontmatter) "
    "so that you can adhere to it consistently."
)


def run_hotpath_task(task_id: str, results_dir="results-6a/hotpath", model=None, recursion_limit: int = 60) -> dict:
    """Chạy một tác vụ trong chế độ hot-path evolution (cho phép tác tử sửa skills/ khi chạy)."""
    task = get_task(task_id)
    skills_dir = ROOT / "skills" / "auto"
    out = Path(results_dir) / task_id
    out.mkdir(parents=True, exist_ok=True)
    sandbox = Path(tempfile.mkdtemp(prefix="lab-hotpath-sandbox-"))

    record = {
        "task": task_id,
        "condition": "hotpath-6a",
        "role": task.role,
        "error": None,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    try:
        prepare_sandbox(task, sandbox, skills_dir)
        hash_before = hash_dir(sandbox / "skills")
        record["skills_sha256_initial"] = hash_before

        system_prompt = BASE_PROMPT + HOTPATH_SKILLS_NOTE
        agent = create_deep_agent(
            model=model or make_model(),
            system_prompt=system_prompt,
            backend=make_backend(sandbox),
            skills=["/skills/"],
        )

        usage = UsageMetadataCallbackHandler()
        t0 = time.time()
        messages, final = [], ""
        try:
            result = agent.invoke(
                {"messages": [{"role": "user", "content": task.instruction}]},
                config={"callbacks": [usage], "recursion_limit": recursion_limit},
            )
            messages = result.get("messages", [])
            final = messages[-1].content if messages else ""
        except Exception as exc:  # noqa: BLE001
            record["error"] = f"{type(exc).__name__}: {exc}"
        record["seconds"] = round(time.time() - t0, 1)

        totals = {"input": 0, "output": 0, "total": 0}
        for u in usage.usage_metadata.values():
            totals["input"] += u.get("input_tokens", 0)
            totals["output"] += u.get("output_tokens", 0)
            totals["total"] += u.get("total_tokens", 0)
        record["tokens"] = totals

        calls = [tc for m in messages if isinstance(m, AIMessage) for tc in m.tool_calls]
        skill_names = set()
        for tc in calls:
            if tc["name"] != "read_file":
                continue
            path = str(tc["args"].get("file_path", ""))
            if "skills/" in path:
                name = path.split("skills/", 1)[1].split("/", 1)[0]
                if name:
                    skill_names.add(name)
        record["tool_calls"] = len(calls)
        record["subagent_calls"] = sum(1 for tc in calls if tc["name"] == "task")
        record["skills_read"] = len(skill_names)

        hash_after = hash_dir(sandbox / "skills")
        record["skills_modified"] = hash_after != hash_before
        record["skills_sha256_final"] = hash_after
        record["final_message"] = final if isinstance(final, str) else json.dumps(final, ensure_ascii=False)

        # Lưu bản sao thư mục skills nếu tác tử đã tạo hoặc sửa skill
        if record["skills_modified"] and (sandbox / "skills").exists():
            skills_after_dir = out / "skills_after"
            if skills_after_dir.exists():
                shutil.rmtree(skills_after_dir)
            shutil.copytree(sandbox / "skills", skills_after_dir)

        g = grade(task, sandbox / "workspace")
        record.update({
            "score": g.get("score", 0.0),
            "passed": g.get("passed", 0),
            "total": g.get("total", 0),
            "checks": g.get("checks", []),
        })
        (out / "trace.md").write_text(render_trace(messages), encoding="utf-8")
    finally:
        shutil.rmtree(sandbox, ignore_errors=True)

    (out / "run.json").write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")
    return record


def main(argv=None):
    ap = argparse.ArgumentParser(description="Run hot-path evolution on tasks.")
    ap.add_argument("--tasks", nargs="+", default=["eval"], help="task ids, or 'all', 'learn', 'eval'")
    ap.add_argument("--results", default="results-6a/hotpath")
    ap.add_argument("--recursion-limit", type=int, default=60)
    args = ap.parse_args(argv)

    if args.tasks == ["all"]:
        ids = [t.id for t in list_tasks()]
    elif args.tasks in (["learn"], ["eval"]):
        ids = [t.id for t in list_tasks(args.tasks[0])]
    else:
        ids = args.tasks

    for tid in ids:
        try:
            r = run_hotpath_task(tid, args.results, recursion_limit=args.recursion_limit)
        except Exception as exc:  # noqa: BLE001
            print(f"hotpath      {tid:11s} CRASH {type(exc).__name__}: {exc}", flush=True)
            continue
        print(f"hotpath      {tid:11s} score={r['passed']}/{r['total']} tokens={r['tokens']['total']} "
              f"calls={r['tool_calls']} modified={r['skills_modified']} {r['seconds']}s"
              + (f" ERROR={r['error']}" if r["error"] else ""), flush=True)


if __name__ == "__main__":
    main()
