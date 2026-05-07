# Phasmid Non-Claims

This document lists protections or guarantees that Phasmid does not provide.
Each item includes a brief rationale to keep review and deployment decisions explicit.

## Non-Claims

- Phasmid does not provide perfect deniability.  
  Rationale: behavior and artifacts are reduced, not eliminated, and depend on host conditions.

- Phasmid does not provide guaranteed secure deletion.  
  Rationale: flash media behavior, wear leveling, and host storage layers prevent absolute erase guarantees.

- Phasmid does not provide protection against compromised hosts.  
  Rationale: malware, kernel compromise, and privileged tracing can bypass local software controls.

- Phasmid does not provide protection against malware or keyloggers.  
  Rationale: local input capture defeats passphrase and workflow hygiene controls.

- Phasmid does not provide protection against live memory capture.  
  Rationale: in-use key material can be exposed by privileged memory inspection.

- Phasmid does not provide protection against camera observation.  
  Rationale: shoulder-surfing and direct visual capture are outside software-only defenses.

- Phasmid does not provide protection against coercion after disclosure.  
  Rationale: once disclosure has occurred, software cannot enforce human-safety outcomes.

- Phasmid does not provide certified classified-data handling.  
  Rationale: the project is a field-evaluation prototype and not a certified records system.

- Phasmid does not provide remote management, remote wipe, or remote unlock.  
  Rationale: local-only posture is a core project boundary.

- Phasmid does not provide communications security, anonymity, censorship bypass, or surveillance evasion.  
  Rationale: the project scope is local storage behavior, not network transport or anti-censorship systems.

- Phasmid does not provide forensic-grade unverifiable deniability.  
  Rationale: host-level traces and operational artifacts can remain detectable under expert forensic analysis.

- Phasmid does not provide protection in jurisdictions where key disclosure refusal is criminalized.  
  Rationale: legal coercion outcomes are determined by law and court process, not cryptographic design.

- Phasmid does not provide protection against trained forensic examination of host artifacts unless target-hardened deployment is followed.  
  Rationale: deployment controls (tmpfs, local-only binding, hardened host policy) materially affect artifact exposure.

- Phasmid does not promise a single maintainer (bus factor 1) sustainability guarantee.  
  Rationale: long-term response capacity and maintenance continuity can be constrained by single-maintainer limits.
