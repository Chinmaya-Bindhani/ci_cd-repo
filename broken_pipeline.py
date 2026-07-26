"""
Multi-step agent pipeline that fails in 3 ways: timeout, malformed output, wrong data.
Run: python broken_pipeline.py --runs 30
"""
import argparse
import json
import random
import threading
import time
import uuid

SHARED_CACHE = {}


def log(trace_id: str, step: str, msg: str):
    print(json.dumps({"trace_id": trace_id, "step": step, "msg": msg, "ts": time.time()}))


def step1_fetch_user(trace_id, user_id):
    log(trace_id, "step1_fetch_user", f"fetching user {user_id}")
    time.sleep(random.uniform(0.001, 0.01))
    return {"user_id": user_id, "name": f"user-{user_id}"}


def step2_call_external_api(trace_id, user):
    log(trace_id, "step2_call_external_api", "calling external API")
    delay = random.choice([0.01, 0.01, 0.01, 2.5])
    NO_TIMEOUT = 1.0
    if delay > NO_TIMEOUT:
        raise TimeoutError(f"external API call exceeded {NO_TIMEOUT}s (took {delay}s)")
    time.sleep(delay)
    return {"status": "ok", "score": random.randint(1, 100)}


def step3_generate_output(trace_id, user, api_result):
    log(trace_id, "step3_generate_output", "generating structured output")
    payload = f'{{"user_id": "{user["user_id"]}", "score": {api_result["score"]}, "verdict": "approved"}}'
    max_chars = random.choice([70, 70, 70, 48])
    truncated = payload[:max_chars]
    return truncated


def step4_write_result(trace_id, user_id, parsed_result):
    log(trace_id, "step4_write_result", "writing result to shared cache")
    SHARED_CACHE["last_score"] = parsed_result.get("score")
    time.sleep(random.uniform(0, 0.005))
    final_score = SHARED_CACHE["last_score"]
    return {"user_id": user_id, "final_score": final_score}


def run_pipeline(user_id):
    trace_id = str(uuid.uuid4())[:8]
    try:
        user = step1_fetch_user(trace_id, user_id)
        api_result = step2_call_external_api(trace_id, user)
        raw_output = step3_generate_output(trace_id, user, api_result)

        try:
            parsed = json.loads(raw_output)
        except json.JSONDecodeError as e:
            log(trace_id, "step3_generate_output", f"MALFORMED OUTPUT: {e} | raw={raw_output!r}")
            return {"trace_id": trace_id, "status": "malformed_output", "error": str(e)}

        result = step4_write_result(trace_id, user_id, parsed)

        if result["user_id"] != user_id:
            log(trace_id, "step4_write_result", "INVARIANT VIOLATION: wrong user in result")

        if result["final_score"] != api_result["score"]:
            log(trace_id, "step4_write_result",
                f"SILENT WRONG DATA: expected score={api_result['score']} "
                f"but got final_score={result['final_score']} (race condition)")
            return {"trace_id": trace_id, "status": "silent_wrong_data",
                     "expected": api_result["score"], "got": result["final_score"]}

        log(trace_id, "pipeline", f"SUCCESS: {result}")
        return {"trace_id": trace_id, "status": "success", "result": result}

    except TimeoutError as e:
        log(trace_id, "step2_call_external_api", f"TIMEOUT: {e}")
        return {"trace_id": trace_id, "status": "timeout", "error": str(e)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=int, default=30)
    parser.add_argument("--concurrent", action="store_true",
                         help="run requests concurrently to expose the race condition")
    args = parser.parse_args()

    outcomes = {"success": 0, "timeout": 0, "malformed_output": 0, "silent_wrong_data": 0}
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

    print("\n--- Summary ---")
    for status, count in outcomes.items():
        print(f"{status}: {count}/{args.runs}")


if __name__ == "__main__":
    main()
