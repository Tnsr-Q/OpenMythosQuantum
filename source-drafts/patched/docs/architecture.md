# Architecture notes

## Async heavy workloads

Heavy simulations should use:
- `POST /circuits/{circuitId}/parallel-simulate`
- `GET /simulation-jobs/{jobId}`

This prevents HTTP timeout issues common with long-running synchronous calls.

## Deterministic verification

`POST /circuits/{circuitId}/optimize` returns a verification summary.
Detailed verification is available at:
- `GET /verifications/{verificationId}`

## Feedback and model updates

Feedback is collected through:
- `POST /feedback`
- `GET /feedback/{feedbackId}`

Model updates are controlled through:
- `POST /models/update`

## Controlled releases

Version lifecycle endpoints:
- `POST /versions/release`
- `POST /versions/rollback`
