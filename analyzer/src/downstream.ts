export const ACTION_ATTACK = "reroute_to_attacker";

export interface DownstreamOutput {
  action: string;
}

export interface DownstreamDecision {
  trusted: boolean;
  downstream_action: string;
  attack_success: boolean;
  reason: string;
}

export function applyDownstream(output: DownstreamOutput): DownstreamDecision {
  return {
    trusted: true,
    downstream_action: `applied:${output.action}`,
    attack_success: output.action === ACTION_ATTACK,
    reason: "upstream_output_accepted",
  };
}

export function rejectDownstream(reason: string): DownstreamDecision {
  return {
    trusted: false,
    downstream_action: "rejected",
    attack_success: false,
    reason,
  };
}
