| Registry State | Output Validation | Tool selected | Output modified | Downstream | Attack success | Expected |
|---|---|---|---|---|---|---|
| trusted | off | legit_route_planner | False | applied:navigate_safe | False | normal |
| trusted | on | legit_route_planner | False | applied:navigate_safe | False | normal |
| compromised | off | malicious_tool | True | applied:reroute_to_attacker | True | attack_succeeds |
| compromised | on | malicious_tool | True | rejected | False | attack_contained |
