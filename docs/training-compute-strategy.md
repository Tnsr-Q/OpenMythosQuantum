# Training Compute Strategy (Week 1 Decision)

## Decision Summary

**Decision:** Use an **AWS-first compute strategy** for Katopu training execution.

Why this is the Week 1 decision:
- aligns with Katopu's quantum + AGI direction (AWS has practical paths for both GPU training and quantum simulation integration),
- supports staged maturity (start lean, scale without full platform rewrite),
- gives strong operational controls for budget caps and rollback.

## Provider Selection

### Selected Provider: AWS

Primary services:
- **SageMaker Training Jobs** for managed model training orchestration,
- **EKS + Karpenter** for custom distributed or experimental AGI workloads,
- **S3** for datasets, checkpoints, and artifacts,
- **CloudWatch + Budgets** for enforcement and visibility,
- **(Optional Phase 2) AWS Braket simulators** for quantum-adjacent experimentation.

### Why not alternate-first this week
- Multi-cloud in Week 1 adds coordination overhead without immediate ROI.
- On-prem/GPU colocation is powerful but slows initial delivery cadence.
- Cheapest spot-only providers are cost-effective but increase operational fragility for first production hardening.

## Budget Envelope (Month 1)

### Target Cap
- **Hard budget cap:** **$1,500/month**
- **Soft warning threshold:** **$1,100/month**

### Planned Allocation
- **GPU training workloads:** $900
- **Storage + artifact retention (S3):** $150
- **Orchestration/control plane (EKS/SageMaker overhead):** $250
- **Monitoring/logging/networking:** $100
- **Contingency reserve:** $100

## Phase Gates

### Phase A (Week 1-2): Controlled Validation
- Single-region deployment.
- One baseline training template (small/medium model profile).
- Checkpoint every N steps to S3.
- Daily budget checks.

**Exit criteria:**
- at least 3 successful training runs,
- webhook signing + verification validated end-to-end,
- monthly burn-rate forecast remains within cap.

### Phase B (Week 3-4): Throughput Improvement
- Add queue-aware scheduling for training jobs.
- Add spot-instance fallback strategy with retry policy.
- Add model-class-specific resource presets.

**Exit criteria:**
- p95 queue wait time below target,
- <5% failed jobs due to infra preemption,
- repeatable runbook for incident response.

## Rollback Triggers

Rollback to minimal managed profile (SageMaker-only, no EKS custom runners) if any of the following occur:
- projected monthly spend exceeds **$1,500** for 3 consecutive days,
- training job failure rate exceeds 10% due to infra causes,
- checkpoint restore fails in more than one controlled test.

## Week 1 Implementation Checklist

- [ ] Create AWS budget with hard alerts at 75%, 90%, 100%.
- [ ] Define two training profiles: `baseline-small`, `baseline-medium`.
- [ ] Store checkpoints and metadata in versioned S3 paths.
- [ ] Record run metadata for each job (`trainingId`, profile, cost estimate, duration).
- [ ] Keep OpenAPI contract as source-of-truth for control-plane requests.

## OpenMythos Alignment Notes

- **Plugin architecture:** training optimization strategies should be loaded as plugins (not hardcoded into core API handlers).
- **Docs structure:** each training profile should have copy/paste-ready API examples.
- **CI validation:** compute config templates and API contract checks should run in CI before merge.
