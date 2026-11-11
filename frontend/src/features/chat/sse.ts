import type { PipelineEvent } from "../../contracts/events";

/** Incremental Server-Sent Events parser. Feed it raw text chunks in arrival order. */
export function createSseParser(onEvent: (event: PipelineEvent) => void): (chunk: string) => void {
  let buffer = "";
  return (chunk: string) => {
    buffer += chunk.replace(/\r\n/g, "\n");
    let boundary = buffer.indexOf("\n\n");
    while (boundary !== -1) {
      const block = buffer.slice(0, boundary);
      buffer = buffer.slice(boundary + 2);
      const data = block
        .split("\n")
        .filter((line) => line.startsWith("data: "))
        .map((line) => line.slice("data: ".length))
        .join("\n");
      if (data) onEvent(JSON.parse(data) as PipelineEvent);
      boundary = buffer.indexOf("\n\n");
    }
  };
}

/** Stream pipeline events from an SSE endpoint (POST for live chat, GET for replays). */
export async function streamEvents(
  url: string,
  init: RequestInit,
  onEvent: (event: PipelineEvent) => void,
): Promise<void> {
  const response = await fetch(url, init);
  if (!response.ok || !response.body) {
    throw new Error(`The server answered ${response.status}. Check that the backend is running.`);
  }
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  const feed = createSseParser(onEvent);
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    feed(decoder.decode(value, { stream: true }));
  }
  feed(decoder.decode() + "\n\n");
}
