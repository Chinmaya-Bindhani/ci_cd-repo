"""
Fixed version of broken_pipeline.py with guardrails applied.
Run: python fixed_pipeline.py --runs 150 --concurrent
"""
import argparse
import json
import random
import threading
import time
import uuid

CACHE = {}
CACHE_LOCK = threading.Lock()


def log(trace_id, step, msg):
    print(json.dumps({"trace_id": trace_id, "step": step, "msg": msg, "ts": time.time()}))


def step1_fetch_user(trace_id, user_id):
    log(trace_id, "step1_fetch_user", f"fetching user {user_id}")
    time.sleep(random.uniform(0.001, 0.01))
    return {"user_id": user_id, "name": f"user-{user_id}"}


def step2_call_external_api(trace_id, user, timeout=1.0, max_retries=2):
    for attempt in range(1, max_retries + 2):
        log(trace_id, "step2_call_external_api", f"attempt {attempt}")
        delay = random.choice([0.01, 0.01, 0.01, 2.5])
        if delay <= timeout:
            time.sleep(delay)
            return {"status": "ok", "score": random.randint(1, 100)}
        backoff = 0.05 * attempt
        log(trace_id, "step2_call_external_api",
            f"attempt {attempt} exceeded {timeout}s timeout, backing off {backoff}s")
        time.sleep(backoff)
    raise TimeoutError(f"external API failed after {max_retries + 1} attempts")


SCHEMA = {"user_id": str, "score": int, "verdict": str}


def validate_schema(obj: dict, schema: dict) -> bool:
    return all(k in obj and isinstance(obj[k], t) for k, t in schema.items())


def step3_generate_output(trace_id, user, api_result):
    log(trace_id, "step3_generate_output", "generating structured output")
    obj = {"user_id": user["user_id"], "score": api_result["score"], "verdict": "approved"}
    if not validate_schema(obj, SCHEMA):
        raise ValueError(f"generated output failed schema validation: {obj}")
    return obj


def step4_write_result(trace_id, user_id, parsed_result):
    log(trace_id, "step4_write_result", "writing result to cache")
    key = f"trace:{trace_id}"
    with CACHE_LOCK:
        CACHE[key] = parsed_result["score"]
        final_score = CACHE[key]
    return {"user_id": user_id, "final_score": final_score}


def run_pipeline(user_id):
    trace_id = str(uuid.uuid4())[:8]
    try:
        user = step1_fetch_user(trace_id, user_id)
        api_result = step2_call_external_api(trace_id, user)
        parsed = step3_generate_output(trace_id, user, api_result)
        result = step4_write_result(trace_id, user_id, parsed)

        assert result["user_id"] == user_id, "invariant violated: wrong user in result"
        assert result["final_score"] == api_result["score"], "invariant violated: score mismatch"

        log(trace_id, "pipeline", f"SUCCESS: {result}")
        return {"trace_id": trace_id, "status": "success", "result": result}

    except TimeoutError as e:
        log(trace_id, "step2_call_external_api", f"TIMEOUT (exhausted retries): {e}")
        return {"trace_id": trace_id, "status": "timeout", "error": str(e)}
    except (ValueError, AssertionError) as e:
        log(trace_id, "pipeline", f"VALIDATION FAILURE: {e}")
        return {"trace_id": trace_id, "status": "validation_failure", "error": str(e)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=int, default=150)
    parser.add_argument("--concurrent", action="store_true")
    args = parser.parse_args()

    outcomes = {"success": 0, "timeout": 0, "validation_failure": 0}
    results = [None] * args.runs

    def worker(i):
        results[i] = run_pipeline(user_id=f"u{i}")

    if args.concurrent:
        threads = [threading.Thread(target=worker, args=(i,)) for i in range(args.runs)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
    else:
        for i in range(args.runs):
            worker(i)

    for r in results:
        outcomes[r["status"]] += 1

    print("\n--- Summary (fixed pipeline) ---")
    for status, count in outcomes.items():
        print(f"{status}: {count}/{args.runs}")


if __name__ == "__main__":
    main()
