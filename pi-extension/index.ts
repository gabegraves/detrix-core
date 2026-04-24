// Detrix governance extension for the pi agent harness.
// STATUS: PLACEHOLDER - ExtensionAPI is a guessed interface.
// Verify against actual pi SDK before using.
//
// Phase 0: batch forwarder. Collects tool_result events and
// sends them to the Python bridge on turn_end. Fails open.

const BRIDGE_URL = process.env.DETRIX_BRIDGE_URL ?? "http://localhost:7432";

interface ToolResultEvent {
  toolName: string;
  content: unknown;
}

interface TurnEndEvent {
  sessionId?: string;
}

interface ExtensionAPI {
  on(event: "tool_result", handler: (e: ToolResultEvent) => void): void;
  on(event: "turn_end", handler: (e: TurnEndEvent) => void): void;
}

export default function detrixGovernance(pi: ExtensionAPI): void {
  const toolResults: Array<{
    name: string;
    result: unknown;
    timestamp: string;
  }> = [];

  pi.on("tool_result", (event: ToolResultEvent) => {
    toolResults.push({
      name: event.toolName,
      result: event.content,
      timestamp: new Date().toISOString(),
    });
  });

  pi.on("turn_end", async (event: TurnEndEvent) => {
    if (toolResults.length === 0) return;

    const runId = event.sessionId ?? Math.random().toString(36).substring(2, 14);

    try {
      const response = await fetch(`${BRIDGE_URL}/ingest`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          run_artifact: {
            run_id: runId,
            timestamp: new Date().toISOString(),
            pipeline_version: "pi-extension-v0",
            config_hash: "",
            input_file_hash: null,
            steps: toolResults.map((toolResult) => ({
              name: toolResult.name,
              status: "success",
              duration_ms: 0,
            })),
            success: true,
            total_duration_ms: 0,
            model_versions: {},
            gate_history: [],
            terminal_routes: {},
          },
          domain: "pi",
        }),
      });
      if (!response.ok) {
        console.warn(`[detrix] bridge returned ${response.status}`);
      }
    } catch {
      // Fail open: agent continues unimpeded.
    } finally {
      toolResults.length = 0;
    }
  });
}
