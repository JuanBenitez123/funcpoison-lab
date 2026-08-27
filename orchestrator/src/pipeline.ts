import type { ToolDefinition } from "./registry.ts";
import { scoreTools, type ScoredTool } from "./selector.ts";
import { executeTool, isAttackOutput, type ToolOutput } from "./tools/execute.ts";

export interface PipelineResult {
  ranked: ScoredTool[];
  selected: ScoredTool;
  output: ToolOutput;
}

export function selectAndExecute(
  task: string,
  tools: ToolDefinition[],
  templateBias: number
): PipelineResult {
  if (tools.length === 0) {
    throw new Error("empty registry");
  }
  const ranked = scoreTools(task, tools, { templateBias });
  const selected = ranked[0];
  const output = executeTool(selected.tool.name);
  return { ranked, selected, output };
}

export function publicScores(ranked: ScoredTool[]) {
  return ranked.map((row) => ({
    name: row.tool.name,
    semantic_relevance: row.semanticRelevance,
    template_feature: row.templateFeature,
    score: row.score,
  }));
}

export { isAttackOutput };
