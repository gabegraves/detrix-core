// Detrix observer extension for the Pi coding agent.
//
// Thin Phase 0 shape: observe tool_result events, batch them at turn_end,
// and forward an AXV2-compatible run artifact to the local Detrix bridge.
// This is intentionally fail-open; bridge failures never affect Pi execution.

declare const process: { env: Record<string, string | undefined> };

const BRIDGE_URL = trimTrailingSlash(
  process.env.DETRIX_BRIDGE_URL ?? "http://localhost:7432",
);
const DOMAIN = process.env.DETRIX_DOMAIN ?? "support_triage";
const PIPELINE_VERSION = "pi-extension-observer-v0";

type JsonObject = Record<string, unknown>;

interface ToolResultRecord {
  toolCallId?: string;
  toolName: string;
  sessionId?: string;
  turnId?: string;
  result: unknown;
  isError?: boolean;
  timestamp: string;
}

interface ExtensionContext {
  sessionId?: string;
  session?: { id?: string };
  turnId?: string;
  turn?: { id?: string };
}

interface ExtensionAPI {
  on(
    event: "tool_result" | "turn_end",
    handler: (event: JsonObject, ctx?: ExtensionContext) => void | Promise<void>,
  ): void;
}

export default function detrixGovernance(pi: ExtensionAPI): void {
  const toolResults: ToolResultRecord[] = [];

  pi.on("tool_result", (event, ctx) => {
    toolResults.push({
      toolCallId: pickString(event, ["toolCallId", "tool_call_id", "id"]),
      toolName:
        pickString(event, ["toolName", "tool_name", "name"]) ?? "unknown_tool",
      sessionId: pickSessionId(event, ctx),
      turnId: pickTurnId(event, ctx),
      result:
        event.result ??
        event.content ??
        event.output ??
        event.toolResult ??
        event,
      isError: pickBoolean(event, ["isError", "is_error", "error"]),
      timestamp: pickString(event, ["timestamp", "createdAt"]) ?? nowIso(),
    });
  });

  pi.on("turn_end", async (event, ctx) => {
    if (toolResults.length === 0) return;

    const batch = toolResults.splice(0, toolResults.length);
    const finishedAt = nowIso();
    const sessionId = pickSessionId(event, ctx) ?? latestDefined(batch, "sessionId");
    const turnId = pickTurnId(event, ctx) ?? latestDefined(batch, "turnId");
    const runId = buildRunId(sessionId, turnId, finishedAt);
    const artifact = buildRunArtifact({
      runId,
      timestamp: finishedAt,
      sessionId,
      turnId,
      toolResults: batch,
    });

    try {
      const response = await fetch(`${BRIDGE_URL}/ingest`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          run_artifact: artifact,
          domain: DOMAIN,
        }),
      });

      if (!response.ok) {
        console.warn(`[detrix] bridge ingest returned ${response.status}`);
      }
    } catch (error) {
      console.warn(`[detrix] bridge ingest failed: ${errorMessage(error)}`);
    }
  });
}

function buildRunArtifact(args: {
  runId: string;
  timestamp: string;
  sessionId?: string;
  turnId?: string;
  toolResults: ToolResultRecord[];
}): JsonObject {
  const firstTimestamp = args.toolResults[0]?.timestamp ?? args.timestamp;
  const startedAt = Date.parse(firstTimestamp);
  const finishedAt = Date.parse(args.timestamp);
  const totalDurationMs =
    Number.isFinite(startedAt) && Number.isFinite(finishedAt)
      ? Math.max(0, finishedAt - startedAt)
      : 0;

  return {
    run_id: args.runId,
    timestamp: args.timestamp,
    pipeline_version: PIPELINE_VERSION,
    config_hash: `domain:${DOMAIN}`,
    input_file_hash: args.sessionId ?? null,
    steps: args.toolResults.map((toolResult, index) => ({
      name: toolResult.toolName,
      status: toolResult.isError ? "failed" : "success",
      duration_ms: 0,
      input_hash: toolResult.toolCallId ?? `${args.runId}:tool:${index}`,
      output_hash: `${args.runId}:result:${index}`,
      metadata: {
        tool_call_id: toolResult.toolCallId,
        session_id: toolResult.sessionId,
        turn_id: toolResult.turnId,
        observed_at: toolResult.timestamp,
        result: toolResult.result,
      },
    })),
    success: args.toolResults.every((toolResult) => !toolResult.isError),
    total_duration_ms: totalDurationMs,
    model_versions: {},
    gate_history: [],
    terminal_routes: {
      default: {
        verdict: "REQUEST_MORE_DATA",
        reason: "pi_extension_observer_only",
        session_id: args.sessionId,
        turn_id: args.turnId,
        tool_result_count: args.toolResults.length,
      },
    },
  };
}

function pickSessionId(event: JsonObject, ctx?: ExtensionContext): string | undefined {
  return (
    pickString(event, ["sessionId", "session_id"]) ??
    pickNestedString(event, "session", "id") ??
    ctx?.sessionId ??
    ctx?.session?.id
  );
}

function pickTurnId(event: JsonObject, ctx?: ExtensionContext): string | undefined {
  return (
    pickString(event, ["turnId", "turn_id"]) ??
    pickNestedString(event, "turn", "id") ??
    ctx?.turnId ??
    ctx?.turn?.id
  );
}

function pickString(
  source: JsonObject,
  keys: readonly string[],
): string | undefined {
  for (const key of keys) {
    const value = source[key];
    if (typeof value === "string" && value.length > 0) {
      return value;
    }
  }
  return undefined;
}

function pickBoolean(
  source: JsonObject,
  keys: readonly string[],
): boolean | undefined {
  for (const key of keys) {
    const value = source[key];
    if (typeof value === "boolean") {
      return value;
    }
  }
  return undefined;
}

function pickNestedString(
  source: JsonObject,
  key: string,
  nestedKey: string,
): string | undefined {
  const value = source[key];
  if (isObject(value)) {
    return pickString(value, [nestedKey]);
  }
  return undefined;
}

function latestDefined<K extends keyof ToolResultRecord>(
  records: ToolResultRecord[],
  key: K,
): ToolResultRecord[K] | undefined {
  for (let index = records.length - 1; index >= 0; index -= 1) {
    const value = records[index]?.[key];
    if (value !== undefined) return value;
  }
  return undefined;
}

function buildRunId(
  sessionId: string | undefined,
  turnId: string | undefined,
  timestamp: string,
): string {
  const suffix = timestamp.replace(/[^0-9A-Za-z]/g, "").slice(0, 14);
  return [sessionId, turnId, suffix].filter(Boolean).join("-") || `pi-${suffix}`;
}

function trimTrailingSlash(value: string): string {
  return value.replace(/\/+$/, "");
}

function nowIso(): string {
  return new Date().toISOString();
}

function isObject(value: unknown): value is JsonObject {
  return typeof value === "object" && value !== null;
}

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}
