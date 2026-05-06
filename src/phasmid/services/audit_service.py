from __future__ import annotations

from ..models.audit import AuditEntry, AuditReport, AuditSection


def build_audit_report() -> AuditReport:
    return AuditReport(
        sections=[
            AuditSection(
                title="System Position",
                entries=[
                    AuditEntry("Status", "research-grade prototype"),
                    AuditEntry("Purpose", "coercion-aware deniable storage"),
                    AuditEntry("Scope", "local deniable container operations"),
                    AuditEntry("Non-claims", "not forensic-proof / not coercion-proof"),
                ],
            ),
            AuditSection(
                title="Cryptographic Controls",
                entries=[
                    AuditEntry("AEAD", "configured backend"),
                    AuditEntry("KDF", "configured backend"),
                    AuditEntry("Header", "absent"),
                    AuditEntry("Magic bytes", "absent"),
                    AuditEntry("Metadata", "minimized"),
                ],
            ),
            AuditSection(
                title="Operational Controls",
                entries=[
                    AuditEntry("Secrets in config", "no"),
                    AuditEntry("Passphrase logging", "no"),
                    AuditEntry("Destructive confirm", "required"),
                    AuditEntry("Profile stores secrets", "no"),
                    AuditEntry("Shell history risk", "visible in Doctor"),
                ],
            ),
            AuditSection(
                title="Logging Policy",
                entries=[
                    AuditEntry("Passphrases logged", "no"),
                    AuditEntry("Key material logged", "no"),
                    AuditEntry("File contents logged", "no"),
                    AuditEntry("Path redaction", "applied where appropriate"),
                    AuditEntry("Audit log", "append-only event log"),
                ],
            ),
            AuditSection(
                title="Known Limitations",
                entries=[
                    AuditEntry("Host compromise", "may defeat confidentiality"),
                    AuditEntry("OS artifacts", "may reveal usage"),
                    AuditEntry("Coercion resistance", "procedural, not absolute"),
                    AuditEntry("Deniability", "depends on operational context"),
                    AuditEntry("Side channels", "not systematically addressed"),
                    AuditEntry("Memory forensics", "not addressed"),
                ],
            ),
            AuditSection(
                title="Non-Claims",
                entries=[
                    AuditEntry("forensic-proof", "not claimed"),
                    AuditEntry("coercion-proof", "not claimed"),
                    AuditEntry("undetectable", "not claimed"),
                    AuditEntry("unbreakable", "not claimed"),
                    AuditEntry("military-grade", "not claimed"),
                    AuditEntry("guaranteed safe", "not claimed"),
                ],
            ),
        ]
    )


class AuditService:
    def get_report(self) -> AuditReport:
        return build_audit_report()
