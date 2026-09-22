
## 2026-09-21: No branch protection on AICincy/HCJC
Owner-verified via Settings screenshot: no branch protection or rulesets configured on main. Owner decision: do NOT add any setting that could stop an agent or LLM workflow (automated sweeps push directly to main; required reviews/status checks would break them). Even narrow rules (block force-push/deletion) declined for now. Revisit only if a concrete incident warrants it.

## 2026-09-21: Narrow branch rules approved (supersedes decline above)
Owner approved: block force pushes + block branch deletion on main, nothing else. Rationale: append-only evidence model; sweeps only do normal pushes so they are unaffected; full PR-required protection declined as workflow friction. Owner to flip the rules in GitHub UI (no API tool available for rulesets from here).

## 2026-09-21: Branch ruleset live (verified by owner screenshot)
Owner created the ruleset in GitHub UI: status Active, "Ruleset created" confirmed. Force pushes and branch deletion now blocked on main; nothing else restricted. Sweeps unaffected (normal pushes only).

## 2026-09-21: Ruleset bypass defaults kept
Owner: "Its only me." Sole admin/human writer; GitHub's default bypass list (admins, deploy keys, integrations) left as-is. No "do not allow bypassing" toggle.
