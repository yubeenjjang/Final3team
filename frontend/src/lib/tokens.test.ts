import fs from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import tailwindConfig from "../../tailwind.config";

function collectTsxFiles(dir: string): string[] {
  const entries = fs.readdirSync(dir, { withFileTypes: true });
  const results: string[] = [];

  for (const entry of entries) {
    const fullPath = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      results.push(...collectTsxFiles(fullPath));
    } else if (entry.isFile() && entry.name.endsWith(".tsx")) {
      results.push(fullPath);
    }
  }

  return results;
}

describe("F2 design tokens", () => {
  it("F2 no raw colors in src/**/*.tsx", () => {
    const srcDir = path.resolve(__dirname, "..");
    const tsxFiles = collectTsxFiles(srcDir);
    expect(tsxFiles.length).toBeGreaterThan(0);

    const rawHexPattern = /#[0-9A-Fa-f]{6}/g;
    const violations: Array<{ file: string; matches: string[] }> = [];

    for (const file of tsxFiles) {
      const content = fs.readFileSync(file, "utf8");
      const matches = content.match(rawHexPattern);
      if (matches && matches.length > 0) {
        violations.push({
          file: path.relative(srcDir, file),
          matches,
        });
      }
    }

    expect(violations).toEqual([]);
  });

  it("F2 body CSS and Tailwind use the registered Pretendard Variable font", () => {
    const css = fs.readFileSync(path.resolve(__dirname, "../app/globals.css"), "utf8");
    expect(css).toMatch(/font-family:\s*"Pretendard Variable",/);
    const fonts = tailwindConfig.theme?.extend?.fontFamily as Record<string, string[]>;
    expect(fonts.sans[0]).toBe("Pretendard Variable");
  });

  it("F2 registers required color and radius tokens in tailwind config", () => {
    const colors = tailwindConfig.theme?.extend?.colors as Record<string, string>;
    const borderRadius = tailwindConfig.theme?.extend?.borderRadius as Record<
      string,
      string
    >;

    const requiredColors = [
      "bg",
      "surface",
      "ink",
      "muted",
      "brand",
      "accent",
      "neon",
      "dark-bg",
      "dark-surface",
      "crowd-green",
      "crowd-yellow",
      "crowd-orange",
      "crowd-red",
    ];

    for (const token of requiredColors) {
      expect(colors[token]).toBeTruthy();
    }

    expect(borderRadius.card).toBe("18px");
    expect(borderRadius.input).toBe("25px");
    expect(borderRadius.chip).toBe("9999px");
  });
});
