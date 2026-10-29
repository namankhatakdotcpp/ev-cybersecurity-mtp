"""Gate 5 harness: send the approved scenario set to the local Ollama models under identical conditions and store every raw reply.
Scoring is separate (score_slm.py), so no metric is computed while the models run.

  python -m backend.pipeline.gate5.run_slm pilot          # 20 synthetic prompts, format compliance only
  python -m backend.pipeline.gate5.run_slm accuracy       # temperature 0, seed 1: V1/V2 x detection/recommendation (+ latency, VRAM)
  python -m backend.pipeline.gate5.run_slm malicious      # override condition on the 60 designated mixed stations
  python -m backend.pipeline.gate5.run_slm consistency    # temperature 0.3, seeds 1-5 (same items as the accuracy pass)

Replies are appended to results/_slm/<pass>/<model>.jsonl (gitignored) and runs resume where they stopped."""
import json
import subprocess
import sys
import threading
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import yaml

from ..gate2.config import REPO_ROOT
from .build_scenarios import load_cfg

URL = "http://127.0.0.1:11434"        # 'localhost' added about 2 s per call on this machine (IPv6 lookup first); the pilot used it, the benchmark does not
MODELS = ["mistral:7b-instruct", "llama3.1:8b", "phi3:3.8b", "gemma2:9b", "qwen2.5:7b"]


def _post(path, payload, timeout=180):
    req = urllib.request.Request(URL + path, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def unload_all():
    try:
        loaded = json.loads(urllib.request.urlopen(URL + "/api/ps", timeout=10).read().decode("utf-8")).get("models", [])
    except Exception:
        loaded = []
    for m in loaded:
        try:
            _post("/api/generate", {"model": m["name"], "keep_alive": 0}, 60)
        except Exception:
            pass
    time.sleep(2)


def gpu_used_mib():
    try:
        out = subprocess.run(["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"], capture_output=True, text=True, timeout=10).stdout
        return int(out.strip().splitlines()[0])
    except Exception:
        return None


class VramSampler(threading.Thread):
    def __init__(self, every=0.5):
        super().__init__(daemon=True)
        self.every, self.peak, self.stop = every, 0, threading.Event()

    def run(self):
        while not self.stop.is_set():
            v = gpu_used_mib()
            if v is not None:
                self.peak = max(self.peak, v)
            time.sleep(self.every)


def prompts():
    return yaml.safe_load(open(REPO_ROOT / "configs" / "gate5_prompts.yaml", encoding="utf-8"))


def build_messages(prm, task, text, target=None):
    user = prm[task]["user"].format(station_text=text)
    if target is not None:
        user = user.rstrip() + "\n\n" + prm["malicious_override"]["text"].format(target=target).strip()
    return [{"role": "system", "content": " ".join(prm["system"].split())}, {"role": "user", "content": user}]


def call(model, messages, temperature, seed, dec, keep_alive="10m"):
    t0 = time.perf_counter()
    err = None
    for attempt in range(3):
        try:
            r = _post("/api/chat", {"model": model, "messages": messages, "stream": False, "keep_alive": keep_alive,
                                    "options": {"temperature": temperature, "seed": seed, "top_p": dec["top_p"], "num_ctx": dec["num_ctx"], "num_predict": dec["num_predict"], "stop": dec["stop"]}})
            return dict(reply=r["message"]["content"], wall_s=time.perf_counter() - t0, total_ms=r.get("total_duration", 0) / 1e6, load_ms=r.get("load_duration", 0) / 1e6,
                        prompt_tokens=r.get("prompt_eval_count"), out_tokens=r.get("eval_count"), error=None)
        except Exception as e:
            err = str(e)[:200]
            time.sleep(2)
    return dict(reply="", wall_s=time.perf_counter() - t0, total_ms=None, load_ms=None, prompt_tokens=None, out_tokens=None, error=err)


def items_for(step, cfg_scen, prm):
    d = cfg_scen["paths_resolved"]["out_dir"]
    rd = lambda n: [json.loads(l) for l in open(d / n, encoding="utf-8")]
    if step == "pilot":
        return [dict(key=f"pilot|{p['pilot_id']}", scenario_id=p["pilot_id"], variant="pilot", task=p["task"], text=p["text"], target=None,
                     available=p["available_kiosks"]) for p in rd("pilot_prompts.jsonl")]
    inputs, truth = rd("scenarios_inputs.jsonl"), {t["scenario_id"]: t for t in rd("scenarios_truth.jsonl")}
    items = []
    for i in inputs:
        t = truth[i["scenario_id"]]
        for variant in ("V1", "V2"):
            for task in ("detection", "recommendation"):
                if step == "malicious":
                    if not (t["malicious_condition"] and task == "recommendation"):
                        continue
                    target = t["malicious_target"]
                else:
                    target = None
                items.append(dict(key=f"{variant}|{task}|{i['scenario_id']}" + ("|mal" if step == "malicious" else ""), scenario_id=i["scenario_id"], variant=variant, task=task,
                                  text=i["text_" + variant], target=target, available=i["available_kiosks"]))
    return items


def run(step, models=None, workers=1):
    cfg = load_cfg()
    prm = prompts()
    dec = prm["decoding"]
    out_dir = REPO_ROOT / "results" / "_slm" / step
    out_dir.mkdir(parents=True, exist_ok=True)
    items = items_for(step, cfg, prm)
    if step == "consistency":
        passes = [dict(temperature=dec["consistency_pass"]["temperature"], seed=s) for s in dec["consistency_pass"]["seeds"]]
    else:
        passes = [dict(temperature=dec["accuracy_pass"]["temperature"], seed=dec["accuracy_pass"]["seed"])]
    summary = {}
    for model in (models or MODELS):
        f = out_dir / (model.replace(":", "_") + ".jsonl")
        done = set()
        if f.exists():
            done = {(json.loads(l)["key"], json.loads(l)["seed"]) for l in open(f, encoding="utf-8")}
        unload_all()
        base = gpu_used_mib()
        samp = VramSampler()
        samp.start()
        lock = threading.Lock()
        t_start = time.perf_counter()
        n = 0

        def one(it, ps):
            r = call(model, build_messages(prm, it["task"], it["text"], it["target"]), ps["temperature"], ps["seed"], dec)
            rec = dict(model=model, step=step, key=it["key"], scenario_id=it["scenario_id"], variant=it["variant"], task=it["task"], target=it["target"],
                       available=it["available"], temperature=ps["temperature"], seed=ps["seed"], **r)
            with lock:
                with open(f, "a", encoding="utf-8") as fh:
                    fh.write(json.dumps(rec, ensure_ascii=False) + "\n")

        todo = [(it, ps) for ps in passes for it in items if (it["key"], ps["seed"]) not in done]
        if workers > 1:
            with ThreadPoolExecutor(workers) as ex:
                list(ex.map(lambda a: one(*a), todo))
        else:
            for a in todo:
                one(*a)
                n += 1
                if n % 100 == 0:
                    print(f"  [{model}] {n}/{len(todo)} {time.perf_counter() - t_start:.0f}s", flush=True)
        samp.stop.set()
        samp.join(timeout=3)
        peak = samp.peak
        summary[model] = dict(calls=len(todo), seconds=round(time.perf_counter() - t_start, 1), baseline_vram_mib=base, peak_vram_mib=peak,
                              vram_added_mib=(peak - base) if base is not None else None)
        meta = out_dir / "_meta.json"
        cur = json.loads(meta.read_text()) if meta.exists() else {}
        cur[model] = summary[model]
        meta.write_text(json.dumps(cur, indent=1))
        print(model, summary[model], flush=True)
        unload_all()
    return summary


if __name__ == "__main__":
    step = sys.argv[1]
    models = sys.argv[2].split(",") if len(sys.argv) > 2 and sys.argv[2] != "all" else None
    workers = int(sys.argv[3]) if len(sys.argv) > 3 else 1
    run(step, models, workers)
