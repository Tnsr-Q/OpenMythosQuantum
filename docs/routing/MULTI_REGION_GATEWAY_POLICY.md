# Multi-Region Gateway Policy (Lightweight, Deterministic)

## 1) Objective

Define a lightweight policy layer for multi-region quantum job routing that:
- optimizes cost and latency,
- preserves execution fidelity,
- avoids heavy infrastructure lock-in,
- remains falsifiable via deterministic simulation fixtures.

This policy is designed to run as middleware and align with the repository's plugin-oriented gateway patterns.

---

## 2) Architecture: Cached-State Policy Execution

### 2.1 Components

1. **Telemetry Ingest**
   - Pulls node telemetry from region-local collectors.
   - Produces an eventually consistent cache entry per node.

2. **Distributed Cache (lightweight state)**
   - Stores recent node telemetry used by policy execution.
   - Prevents per-request telemetry fan-out to every target node.

3. **Policy Evaluator (middleware)**
   - Applies hard gates first, then deterministic weighted scoring.
   - Returns selected route or typed error.

4. **Decision Trace Emitter**
   - Emits structured reason codes and scored dimensions for auditability.

### 2.2 Telemetry Freshness Contract

| Signal | Max Staleness (TTL) | On stale data |
|---|---:|---|
| `cost_per_shot` | 60s | mark score uncertain, continue unless all nodes stale |
| `queue_depth` | 5s | apply `STALE_QUEUE_PENALTY` |
| `avg_wait_per_job_ms` | 30s | use last value; if unavailable, disqualify candidate |
| `region_rtt_ms` | 30s | use rolling median RTT; if unavailable, use regional default and mark uncertain |
| `hardware_fidelity` inputs (`t1_us`, `t2_us`, `median_2q_error`) | 30s | disqualify candidate if `job.strict_routing=true` or `job.minimum_required_fidelity` is set; otherwise mark fidelity scoring uncertain and continue |
| `fallback_status` | 3s | treat as `DEGRADED` |
| `topology_graph` | 300s | continue (topology is quasi-static) |

If all candidates are filtered due to staleness and policy mode is strict, return `503 ROUTING_STATE_UNAVAILABLE`.

---

## 3) Routing Signals

Required signals per candidate target:

- `signal.cost_per_shot` (USD)
- `signal.region` (region ID)
- `signal.queue_depth` (integer)
- `signal.avg_wait_per_job_ms` (moving average queue service time)
- `signal.region_rtt_ms` (network RTT from gateway to target region)
- `signal.fallback_status` in `{UP, DEGRADED, DOWN}`
- `signal.hardware_fidelity`
  - `t1_us`
  - `t2_us`
  - `median_2q_error` (0..1)
- `signal.topology_match`
  - `swap_penalty_ratio` (estimated extra SWAP gates / total two-qubit gates)
  - `embeddable` boolean

Job-scoped constraints:

- `job.minimum_required_fidelity` (0..1)
- `job.max_queue_latency_ms`
- `job.strict_routing` boolean
- `job.optimize_for` in `{balanced, cost, latency, fidelity}`

---

## 4) Deterministic Policy Logic

### 4.1 Hard gates (must pass)

A candidate is discarded if any condition is true:

1. `fallback_status == DOWN`
2. `estimated_queue_latency_ms > job.max_queue_latency_ms`
3. `fidelity_effective < job.minimum_required_fidelity`
4. `job.strict_routing == true && topology.embeddable == false`

When multiple hard gates fail for the same candidate, record all failures in `disqualification_reasons[]`.

If all candidates are discarded, apply deterministic error precedence:
1. return `422 TOPOLOGY_MISMATCH` if `job.strict_routing == true` and every health-eligible candidate failed topology embeddability,
2. else return `422 FIDELITY_CONSTRAINT_UNSATISFIED` if every health-eligible candidate failed fidelity,
3. else return `503 NO_ELIGIBLE_TARGET`.

### 4.2 Normalization constants (policy v1)

```text
REF_T1_US = 120
REF_T2_US = 150
MAX_ACCEPTABLE_2Q_ERROR = 0.03
SWAP_PENALTY_SOFT_LIMIT = 0.40
STALE_QUEUE_PENALTY = 0.15
DEGRADED_STATUS_PENALTY = 0.20
```

### 4.3 Intermediate metrics

For each candidate `i`:

```text
t1_norm_i = clamp(t1_us / REF_T1_US, 0, 1)
t2_norm_i = clamp(t2_us / REF_T2_US, 0, 1)
err_norm_i = clamp(1 - (median_2q_error / MAX_ACCEPTABLE_2Q_ERROR), 0, 1)

hardware_fidelity_i = 0.35*t1_norm_i + 0.35*t2_norm_i + 0.30*err_norm_i

topology_score_i = if embeddable then clamp(1 - (swap_penalty_ratio / SWAP_PENALTY_SOFT_LIMIT), 0, 1) else 0

fidelity_effective_i = 0.70*hardware_fidelity_i + 0.30*topology_score_i

estimated_queue_latency_ms_i = queue_depth * avg_wait_per_job_ms_i + region_rtt_ms_i
```

### 4.4 Cost and latency normalization across remaining candidates

Let `R` be the set of candidates that passed hard gates.

```text
cost_score_i =
  if max(cost)-min(cost) == 0 then 1
  else 1 - ((cost_i - min(cost)) / (max(cost)-min(cost)))

latency_score_i =
  if max(lat)-min(lat) == 0 then 1
  else 1 - ((lat_i - min(lat)) / (max(lat)-min(lat)))
```

Apply penalties and score ordering:

```text
if queue telemetry stale: latency_score_i = max(0, latency_score_i - STALE_QUEUE_PENALTY)

base_score_i = w_cost*cost_score_i + w_latency*latency_score_i + w_fidelity*fidelity_effective_i + w_region*region_score_i

if fallback_status == DEGRADED:
  final_score_i = max(0, base_score_i - DEGRADED_STATUS_PENALTY)
else:
  final_score_i = base_score_i
```

### 4.5 Weight profiles

```text
balanced: w_cost=0.30, w_latency=0.25, w_fidelity=0.35, w_region=0.10
cost:     w_cost=0.55, w_latency=0.20, w_fidelity=0.20, w_region=0.05
latency:  w_cost=0.15, w_latency=0.55, w_fidelity=0.20, w_region=0.10
fidelity: w_cost=0.10, w_latency=0.15, w_fidelity=0.65, w_region=0.10
```

`region_score_i` is `1` for preferred region, else `0.7` for same legal zone, else `0.4`.

Final score after penalties:

```text
final_score_i = max(0, base_score_i - degraded_penalty_i)
degraded_penalty_i = DEGRADED_STATUS_PENALTY if fallback_status == DEGRADED else 0
```

Choose candidate with highest `final_score`.
Tie-breakers (deterministic):
1. lower `cost_per_shot`,
2. lower `estimated_queue_latency_ms`,
3. lexicographically smaller `node_id`.

---

## 5) Error Semantics

- `422 TOPOLOGY_MISMATCH`: strict routing requested and no embeddable topology survives.
- `422 FIDELITY_CONSTRAINT_UNSATISFIED`: no candidate meets required fidelity.
- `503 NO_ELIGIBLE_TARGET`: all candidates removed by health/latency constraints.
- `503 ROUTING_STATE_UNAVAILABLE`: strict mode and telemetry state too stale.

---

## 6) Decision Trace Contract

Each routing decision should emit:

- `policy_version`
- `job_id`
- `candidate_scores[]` with
  - `node_id`
  - `cost_score`
  - `latency_score`
  - `hardware_fidelity`
  - `topology_score`
  - `fidelity_effective`
  - `final_score`
  - `disqualification_reasons[]`
- `selected_node_id` or `error_code`

---

## 7) Falsifiable Simulation Fixtures

Fixtures are versioned JSON payloads under:

- `tests/fixtures/routing/sim_alpha_cost_vs_queue.json`
- `tests/fixtures/routing/sim_beta_fidelity_override.json`
- `tests/fixtures/routing/sim_gamma_topology_mismatch.json`

### 7.1 Simulation Alpha: Cost vs Queue Depth

Expectation:
- with `optimize_for=cost`, route to cheaper node while queue latency is below threshold,
- if queue threshold is exceeded, route shifts to lower-latency candidate.

### 7.2 Simulation Beta: Fidelity Override

Expectation:
- cheap but degraded calibration target is rejected for depth-sensitive job,
- expensive high-fidelity target wins.

### 7.3 Simulation Gamma: Topology Mismatch

Expectation:
- strict routing with non-embeddable topology produces `422 TOPOLOGY_MISMATCH`.

---

## 8) Compatibility with Plugin-Oriented Gateway

This policy is intentionally middleware-friendly:

- reads from cached telemetry interface (`get_node_snapshot(node_id)`),
- is pure and deterministic given the snapshot set and job request,
- can be wrapped as a plugin stage in existing registry-based loading,
- emits immutable decision records suitable for snapshot/freeze patterns.

---

## 9) Policy Versioning

- Initial version: `gateway_policy_v1.0.0`
- Any change to formula constants, hard gates, or tie-breakers increments minor/major version.
- Fixtures must declare the policy version and remain reproducible.
