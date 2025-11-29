# SOP 02: Incident Response

## 1. Overview
This SOP defines the response plan for system incidents (outages, performance degradation, security alerts).

## 2. Severity Levels

| Level | Description | Response Time |
|-------|-------------|---------------|
| SEV-1 | Critical Outage (Data loss, System down) | 15 mins |
| SEV-2 | Major Issue (Feature broken, High Latency) | 1 hour |
| SEV-3 | Minor Issue (Bug, UI glitch) | 24 hours |

## 3. Response Process

### 3.1 Detection
- Alerts triggered by Monitoring system (Prometheus/Grafana).
- User reports.

### 3.2 Triage
1.  **Acknowledge** the alert.
2.  **Verify** the issue (reproduce).
3.  **Assign** Severity Level.

### 3.3 Mitigation
- **SEV-1:** Focus on restoring service. Rollback recent changes if necessary.
- **SEV-2:** Investigate root cause. Apply hotfix.

### 3.4 Post-Mortem
- Required for all SEV-1 and SEV-2 incidents.
- Document: Root Cause, Timeline, Resolution, Preventive Actions.

## 4. Contact List
- **On-Call Engineer:** [Phone/Slack]
- **Database Admin:** [Phone/Slack]
