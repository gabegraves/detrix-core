# ml-intern governed worker policy

Detrix may use Hugging Face `ml-intern` as an isolated ML engineering worker, but never as a governor, evaluator, evidence writer, gate-threshold editor, or promoter. Detrix remains the source of truth for trajectory admission, training-data export, held-out/domain evaluation, promotion, and rollback.

## Upstream behavior checked

Checked `huggingface/ml-intern` at commit `4501d6981d417710794f4361d1b65fc9bba2dfbd`.

Relevant upstream facts:

- The CLI config path is hardcoded relative to the imported package: `agent/main.py` defines `CLI_CONFIG_PATH = Path(__file__).parent.parent / "configs" / "cli_agent_config.json`.
- The checked-in CLI config enables session saving and automatic file upload and configures an HF MCP server by default.
- The CLI has `prompt`, `--model`, `--max-iterations`, and `--no-stream`; it does not expose a `--config` override.
- Upstream headless mode sets `config.yolo_mode = True` and auto-approves `approval_required` events.

Sources:

- <https://github.com/huggingface/ml-intern/blob/4501d6981d417710794f4361d1b65fc9bba2dfbd/agent/main.py>
- <https://github.com/huggingface/ml-intern/blob/4501d6981d417710794f4361d1b65fc9bba2dfbd/agent/config.py>
- <https://github.com/huggingface/ml-intern/blob/4501d6981d417710794f4361d1b65fc9bba2dfbd/configs/cli_agent_config.json>

## Governed execution policy

`MLInternWorker` supports source-checkout mode only for governed work:

1. Caller supplies a local `ml_intern_source_dir` checkout.
2. Worker copies the checkout into a fresh run directory and excludes dotfiles, `.git`, virtualenvs, caches, and `__pycache__`.
3. Worker writes and reads back `configs/cli_agent_config.json` in the copied checkout.
4. Worker fails closed unless the copied config has:
   - `save_sessions: false`
   - `auto_file_upload: false`
   - `yolo_mode: false`
   - `confirm_cpu_jobs: true`
   - `mcpServers: {}` by default
   - `model_name` supplied by Detrix configuration
   - `auto_save_interval: 0`
   - `heartbeat_interval_s: 0`
5. Worker launches a Detrix-generated safe shim instead of raw upstream headless mode, because upstream headless forces YOLO mode.
6. Worker passes only an explicit environment allowlist: `PATH`, isolated `HOME`, isolated HF/Transformers caches, `PYTHONNOUSERSITE`, telemetry disabled, `DETRIX_MLINTERN_OUTPUT_DIR`, and caller-provided provider keys. Caller-provided env may not override isolation keys.
7. Worker writes stdout/stderr and scans the full run directory; only artifacts under the declared output directory can be clean. New files outside the output directory block the result.

Global installed `ml-intern` is forbidden for governed work until upstream provides a documented config override path that does not force YOLO/auto-approval.

## Artifact policy

Allowed artifacts:

- `stdout.log`
- `stderr.log`
- `mlintern_result.json`
- `training_result.json`
- `adapter/*.safetensors` and `adapter/**/*.safetensors`
- adapter tokenizer/config files under `adapter/`
- `reports/*.json`, `reports/**/*.json`, `reports/*.md`, `reports/**/*.md`

Forbidden artifacts:

- any dotfile or dot-directory
- `.env`, token/secret/credential/password/API-key-like filenames
- raw source datasets or arbitrary workspace files
- new artifacts outside the run output directory
- oversized artifacts above the configured max bytes

Any forbidden artifact marks `MLInternResult.redaction_status = "blocked"`. Blocked worker results cannot enter the governed demo/promotion path.

## Demo boundary

The governed demo sequence is:

1. AgentXRD/AXV2 trajectory is ingested into `TrajectoryStore`.
2. `TrainingExporter` exports only admitted SFT rows.
3. `MLInternWorker` attempts training/fix work and returns a structured subprocess result plus artifact manifest.
4. Detrix post-hoc evaluation supplies incumbent/challenger metrics.
5. Detrix writes a promote/reject report. Promotion is rejected if pass-rate regresses or worker artifacts are blocked.

The worker result alone is never evidence of model quality.
