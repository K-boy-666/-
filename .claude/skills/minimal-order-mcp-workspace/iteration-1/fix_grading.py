import json
import os

WORKSPACE = os.path.dirname(os.path.abspath(__file__))

for eval_dir in sorted(os.listdir(WORKSPACE)):
    eval_path = os.path.join(WORKSPACE, eval_dir)
    if not os.path.isdir(eval_path) or not eval_dir.startswith("eval-"):
        continue
    for config in ["with_skill", "without_skill"]:
        config_path = os.path.join(eval_path, config)
        if not os.path.isdir(config_path):
            continue
        for run_dir in sorted(os.listdir(config_path)):
            run_path = os.path.join(config_path, run_dir)
            if not os.path.isdir(run_path) or not run_dir.startswith("run-"):
                continue
            grading_path = os.path.join(run_path, "grading.json")
            if not os.path.exists(grading_path):
                continue

            with open(grading_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            assertions = data.get("assertions", [])
            passed = sum(1 for a in assertions if a.get("passed"))
            total = len(assertions)
            pass_rate = round(passed / total, 4) if total > 0 else 0.0

            # Read timing
            timing_path = os.path.join(run_path, "timing.json")
            timing = {}
            if os.path.exists(timing_path):
                with open(timing_path, "r") as tf:
                    timing = json.load(tf)

            new_data = {
                "summary": {
                    "pass_rate": pass_rate,
                    "passed": passed,
                    "failed": total - passed,
                    "total": total,
                },
                "expectations": assertions,
                "timing": timing,
            }

            with open(grading_path, "w", encoding="utf-8") as f:
                json.dump(new_data, f, ensure_ascii=False, indent=2)

            print(f"{eval_dir}/{config}/{run_dir}: {passed}/{total} ({pass_rate})")

print("Done fixing grading files")
