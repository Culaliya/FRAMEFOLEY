export class AuditionEngine {
  private context: AudioContext | null = null;
  private gain: GainNode | null = null;
  private activeSources = new Set<AudioBufferSourceNode>();
  private timers = new Set<number>();
  private volume = 0.9;
  private muted = false;

  private async audioContext(): Promise<AudioContext> {
    if (!this.context) {
      this.context = new AudioContext();
      this.gain = this.context.createGain();
      this.gain.connect(this.context.destination);
      this.syncGain();
    }
    await this.context.resume();
    return this.context;
  }

  private syncGain(): void {
    if (this.gain && this.context) {
      this.gain.gain.setValueAtTime(this.muted ? 0 : this.volume, this.context.currentTime);
    }
  }

  setVolume(value: number): void {
    this.volume = Math.min(1, Math.max(0, value));
    this.syncGain();
  }

  setMuted(value: boolean): void {
    this.muted = value;
    this.syncGain();
  }

  async decode(url: string): Promise<AudioBuffer> {
    const context = await this.audioContext();
    const response = await fetch(url);
    if (!response.ok) throw new Error("Candidate audio could not be loaded.");
    return context.decodeAudioData(await response.arrayBuffer());
  }

  private start(buffer: AudioBuffer, delaySeconds = 0): void {
    if (!this.context || !this.gain) throw new Error("Audio context is not ready.");
    const source = this.context.createBufferSource();
    source.buffer = buffer;
    source.connect(this.gain);
    source.onended = () => {
      source.disconnect();
      this.activeSources.delete(source);
    };
    this.activeSources.add(source);
    source.start(this.context.currentTime + delaySeconds);
  }

  async playSolo(url: string): Promise<void> {
    const buffer = await this.decode(url);
    this.stop();
    this.start(buffer);
  }

  async playInContext(url: string, timestamp: number, video: HTMLVideoElement): Promise<void> {
    const buffer = await this.decode(url);
    this.stop(video);
    const leadSeconds = Math.min(1.25, timestamp);
    video.currentTime = Math.max(0, timestamp - leadSeconds);
    await video.play();
    this.start(buffer, leadSeconds);
    const timer = window.setTimeout(() => {
      video.pause();
      this.timers.delete(timer);
    }, (leadSeconds + buffer.duration + 0.7) * 1000);
    this.timers.add(timer);
  }

  stop(video?: HTMLVideoElement): void {
    for (const source of this.activeSources) {
      try {
        source.stop();
      } catch {
        // A source may already have ended between the set iteration and stop call.
      }
      source.disconnect();
    }
    this.activeSources.clear();
    for (const timer of this.timers) window.clearTimeout(timer);
    this.timers.clear();
    video?.pause();
  }

  async dispose(video?: HTMLVideoElement): Promise<void> {
    this.stop(video);
    this.gain?.disconnect();
    this.gain = null;
    if (this.context && this.context.state !== "closed") await this.context.close();
    this.context = null;
  }
}
