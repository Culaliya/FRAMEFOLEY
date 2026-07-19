import type { StyleProfile } from "@framefoley/contracts";

export const STYLE_PRESETS: StyleProfile[] = [
  {
    id: "lunar_arcade",
    title: "LUNAR ARCADE",
    promptPrefix:
      "Luminous, tactile, playful, slightly glassy. Dry close perspective. Clear transients.",
  },
  {
    id: "rubber_dungeon",
    title: "RUBBER DUNGEON",
    promptPrefix: "Squishy, warm, tactile, comic. Soft weight, close room, no giant tail.",
  },
  {
    id: "rust_bloom",
    title: "RUST BLOOM",
    promptPrefix:
      "Dry metal, dusty mechanisms, restrained weight. Mechanical detail without trailer-scale impact.",
  },
  {
    id: "paper_signal",
    title: "PAPER SIGNAL",
    promptPrefix:
      "Papery, wooden, handmade, soft transient. Small-room intimacy and readable motion.",
  },
];

export function stylePreset(id: StyleProfile["id"]): StyleProfile | undefined {
  return STYLE_PRESETS.find((preset) => preset.id === id);
}
