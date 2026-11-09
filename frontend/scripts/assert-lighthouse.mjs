import { readFile } from "node:fs/promises";

const reportPath = process.argv[2];
if (!reportPath) {
  throw new Error("Usage: npm run test:lighthouse:assert -- <report.json>");
}

const report = JSON.parse(await readFile(reportPath, "utf8"));
const thresholds = {
  performance: 0.9,
  accessibility: 0.95,
  "best-practices": 0.95,
};

for (const [category, threshold] of Object.entries(thresholds)) {
  const score = report.categories?.[category]?.score;
  if (typeof score !== "number" || score < threshold) {
    throw new Error(
      `Lighthouse ${category} score ${String(score)} is below ${threshold}`,
    );
  }
  process.stdout.write(`${category}: ${score.toFixed(2)}\n`);
}
