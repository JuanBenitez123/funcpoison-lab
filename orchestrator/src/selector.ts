// Core of the project. DETERMINISTIC parametric selector.
//
// The fixture's `poisoned` field is not an input to the score.
//
//   score = semantic_relevance(task, tool.description)
//         + template_bias * template_feature(tool.description)
//
// - semantic_relevance: fraction of task tokens that appear in the description
//   (recall; inspectable, no embeddings).
// - template_feature: 1 if the description contains a `call name(...)`
//   invocation, else 0. Intensity is controlled only by `template_bias`.
// - template_bias: experimental parameter.

import type { ToolDefinition } from "./registry.ts";

export interface SelectorConfig {
  templateBias: number;
}

export interface ScoredTool {
  tool: ToolDefinition;
  semanticRelevance: number;
  templateFeature: number;
  score: number;
}

const STOPWORDS = new Set([
  "a",
  "an",
  "the",
  "to",
  "from",
  "and",
  "or",
  "of",
  "for",
  "in",
  "on",
  "at",
  "by",
  "with",
]);

const INVOCATION_RE = /\bcall\s+[A-Za-z_][A-Za-z0-9_]*\s*\([^)]*\)/;

export function tokenize(text: string): string[] {
  return text
    .toLowerCase()
    .split(/[^a-z0-9]+/)
    .filter((tok) => tok.length > 0 && !STOPWORDS.has(tok));
}

export function semanticRelevance(task: string, description: string): number {
  const taskTokens = [...new Set(tokenize(task))];
  if (taskTokens.length === 0) return 0;
  const descTokens = new Set(tokenize(description));
  const overlap = taskTokens.filter((tok) => descTokens.has(tok)).length;
  return overlap / taskTokens.length;
}

export function templateFeature(description: string): number {
  return INVOCATION_RE.test(description) ? 1 : 0;
}

export function scoreTools(
  task: string,
  tools: ToolDefinition[],
  config: SelectorConfig
): ScoredTool[] {
  return tools
    .map((tool) => {
      const sr = semanticRelevance(task, tool.description);
      const tf = templateFeature(tool.description);
      return {
        tool,
        semanticRelevance: sr,
        templateFeature: tf,
        score: sr + config.templateBias * tf,
      };
    })
    .sort((a, b) => b.score - a.score || a.tool.name.localeCompare(b.tool.name));
}

export function selectTool(
  task: string,
  tools: ToolDefinition[],
  config: SelectorConfig
): ScoredTool {
  const ranked = scoreTools(task, tools, config);
  if (ranked.length === 0) {
    throw new Error("no tools to select");
  }
  return ranked[0];
}
