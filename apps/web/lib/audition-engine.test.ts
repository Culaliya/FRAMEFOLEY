import { afterEach, describe, expect, it, vi } from "vitest";

import { AuditionEngine } from "./audition-engine";

class FakeSource {
  buffer: AudioBuffer | null = null;
  onended: (() => void) | null = null;
  stop = vi.fn();
  connect = vi.fn();
  disconnect = vi.fn();
  start = vi.fn();
}

class FakeGain {
  connect = vi.fn();
  disconnect = vi.fn();
  gain = { setValueAtTime: vi.fn() };
}

class FakeAudioContext {
  static sources: FakeSource[] = [];
  state = "running";
  currentTime = 1;
  destination = {} as AudioDestinationNode;
  gain = new FakeGain();
  close = vi.fn(async () => undefined);
  resume = vi.fn(async () => undefined);
  createGain = vi.fn(() => this.gain as unknown as GainNode);
  createBufferSource = vi.fn(() => {
    const source = new FakeSource();
    FakeAudioContext.sources.push(source);
    return source as unknown as AudioBufferSourceNode;
  });
  decodeAudioData = vi.fn(async () => ({ duration: 0.5 }) as AudioBuffer);
}

describe("AuditionEngine cleanup", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    FakeAudioContext.sources = [];
  });

  it("stops and disconnects every active Web Audio node on disposal", async () => {
    vi.stubGlobal("AudioContext", FakeAudioContext);
    vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(new ArrayBuffer(8)));
    const engine = new AuditionEngine();
    await engine.playSolo("https://signed.example/candidate.wav");
    const source = FakeAudioContext.sources[0];
    expect(source.start).toHaveBeenCalledOnce();
    await engine.dispose();
    expect(source.stop).toHaveBeenCalledOnce();
    expect(source.disconnect).toHaveBeenCalled();
  });
});
