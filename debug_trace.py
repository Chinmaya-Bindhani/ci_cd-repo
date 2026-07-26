"""
Debugging harness: runs broken pipeline, captures traces, bisects failures.

Run: python debug_trace.py --runs 100 --concurrent
"""
import argparse
import contextlib
import io
import json
from collections import defaultdict

from broken_pipeline import run_pipeline


def isolate_step_from_log(captured_output: str) -> str:
    """Find the step that caused the failure from log traces."""
    lines = [entry_line for entry_line in captured_output.splitlines() if entry_line.strip()]
    for line in reversed(lines):
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        if any(tag in entry["msg"] for tag in
               ("TIMEOUT", "MALFORMED", "SILENT WRONG DATA", "INVARIANT")):
            return entry["step"]
    return "unknown"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=int, default=100)
    args = parser.parse_args()

    failures_by_step = defaultdict(int)
    failures_by_type = defaultdict(int)

    for i in range(args.runs):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            result = run_pipeline(user_id=f"u{i}")
        output = buf.getvalue()

        if result["status"] != "success":
            failing_step = isolate_step_from_log(output)
            failures_by_step[failing_step] += 1
            failures_by_type[result["status"]] += 1

    print("--- Failure isolation report ---")
    print(f"Total runs: {args.runs}\n")

    print("By failure type:")
    for ftype, count in sorted(failures_by_type.items(), key=lambda x: -x[1]):
        print(f"  {ftype:<20} {count:>4}  ({100*count/args.runs:.1f}%)")

    print("\nBy responsible pipeline step (bisected from trace):")
    for step, count in sorted(failures_by_step.items(), key=lambda x: -x[1]):
        print(f"  {step:<25} {count:>4}")

    print("\nDiagnosis:")
    if failures_by_type.get("timeout"):
        print("  - step2_call_external_api: no timeout/backoff configured on the "
              "external call -> add explicit timeout + retry with backoff.")
    if failures_by_type.get("malformed_output"):
        print("  - step3_generate_output: output truncated below a variable limit, "
              "no schema validation before parsing -> enforce schema/tool-use output "
              "and validate length budget before truncating mid-structure.")
    if failures_by_type.get("silent_wrong_data"):
        print("  - step4_write_result: unsynchronized shared cache read/write under "
              "concurrency -> use per-trace keys instead of a shared mutable key, "
              "or lock around the read-after-write.")


if __name__ == "__main__":
    main()
