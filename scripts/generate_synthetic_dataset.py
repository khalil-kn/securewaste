#!/usr/bin/env python3
"""Synthetic dataset generator for SecureWaste document classification (Sprint 2: SCRUM-19/20/21).

Generates balanced synthetic documents across four classification labels:
- Public: No sensitive data
- Internal: Emails, phone numbers, keywords
- Confidential: Payment cards, IBANs, national IDs, passports, confidentiality labels
- Highly Confidential: API keys, secrets, private keys

All data is synthetic/fictional - no real company or personal data.
"""

from __future__ import annotations

import random
import string
from dataclasses import dataclass
from pathlib import Path

# =============================================================================
# Configuration
# =============================================================================

CLASSIFICATION_LABELS = ["Public", "Internal", "Confidential", "Highly Confidential"]

# Target samples per class for balanced dataset
SAMPLES_PER_CLASS = 50

# Output directory
OUTPUT_DIR = Path("tests/fixtures/synthetic_dataset")

# Random seed for reproducibility
SEED = 42

random.seed(SEED)


# =============================================================================
# Synthetic Data Templates
# =============================================================================

# Public documents - no sensitive content
# Varied document types: emails, reports, tutorials, announcements, policies, blog posts
PUBLIC_TEMPLATES = [
    # Short emails/messages
    "Hi team, just a reminder about our standup tomorrow at 9am in the main conference room.",
    "Thanks for the quick review on the PR. I've addressed your comments and pushed the updates.",
    "The office will be closed next Friday for the company holiday. Enjoy the long weekend!",
    "Lunch and learn session this Thursday at noon - topic: 'Intro to GraphQL'. Pizza provided.",
    "Welcome aboard Sarah! Your desk is on the 3rd floor, badge access already configured.",
    
    # Meeting notes & agendas
    """Meeting Notes - Project Atlas Sync - {date}

Attendees: {attendees}

Discussion:
1. Sprint velocity trending up 12% this quarter - good momentum
2. Blockers: waiting on design review for checkout flow (targeting Tuesday)
3. New hire ramp-up: both junior devs shipping features by week 3
4. Technical debt: allocated 15% capacity for refactoring auth module

Decisions:
- Proceed with React 18 upgrade after Q3 release
- Adopt ESLint flat config for new projects

Action Items:
- {action_owner_1}: finalize API spec by {action_date_1}
- {action_owner_2}: schedule load test for payment service
- {action_owner_3}: update runbook for new deployment process""",
    
    """Quarterly All-Hands - Q{quarter} {year} Highlights

Company Metrics:
- Revenue: ${revenue:,.0f} (+{growth}% YoY)
- Headcount: {headcount} ({new_hires} new hires this quarter)
- Customer NPS: {nps} (industry avg: 42)

Product Updates:
- Launched: Mobile app v3.2 with dark mode
- Shipped: Real-time collaboration features
- Beta: AI-powered code suggestions (opt-in)

Engineering:
- Deploy frequency: {deploy_freq}/week (target: 50)
- P95 latency: {p95_ms}ms (down from {p95_prev}ms)
- Incident count: {incidents} (target: < 5/month)

People:
- Promotions: {promotions} engineers to Senior/Staff
- Learning budget: ${learning_budget:,.0f} utilized
- Hackathon winners: {hackathon_winners}""",
    
    # Tutorials & documentation
    """Getting Started with {technology}

Prerequisites:
- {prereq_1}
- {prereq_2}
- Basic understanding of {concept}

Installation:
```bash
# Using pip
pip install {package_name}

# Or with poetry
poetry add {package_name}
```

Quick Start:
```python
from {module_name} import Client

client = Client(api_key="your-key-here")
result = client.process("hello world")
print(result)
```

Configuration:
Create a `.env` file:
```
{CONFIG_PREFIX}_API_KEY=your-key
{CONFIG_PREFIX}_ENDPOINT=https://api.example.com
{CONFIG_PREFIX}_TIMEOUT=30
```

Common Issues:
| Error | Solution |
|-------|----------|
| Connection timeout | Check firewall / proxy settings |
| Invalid API key | Verify key in dashboard |
| Rate limited | Implement exponential backoff |

Next Steps:
- Read the full API reference at docs.example.com
- Join our Discord community for support
- Check out the examples repository on GitHub""",
    
    # Blog posts & articles
    """{title}

By {author} | {date} | {read_time} min read

{intro_paragraph}

{main_paragraph_1}

{main_paragraph_2}

Key Takeaways:
- {takeaway_1}
- {takeaway_2}
- {takeaway_3}

{conclusion}

Tags: {tags}
---""",
    
    # Policies & announcements
    """Company Policy Update: {policy_name}

Effective: {effective_date}

Summary:
{policy_summary}

What's Changing:
{changes_list}

What You Need to Do:
{action_items}

Questions?
Contact {contact_team} at {contact_email} or visit the internal wiki.

---
This is an automated notification from {sender}.""",
    
    # Technical blog / engineering posts
    """How We {achievement} at {company_name}

Background:
{background_context}

The Challenge:
{challenge_description}

Our Approach:
{approach_details}

Results:
- {metric_1}: {value_1}
- {metric_2}: {value_2}
- {metric_3}: {value_3}

Lessons Learned:
{lessons_learned}

What's Next:
{next_steps}

---
{author} is a {role} at {company_name}. Connect on LinkedIn/Twitter.""",
    
    # Release notes
    """Release Notes: {product_name} v{version}

Released: {release_date}

🎉 New Features:
{new_features}

🐛 Bug Fixes:
{bug_fixes}

🔧 Improvements:
{improvements}

⚠️ Breaking Changes:
{breaking_changes}

📦 Dependencies:
- Updated: {updated_deps}
- Added: {added_deps}

Full changelog: {changelog_url}
Upgrade guide: {upgrade_guide_url}""",
]

# Internal documents - emails, phones, keywords, internal reports, onboarding, audit
# Varied: HR, IT, security, finance, project management, team communications
INTERNAL_TEMPLATES = [
    # Short emails/messages
    "Hey, can you review the PR for the new auth middleware? Thanks!",
    "FYI - the staging deployment is scheduled for 2pm today. Let me know if any concerns.",
    "Quick sync on the API rate limiting issue? I'm free after 3pm.",
    "The new hire laptop arrived. Can IT set it up before Monday?",
    "Expense report for AWS re:Invent submitted. Receipt attached.",
    
    # HR & onboarding
    """Welcome to the Team - {employee_name}

Role: {role} | Team: {onboarding_team} | Start Date: {date}
Manager: {manager_name} ({manager_email}) | Buddy: {buddy_name} ({buddy_email})

Your First Week:
Day 1: Orientation (9am), IT setup (10am), Team lunch (12:30pm), 1:1 with manager (3pm)
Day 2: Security training (mandatory), Access provisioning, Codebase tour
Day 3: {system_1} deep dive, {system_2} hands-on, First commit!
Day 4: Architecture overview with {architect_name}, Pair programming session
Day 5: Sprint planning participation, 30-day goals review

Key Contacts:
- HR: {hr_name} ({hr_email}) - benefits, policies
- IT: {it_name} ({it_email}) - access, hardware, tools
- Security: {security_name} ({security_email}) - VPN, MFA, secrets

Resources:
- Internal wiki: wiki.company.internal
- Engineering handbook: handbook.company.internal
- Onboarding checklist: onboarding.company.internal/{employee_id}

Welcome aboard! 🎉""",
    
    """Performance Review - {employee_name} ({review_cycle})

Role: {role} | Level: {level} | Manager: {manager_name}

Achievements:
{achievements}

Strengths:
{strengths}

Areas for Growth:
{growth_areas}

Goals for Next Period:
{next_goals}

Compensation Discussion:
Current: ${current_comp:,.0f} | Market: ${market_comp:,.0f}
Recommended adjustment: {adjustment_pct}%

Signatures:
Employee: _____________________ Date: _______
Manager: _____________________ Date: _______""",
    
    # IT & Security
    """IT Security Advisory - {advisory_id}

Date: {date} | Severity: {severity} | Status: {status}
Affected: {affected_systems}

Summary:
{summary}

Technical Details:
{technical_details}

Impact:
{impact_assessment}

Required Actions:
1. {action_1} (Owner: {owner_1}, Due: {due_1})
2. {action_2} (Owner: {owner_2}, Due: {due_2})
3. {action_3} (Owner: {owner_3}, Due: {due_3})

Workaround:
{workaround}

References:
- CVE-{cve_year}-{cve_id}
- Internal ticket: {ticket_id}

Contact: security@company.internal | #security-alerts on Slack""",
    
    """Incident Retrospective - INC-{incident_id}

Date: {date} | Duration: {duration_min} minutes | Severity: SEV-{severity}

Timeline:
{timeline}

Root Cause:
{root_cause}

Impact:
- Users affected: {users_affected:,}
- Revenue impact: \${revenue_impact:,.0f}
- SLA breach: {sla_breach}

What Went Well:
{went_well}

What Went Wrong:
{went_wrong}

Action Items:
{action_items}

Follow-up: {followup_date}""",
    
    # Project & Finance
    """Project Proposal: {project_name}

Author: {author_name} ({author_email}) | Date: {date}
Sponsor: {sponsor_name} ({sponsor_email})

Executive Summary:
{exec_summary}

Problem Statement:
{problem_statement}

Proposed Solution:
{solution_description}

Resource Request:
- Engineering: {eng_fte} FTEs ({eng_cost:,.0f}/month)
- Design: {design_fte} FTEs ({design_cost:,.0f}/month)
- PM: {pm_fte} FTE ({pm_cost:,.0f}/month)
- Infrastructure: \${infra_cost:,.0f}/month
Total: \${total_cost:,.0f} over {duration_months} months

Success Metrics:
{success_metrics}

Risks & Mitigations:
{risks_mitigations}

Approval Required: {approvers}""",
    
    """Quarterly Budget Review - {department} - Q{quarter} {year}

Budget Allocated: \${allocated:,.0f}
Budget Spent: \${spent:,.0f} ({spent_pct}%)
Variance: \${variance:,.0f} ({variance_pct}%)

Top Expenses:
1. {expense_1}: \${amt_1:,.0f}
2. {expense_2}: \${amt_2:,.0f}
3. {expense_3}: \${amt_3:,.0f}

Forecast Next Quarter:
{forecast}

Decisions Needed:
{decisions}""",
    
    # Team communications
    """Team Sync Notes - {team_sync_name} - {date}

Attendees: {attendees}

Updates:
{updates}

Discussion Items:
1. {discussion_1}
2. {discussion_2}
3. {discussion_3}

Decisions:
{decisions}

Action Items:
{action_items}

Parking Lot:
{parking_lot}""",
    
    """Engineering Design Review - {feature_name}

Author: {author_name} | Reviewers: {reviewers}
Date: {date} | Status: {status}

Context:
{context}

Proposed Design:
{design_description}

Alternatives Considered:
{alternatives}

Trade-offs:
{tradeoffs}

Security Considerations:
{security_considerations}

Testing Strategy:
{testing_strategy}

Rollout Plan:
{rollout_plan}

Open Questions:
{open_questions}""",
]

# Confidential documents - payment cards, IBANs, IDs, labels, contracts, financial
# Varied: contracts, payroll, financial reports, legal agreements, vendor docs
CONFIDENTIAL_TEMPLATES = [
    # Short documents
    "Invoice #{id}: Payment card {card} for {amount}. CONFIDENTIAL",
    "Bank transfer: IBAN {iban} for {amount}. Reference: {ref}. CONFIDENTIAL",
    "Employee record: National ID {national_id} - {name}. CONFIDENTIAL",
    "Passport copy: {passport} for {name} travel. CONFIDENTIAL",
    "Client contract: Payment terms {card}. IBAN: {iban}. CONFIDENTIAL",
    "Payroll data: Employee {national_id} salary {amount}. CONFIDENTIAL",
    "Vendor payment: Card {card} IBAN {iban} amount {amount}. CONFIDENTIAL",
    "Travel booking: Passport {passport} for {name}. CONFIDENTIAL",
    "Financial statement: Account {iban} balance {amount}. CONFIDENTIAL",
    "Audit trail: Transaction {card} verified. CONFIDENTIAL",
    
    # Legal contracts & agreements
    """Master Services Agreement - {msa_id}

Between: {client_name} ("Client") and {vendor_name} ("Vendor")
Effective Date: {effective_date}
Classification: CONFIDENTIAL

1. Services
Vendor shall provide {service_description} in accordance with the attached
Statement of Work (Exhibit A).

2. Fees & Payment
Total Contract Value: ${total_value:,.2f}
Payment Terms: {payment_terms}
Invoicing: {invoicing_schedule}
Wire Instructions:
  Bank: {bank_name}
  Account: {account_number}
  Routing: {routing_number}
  SWIFT: {swift_code}

3. Confidentiality
Both parties acknowledge that Confidential Information includes, but is not
limited to: pricing, technical architectures, customer data, trade secrets,
business strategies, and any information marked "CONFIDENTIAL".

4. Data Protection
Vendor shall comply with all applicable data protection laws including GDPR,
CCPA, and HIPAA where applicable. Data Processing Addendum (Exhibit B).

5. Intellectual Property
Pre-existing IP remains with original owner. Work product IP assigns to Client
upon full payment.

6. Limitation of Liability
Neither party liable for indirect, consequential, or punitive damages.
Vendor's aggregate liability capped at 12 months' fees.

7. Term & Termination
Initial Term: {term_months} months. Auto-renewal for successive 12-month
periods unless 60 days written notice.
Termination for cause: 30 days cure period.

Signatures:
Client: _________________________ Date: __________
Vendor: _________________________ Date: __________""",
    
    """Non-Disclosure Agreement - {nda_id}

Parties: {party_a} and {party_b}
Effective: {effective_date}
Classification: CONFIDENTIAL

Purpose: {purpose}

Confidential Information includes:
- Financial projections and metrics
- Technical architectures and source code
- Customer lists and pipeline data
- Product roadmaps and unreleased features
- Pricing models and discount structures
- Personnel compensation data

Obligations:
1. Use Confidential Information solely for the Purpose
2. Restrict access to need-to-know personnel under NDA
3. Protect with same degree of care as own confidential information
4. No reverse engineering, decompilation, or disassembly
5. Return/destroy upon request or termination

Term: {term_years} years from disclosure
Survival: Confidentiality obligations survive {survival_years} years

Governing Law: {governing_law}
Jurisdiction: {jurisdiction}

Signatures:
{party_a}: _________________________ Date: __________
{party_b}: _________________________ Date: __________""",
    
    # Financial reports
    """Quarterly Financial Report - {entity_name} - Q{quarter} {year}

Prepared by: {preparer_name} | Date: {date}
Classification: CONFIDENTIAL
Distribution: CFO, Controller, Board Audit Committee

=== INCOME STATEMENT ===
Revenue: ${revenue:,.0f} (+{rev_growth}% YoY)
COGS: ${cogs:,.0f} ({cogs_pct}%)
Gross Profit: ${gross_profit:,.0f} ({gross_margin}%)

Operating Expenses:
  R&D: ${rd_expense:,.0f} ({rd_pct}%)
  Sales & Marketing: ${sm_expense:,.0f} ({sm_pct}%)
  G&A: ${ga_expense:,.0f} ({ga_pct}%)
Total OpEx: ${total_opex:,.0f} ({opex_pct}%)

Operating Income: ${operating_income:,.0f} ({op_margin}%)
Net Income: ${net_income:,.0f} ({net_margin}%)

=== BALANCE SHEET HIGHLIGHTS ===
Cash & Equivalents: ${cash:,.0f}
Accounts Receivable: ${ar:,.0f} (DSO: {dso} days)
Total Assets: ${total_assets:,.0f}
Total Liabilities: ${total_liabilities:,.0f}
Equity: ${equity:,.0f}

=== KEY METRICS ===
ARR: ${arr:,.0f} (+{arr_growth}% YoY)
NRR: {nrr}%
Burn Rate: ${burn_rate:,.0f}/month
Runway: {runway_months} months

=== PAYMENT DATA ===
Cards Processed: {card_count:,}
Volume: ${card_volume:,.0f}
Chargebacks: {chargeback_count} ({chargeback_rate}%)
Refunds: {refund_count} ({refund_rate}%)

Bank Accounts:
Primary Operating: {iban_primary}
Reserve: {iban_reserve}
Payroll: {iban_payroll}""",
    
    """Payroll Register - {pay_period} - CONFIDENTIAL

Entity: {entity_name} | EIN: {ein}
Processed by: {payroll_processor} | Date: {process_date}
Classification: CONFIDENTIAL - HR & Finance Only

Summary:
Employees Paid: {employee_count}
Gross Wages: ${gross_wages:,.2f}
Employer Taxes: ${employer_taxes:,.2f}
Benefits Cost: ${benefits_cost:,.2f}
Net Pay: ${net_pay:,.2f}
Total Cost: ${total_cost:,.2f}

Top 5 Earners:
1. {top1_name} - ${top1_gross:,.2f} ({top1_role})
2. {top2_name} - ${top2_gross:,.2f} ({top2_role})
3. {top3_name} - ${top3_gross:,.2f} ({top3_role})
4. {top4_name} - ${top4_gross:,.2f} ({top4_role})
5. {top5_name} - ${top5_gross:,.2f} ({top5_role})

Tax Deposits:
Federal: ${fed_tax:,.2f} (Due: {fed_due})
State: ${state_tax:,.2f} (Due: {state_due})
Local: ${local_tax:,.2f} (Due: {local_due})

Benefits Deductions:
401(k): ${k401:,.2f} | Health: ${health:,.2f} | HSA: ${hsa:,.2f}

Bank: {bank_name} | Account: {payroll_account} | Routing: {payroll_routing}""",
    
    """Vendor Contract - {vendor_contract_id}

Vendor: {vendor_name} ({vendor_tax_id})
Address: {vendor_address}
Contact: {vendor_contact} ({vendor_email})
Classification: CONFIDENTIAL

Services: {services_description}
Term: {contract_start} to {contract_end}
Auto-renewal: {auto_renewal}

Pricing:
{pricing_details}
Payment Terms: {payment_terms}

SLAs:
- Availability: {availability_sla}%
- Response Time: {response_time_sla}
- Resolution Time: {resolution_time_sla}

Data Handling:
Data Categories: {data_categories}
Processing Location: {processing_location}
Subprocessors: {subprocessors_list}
Security Certifications: {certifications}

Termination:
Notice Period: {notice_period} days
Transition Assistance: {transition_days} days
Data Return: {data_return_days} days

Signatures:
Company: _________________________ Date: __________
Vendor: _________________________ Date: __________""",
]

# Highly Confidential - API keys, secrets, private keys
HIGHLY_CONFIDENTIAL_TEMPLATES = [
    # Short documents (existing)
    "AWS credentials: AKIA{key} secret={secret}. HIGHLY CONFIDENTIAL",
    "Database config: password={pwd} api_key={key}. HIGHLY CONFIDENTIAL",
    "SSH private key: -----BEGIN PRIVATE KEY-----\n{key}\n-----END PRIVATE KEY-----. HIGHLY CONFIDENTIAL",
    "API token: Bearer {token}. DO NOT SHARE. HIGHLY CONFIDENTIAL",
    "Kubernetes secret: api-key={key} secret={secret}. HIGHLY CONFIDENTIAL",
    "Docker registry: username={user} password={pwd}. HIGHLY CONFIDENTIAL",
    "JWT signing key: {key}. Keep secure. HIGHLY CONFIDENTIAL",
    "Encryption key: {key} for {system}. HIGHLY CONFIDENTIAL",
    "Service account: {email} key={key}. HIGHLY CONFIDENTIAL",
    "Webhook secret: {secret} for {endpoint}. HIGHLY CONFIDENTIAL",
    # Multi-paragraph documents (new)
    """Production Deployment Runbook - {deployment_id}

Date: {date}
Environment: PRODUCTION
Classification: HIGHLY CONFIDENTIAL

Pre-deployment Checklist:
- [ ] All tests passing in staging
- [ ] Security scan clean
- [ ] Database migration reviewed
- [ ] Rollback plan documented
- [ ] On-call engineer confirmed: {oncall_name} ({oncall_phone})

Secrets Required:
AWS Access Key: AKIA{aws_key}
AWS Secret Key: {aws_secret}
Database Password: {db_password}
API Keys: {api_keys}
JWT Signing Key: {jwt_key}
Encryption Keys: {deployment_encryption_keys}

Deployment Steps:
1. Create pre-deployment snapshot
2. Apply database migrations
3. Deploy application containers
4. Run smoke tests
5. Update DNS records
6. Monitor error rates for 30 minutes

Rollback Procedure:
1. Revert DNS
2. Restore database snapshot
3. Redeploy previous container version
4. Notify stakeholders

Emergency Contacts:
Security: {security_email}
Infrastructure: {infra_email}
Management: {mgmt_email}""",
    """Incident Response Playbook - {incident_id}

Severity: SEV-{severity}
Detected: {detection_time}
Classification: HIGHLY CONFIDENTIAL

Incident Summary:
{incident_summary}

Affected Systems:
{affected_systems}

Root Cause Analysis:
{root_cause}

Compromised Credentials (ROTATE IMMEDIATELY):
- AWS Keys: AKIA{compromised_aws_key} / {compromised_aws_secret}
- Database: {compromised_db_user} / {compromised_db_password}
- API Tokens: {compromised_api_tokens}
- SSH Keys: {compromised_ssh_keys}

Containment Actions Taken:
{containment_actions}

Eradication Steps:
1. Rotate all compromised credentials
2. Patch vulnerable systems
3. Remove unauthorized access
4. Verify integrity of all systems

Recovery Plan:
{recovery_plan}

Lessons Learned:
{lessons_learned}

Report Prepared by: {responder_name} ({responder_email})
Approved by: {approver_name} ({approver_email})""",
    """Infrastructure Configuration - {config_id}

Environment: {environment}
Last Updated: {date}
Classification: HIGHLY CONFIDENTIAL

Database Clusters:
Primary: {primary_db_host}:{primary_db_port}
  Credentials: {primary_db_user} / {primary_db_password}
  Connection String: {primary_connection_string}
Replica: {replica_db_host}:{replica_db_port}
  Credentials: {replica_db_user} / {replica_db_password}

Message Queues:
RabbitMQ: {rabbitmq_host}
  Credentials: {rabbitmq_user} / {rabbitmq_password}
Kafka: {kafka_brokers}
  SASL Credentials: {kafka_user} / {kafka_password}

Cache Layer:
Redis: {redis_host}:{redis_port}
  Password: {redis_password}
  Cluster Mode: {redis_cluster}

Secrets Management:
Vault Address: {vault_addr}
Vault Token: {vault_token}
Key Paths: {vault_key_paths}

Monitoring:
Prometheus: {prometheus_url}
Grafana: {grafana_url}
  Admin: {grafana_admin} / {grafana_password}
Alertmanager: {alertmanager_url}""",
    """Cryptographic Key Ceremony - {ceremony_id}

Date: {date}
Participants: {participants}
Classification: HIGHLY CONFIDENTIAL

Purpose:
Generate and distribute {key_type} keys for {system_name}.

Key Generation:
Algorithm: {algorithm}
Key Size: {key_size} bits
Entropy Source: {entropy_source}

Generated Keys:
Root CA: {root_ca_key}
Intermediate CA: {intermediate_ca_key}
Leaf Certificates: {leaf_certificates}
Encryption Keys: {ceremony_encryption_keys}
Signing Keys: {signing_keys}

Distribution:
{distribution_plan}

Backup and Escrow:
Offline backup: {offline_backup_location}
Escrow agent: {escrow_agent}
Escrow conditions: {escrow_conditions}

Revocation Procedure:
{revocation_procedure}

Attestation:
All participants confirm secure generation and distribution.
Signatures: {signatures}""",
]


# Mixed-sensitivity documents - primarily one level but containing higher sensitivity info
# These test the "highest-sensitivity-wins" classification policy
MIXED_SENSITIVITY_TEMPLATES = [
    # Mostly Internal but contains credentials (should be Highly Confidential)
    """Internal Team Update - {project_name}

Team: {team_name}
Date: {date}
Classification: INTERNAL

Sprint Summary:
Completed {completed_tickets} tickets this sprint. Velocity: {velocity} points.

Upcoming:
- {upcoming_feature_1}
- {upcoming_feature_2}
- {upcoming_feature_3}

Action Items:
{action_items}

Note: For database access, use credentials:
Host: {db_host}
User: {db_user}
Password: {db_password}  <-- HIGHLY CONFIDENTIAL

API Key for external service: {api_key}  <-- HIGHLY CONFIDENTIAL
""",
    """Onboarding Document - {employee_name}

Welcome to the team! This document contains internal information for your onboarding.
Classification: INTERNAL

Team Contacts:
- Manager: {manager_name} ({manager_email})
- Buddy: {buddy_name} ({buddy_email})
- HR: {hr_name} ({hr_email})

Systems Access:
You'll need access to the following systems:
- Jira: {jira_url}
- GitLab: {gitlab_url}
- Confluence: {confluence_url}
- VPN: {vpn_config}

IMPORTANT - Production Database Credentials (HIGHLY CONFIDENTIAL):
Host: {prod_db_host}
Port: {prod_db_port}
Username: {prod_db_user}
Password: {prod_db_password}

AWS Credentials (HIGHLY CONFIDENTIAL):
Access Key: AKIA{aws_key}
Secret Key: {aws_secret}

Please store these securely and never commit to version control.
""",
    # Mostly Confidential but contains API keys (should be Highly Confidential)
    """Client Project Proposal - {project_name}

Client: {client_name}
Date: {date}
Classification: CONFIDENTIAL

Project Overview:
{project_overview}

Scope and Deliverables:
{scope_deliverables}

Timeline: {timeline}
Budget: ${budget:,.2f}

Payment Information:
Wire transfer to IBAN: {iban}
Reference: {payment_ref}

Technical Integration:
The client's API requires the following credentials (HIGHLY CONFIDENTIAL):
API Endpoint: {api_endpoint}
API Key: {client_api_key}
Webhook Secret: {webhook_secret}

These credentials must be stored in the secure vault and rotated quarterly.
""",
    # Internal memo with accidentally included credentials
    """Internal Security Review Notes - {review_id}

Date: {date}
Reviewer: {reviewer_name} ({reviewer_email})
Classification: INTERNAL

Review Summary:
Completed security review of {system_name}. Overall posture: {posture}.

Findings:
1. {finding_1} - Severity: {severity_1}
2. {finding_2} - Severity: {severity_2}
3. {finding_3} - Severity: {severity_3}

Credentials Found in Code Review (HIGHLY CONFIDENTIAL - MUST ROTATE):
- AWS Key: AKIA{found_aws_key}
- GitHub Token: ghp_{found_github_token}
- Database Password: {found_db_password}

Remediation:
1. Immediately rotate all exposed credentials
2. Add pre-commit hooks to prevent future leaks
3. Schedule follow-up scan in 30 days

Approved by: {approver_name} ({approver_email})
""",
]


# Mixed-sensitivity documents - primarily one level but containing higher sensitivity info
# These test the "highest-sensitivity-wins" classification policy
MIXED_SENSITIVITY_TEMPLATES = [
    # Mostly Internal but contains credentials (should be Highly Confidential)
    """Internal Team Update - {project_name}

Team: {team_name}
Date: {date}
Classification: INTERNAL

Sprint Summary:
Completed {completed_tickets} tickets this sprint. Velocity: {velocity} points.

Upcoming:
- {upcoming_feature_1}
- {upcoming_feature_2}
- {upcoming_feature_3}

Action Items:
{action_items}

Note: For database access, use credentials:
Host: {db_host}
User: {db_user}
Password: {db_password}  <-- HIGHLY CONFIDENTIAL

API Key for external service: {api_key}  <-- HIGHLY CONFIDENTIAL
""",
    """Onboarding Document - {employee_name}

Welcome to the team! This document contains internal information for your onboarding.
Classification: INTERNAL

Team Contacts:
- Manager: {manager_name} ({manager_email})
- Buddy: {buddy_name} ({buddy_email})
- HR: {hr_name} ({hr_email})

Systems Access:
You'll need access to the following systems:
- Jira: {jira_url}
- GitLab: {gitlab_url}
- Confluence: {confluence_url}
- VPN: {vpn_config}

IMPORTANT - Production Database Credentials (HIGHLY CONFIDENTIAL):
Host: {prod_db_host}
Port: {prod_db_port}
Username: {prod_db_user}
Password: {prod_db_password}

AWS Credentials (HIGHLY CONFIDENTIAL):
Access Key: AKIA{aws_key}
Secret Key: {aws_secret}

Please store these securely and never commit to version control.
""",
    # Mostly Confidential but contains API keys (should be Highly Confidential)
    """Client Project Proposal - {project_name}

Client: {client_name}
Date: {date}
Classification: CONFIDENTIAL

Project Overview:
{project_overview}

Scope and Deliverables:
{scope_deliverables}

Timeline: {timeline}
Budget: ${budget:,.2f}

Payment Information:
Wire transfer to IBAN: {iban}
Reference: {payment_ref}

Technical Integration:
The client's API requires the following credentials (HIGHLY CONFIDENTIAL):
API Endpoint: {api_endpoint}
API Key: {client_api_key}
Webhook Secret: {webhook_secret}

These credentials must be stored in the secure vault and rotated quarterly.
""",
    # Public tutorial mentioning passwords (should remain Public or be Internal)
    """Public Tutorial: {topic}

In this tutorial, we'll learn how to {objective}.

Prerequisites:
- {prereq_1}
- {prereq_2}

Step 1: Configuration
Create a config file with your settings:
    # config.yaml
    database:
      host: localhost
      port: 5432
      # WARNING: Never hardcode passwords in config files!
      # Use environment variables instead:
      # password: ${{DB_PASSWORD}}
      username: tutorial_user

Step 2: Running the Application
Start the server:
    python app.py

Common Example (DO NOT USE IN PRODUCTION):
    # Bad example - hardcoded password
    password = "example_password_123"
    
    # Good example - from environment
    import os
    password = os.environ.get("DB_PASSWORD")

Security Best Practices:
- Never commit passwords or API keys to version control
- Use a secrets manager in production
- Rotate credentials regularly
- Use least-privilege access

Next Steps:
Explore the advanced features in our documentation.
""",
    # Internal memo with accidentally included credentials
    """Internal Security Review Notes - {review_id}

Date: {date}
Reviewer: {reviewer_name} ({reviewer_email})
Classification: INTERNAL

Review Summary:
Completed security review of {system_name}. Overall posture: {posture}.

Findings:
1. {finding_1} - Severity: {severity_1}
2. {finding_2} - Severity: {severity_2}
3. {finding_3} - Severity: {severity_3}

Credentials Found in Code Review (HIGHLY CONFIDENTIAL - MUST ROTATE):
- AWS Key: AKIA{found_aws_key}
- GitHub Token: ghp_{found_github_token}
- Database Password: {found_db_password}

Remediation:
1. Immediately rotate all exposed credentials
2. Add pre-commit hooks to prevent future leaks
3. Schedule follow-up scan in 30 days

Approved by: {approver_name} ({approver_email})
""",
]


# =============================================================================
# Synthetic Value Generators
# =============================================================================

def gen_email() -> str:
    domains = ["example.com", "company.org", "test.net", "demo.io", "sample.co"]
    name = "".join(random.choices(string.ascii_lowercase, k=random.randint(5, 10)))
    return f"{name}@{random.choice(domains)}"


def gen_phone() -> str:
    formats = [
        lambda: f"+{random.randint(1, 99)} {random.randint(100, 999)} {random.randint(100, 999)} {random.randint(1000, 9999)}",
        lambda: f"({random.randint(100, 999)}) {random.randint(100, 999)}-{random.randint(1000, 9999)}",
        lambda: f"{random.randint(100, 999)}-{random.randint(100, 999)}-{random.randint(1000, 9999)}",
    ]
    return random.choice(formats)()


def gen_payment_card() -> str:
    prefix = "4"
    body = "".join(random.choices(string.digits, k=14))
    partial = prefix + body
    
    def luhn_checksum(num):
        digits = [int(d) for d in num]
        odd = digits[-1::-2]
        even = digits[-2::-2]
        total = sum(odd)
        for d in even:
            total += sum(divmod(d * 2, 10))
        return (10 - (total % 10)) % 10
    check = luhn_checksum(partial + "0")
    return partial + str(check)


def gen_iban() -> str:
    country = "DE"
    check = f"{random.randint(10, 99)}"
    bban = "".join(random.choices(string.digits + string.ascii_uppercase, k=20))
    return f"{country}{check} {bban[:4]} {bban[4:8]} {bban[8:12]} {bban[12:16]} {bban[16:20]}"


def gen_national_id() -> str:
    return "".join(random.choices(string.digits, k=8))


def gen_passport() -> str:
    letter = random.choice(string.ascii_uppercase)
    digits = "".join(random.choices(string.digits, k=7))
    return f"{letter}{digits}"


def gen_aws_key() -> str:
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=16))


def gen_secret() -> str:
    return "".join(random.choices(string.ascii_letters + string.digits + "!@#$%", k=32))


def gen_private_key_fragment() -> str:
    return "\n".join("".join(random.choices(string.ascii_letters + string.digits + "+/=", k=64)) for _ in range(4))


def gen_api_token() -> str:
    return "".join(random.choices(string.ascii_letters + string.digits, k=48))


def gen_jwt_key() -> str:
    return "".join(random.choices(string.ascii_letters + string.digits, k=64))


def gen_encryption_key() -> str:
    return "".join(random.choices(string.ascii_letters + string.digits, k=32))


def gen_webhook_secret() -> str:
    return "".join(random.choices(string.ascii_letters + string.digits, k=40))


# =============================================================================
# Document Generation
# =============================================================================

@dataclass
class SyntheticDocument:
    text: str
    label: str
    metadata: dict


def gen_public() -> SyntheticDocument:
    template = random.choice(PUBLIC_TEMPLATES)
    text = template.format(
        # Common
        date=f"2026-{random.randint(1, 12):02d}-{random.randint(1, 28):02d}",
        # Meeting/agenda templates
        attendees=", ".join(random.sample(["John Smith", "Jane Doe", "Bob Johnson", "Alice Williams", "Mike Brown", "Sarah Davis", "Chris Wilson", "Lisa Anderson"], k=random.randint(3, 6))),
        action_owner_1=random.choice(["John Smith", "Jane Doe", "Bob Johnson", "Alice Williams"]),
        action_date_1=f"2026-{random.randint(1, 12):02d}-{random.randint(1, 28):02d}",
        action_owner_2=random.choice(["Mike Brown", "Sarah Davis", "Chris Wilson"]),
        action_date_2=f"2026-{random.randint(1, 12):02d}-{random.randint(1, 28):02d}",
        action_owner_3=random.choice(["John Smith", "Jane Doe", "Bob Johnson"]),
        project_name=random.choice(["Atlas", "Orion", "Phoenix", "Nexus", "Vanguard", "Horizon", "Apex"]),
        # All-hands / metrics templates
        quarter=random.randint(1, 4),
        year=2026,
        revenue=random.randint(1000000, 100000000),
        growth=random.randint(5, 60),
        headcount=random.randint(50, 2000),
        new_hires=random.randint(5, 100),
        nps=random.randint(30, 80),
        deploy_freq=random.randint(10, 100),
        p95_ms=random.randint(50, 500),
        p95_prev=random.randint(100, 800),
        incidents=random.randint(0, 10),
        promotions=random.randint(1, 20),
        learning_budget=random.randint(50000, 500000),
        hackathon_winners=random.choice(["Team Alpha", "Team Beta", "Team Gamma", "Innovation Squad"]),
        # Tutorial templates
        technology=random.choice(["Docker", "Kubernetes", "Terraform", "Ansible", "Prometheus", "Grafana", "Kafka", "Redis", "PostgreSQL", "React", "Vue", "TypeScript", "Go", "Rust", "Python"]),
        concept=random.choice(["container orchestration", "infrastructure as code", "observability", "CI/CD", "microservices", "event-driven architecture"]),
        prereq_1=random.choice(["Python 3.8+", "Node.js 16+", "Go 1.18+", "Docker installed", "Kubernetes cluster", "Cloud account"]),
        prereq_2=random.choice(["Git configured", "Cloud account", "IDE setup", "Basic CLI knowledge", "YAML familiarity"]),
        package_name=random.choice(["awesome-lib", "super-tool", "mega-framework", "data-processor", "api-client", "config-manager"]),
        module_name=random.choice(["awesome_lib", "super_tool", "mega_framework", "data_processor", "api_client", "config_manager"]),
        CONFIG_PREFIX=random.choice(["APP", "MYAPP", "PROJECT", "SERVICE", "PLATFORM"]),
        # Blog/article templates
        title=random.choice(["How We Scaled to 1M Users", "Lessons from Our Migration to Kubernetes", "Building a Type-Safe API Layer", "Database Sharding Strategies", "Observability at Scale", "Securing Microservices", "CI/CD Pipeline Best Practices", "From Monolith to Microservices"]),
        author=random.choice(["Sarah Chen", "Marcus Johnson", "Priya Patel", "Alex Rodriguez", "Emma Thompson", "David Kim", "Lisa Wang", "James Okafor"]),
        read_time=random.randint(5, 15),
        intro_paragraph=random.choice(["When we started this journey...", "Last quarter, our team faced...", "After months of planning...", "The challenge was clear:...", "We've all been there:..."]),
        main_paragraph_1=random.choice(["First, we identified the bottlenecks...", "The key insight came from...", "Our approach was unconventional...", "We started by measuring..."]),
        main_paragraph_2=random.choice(["The results exceeded expectations...", "Surprisingly, the simplest solution...", "Team adoption was faster than...", "Edge cases taught us..."]),
        takeaway_1=random.choice(["Measure before optimizing", "Invest in developer experience", "Automate the boring stuff", "Design for failure"]),
        takeaway_2=random.choice(["Simplicity scales, complexity fails", "Documentation is a feature", "Feedback loops drive improvement"]),
        takeaway_3=random.choice(["Culture eats strategy for breakfast", "Technical debt is a choice", "Your team is your greatest asset"]),
        conclusion=random.choice(["We're hiring! Check out our careers page.", "Try it yourself and let us know.", "The full code is on GitHub.", "Stay tuned for part 2."]),
        tags=random.choice(["engineering, scaling, kubernetes", "api, typescript, architecture", "security, microservices, observability", "database, performance, sharding"]),
        # Policy/announcement templates
        policy_name=random.choice(["Remote Work Policy", "Security Training Requirements", "Expense Reimbursement", "Code Review Standards", "Incident Response Procedures", "Data Retention Policy"]),
        effective_date=f"2026-{random.randint(1, 12):02d}-01",
        policy_summary=random.choice(["Updated guidelines for...", "New requirements for...", "Clarification on...", "Streamlined process for..."]),
        changes_list=random.choice(["- Change 1\n- Change 2\n- Change 3", "- Updated thresholds\n- New approval flow\n- Simplified documentation"]),
        action_items=random.choice(["- Review by Friday\n- Acknowledge in HR system", "- Attend training session\n- Update local config", "- No action required\n- For awareness only"]),
        contact_team=random.choice(["PeopleOps", "Security", "Finance", "Engineering", "Legal"]),
        contact_email=random.choice(["peopleops@company.com", "security@company.com", "finance@company.com", "eng@company.com", "legal@company.com"]),
        sender=random.choice(["PeopleOps Team", "Security Team", "Engineering Leadership", "Executive Team"]),
        # Engineering blog templates
        company_name=random.choice(["TechCorp", "DataFlow", "CloudScale", "APIHub", "DevTools Inc", "SecureNet", "PayFlow", "StreamLine"]),
        achievement=random.choice(["Reduced Latency by 80%", "Scaled to 1M Requests/sec", "Achieved Zero Downtime Deploys", "Cut Cloud Costs by 40%", "Improved Developer Velocity"]),
        background_context=random.choice(["As our user base grew...", "Our legacy architecture...", "The previous system..."]),
        challenge_description=random.choice(["Handling traffic spikes...", "Maintaining consistency...", "Debugging distributed systems..."]),
        approach_details=random.choice(["We implemented a new caching layer...", "We adopted event sourcing...", "We migrated to a service mesh..."]),
        metric_1=random.choice(["P99 latency", "Error rate", "Deploy frequency", "MTTR"]),
        value_1=random.choice(["< 50ms", "< 0.1%", "50+/day", "< 5 min"]),
        metric_2=random.choice(["Developer satisfaction", "Incident count", "On-call burden"]),
        value_2=random.choice(["+40%", "-60%", "-80%"]),
        metric_3=random.choice(["Cloud costs", "Build time", "Test coverage"]),
        value_3=random.choice(["-40%", "-50%", "+25%"]),
        lessons_learned=random.choice(["Start with metrics", "Involve the team early", "Automate everything", "Plan for rollback"]),
        next_steps=random.choice(["Expand to other services", "Open source the tooling", "Write a follow-up post"]),
        role=random.choice(["Staff Engineer", "Engineering Manager", "Principal Engineer", "Tech Lead"]),
        # Release notes templates
        product_name=random.choice(["API Gateway", "Analytics Platform", "Auth Service", "Payment Gateway", "Notification Service", "Search Engine"]),
        version=f"{random.randint(1, 5)}.{random.randint(0, 9)}.{random.randint(0, 9)}",
        release_date=f"2026-{random.randint(1, 12):02d}-{random.randint(1, 28):02d}",
        new_features=random.choice(["- Feature A\n- Feature B\n- Feature C", "- New dashboard\n- Enhanced API\n- Improved performance"]),
        bug_fixes=random.choice(["- Fixed memory leak\n- Resolved race condition\n- Corrected edge case", "- Patch for CVE-2026-XXXXX\n- Fixed timeout issue"]),
        improvements=random.choice(["- Better error messages\n- Faster startup\n- Reduced memory usage", "- Enhanced logging\n- Improved validation"]),
        breaking_changes=random.choice(["- Removed deprecated v1 API\n- Changed config format", "- Updated authentication flow", "- None"]),
        updated_deps=random.choice(["React 18.2, TypeScript 5.1", "Kubernetes 1.28, Go 1.21", "PostgreSQL 16, Redis 7.2"]),
        added_deps=random.choice(["OpenTelemetry SDK", "New caching library", "None"]),
        changelog_url="https://github.com/example/project/blob/main/CHANGELOG.md",
        upgrade_guide_url="https://docs.example.com/upgrade-guide",
    )
    return SyntheticDocument(text=text, label="Public", metadata={})


def gen_internal() -> SyntheticDocument:
    template = random.choice(INTERNAL_TEMPLATES)
    name = f"{random.choice(['John', 'Jane', 'Bob', 'Alice', 'Mike', 'Sarah', 'Chris', 'Lisa', 'David', 'Emma'])} {random.choice(['Smith', 'Doe', 'Johnson', 'Williams', 'Brown', 'Davis', 'Wilson', 'Anderson', 'Taylor', 'Thomas'])}"
    text = template.format(
        name=name,
        email=gen_email(),
        phone=gen_phone(),
        date=f"2026-{random.randint(1, 12):02d}-{random.randint(1, 28):02d}",
        role=random.choice(["Engineer", "Manager", "Analyst", "Designer", "Lead", "Architect", "Principal"]),
        system=random.choice(["Jira", "GitLab", "Confluence", "Slack", "VPN", "CI/CD", "Datadog", "PagerDuty"]),
        keyword=random.choice(["confidential", "internal", "budget", "roadmap", "strategy", "restricted"]),
        topic=random.choice(["sprint planning", "architecture", "security", "deployment", "incident review", "design review"]),
        # HR & onboarding
        employee_name=name,
        team_name=random.choice(["Platform", "Backend", "Frontend", "Security", "Data", "ML", "DevOps", "QA"]),
        onboarding_team=random.choice(["Platform", "Backend", "Frontend", "Security", "Data", "ML", "DevOps", "QA"]),
        manager_name=f"{random.choice(['John', 'Jane', 'Bob', 'Alice'])} {random.choice(['Smith', 'Doe', 'Johnson'])}",
        manager_email=gen_email(),
        buddy_name=f"{random.choice(['Mike', 'Sarah', 'Chris', 'Lisa'])} {random.choice(['Brown', 'Davis', 'Wilson', 'Anderson'])}",
        buddy_email=gen_email(),
        hr_name=f"{random.choice(['Lisa', 'Tom', 'Maria'])} {random.choice(['Anderson', 'Taylor', 'Martinez'])}",
        hr_email=gen_email(),
        it_name=f"{random.choice(['Chris', 'Alex'])} {random.choice(['Wilson', 'Martinez'])}",
        it_email=gen_email(),
        security_name=f"{random.choice(['Sam', 'Jordan'])} {random.choice(['Lee', 'Chen'])}",
        security_email="security@company.internal",
        architect_name=f"{random.choice(['Alex', 'Sam'])} {random.choice(['Brown', 'Davis'])}",
        system_1=random.choice(["Jira", "GitLab", "Confluence"]),
        system_2=random.choice(["Slack", "VPN", "CI/CD", "Datadog"]),
        training_module=random.choice(["Security Awareness", "Code Review", "Deployment", "Incident Response"]),
        shadow_role=random.choice(["Senior Engineer", "Tech Lead", "Architect", "Staff Engineer"]),
        shadow_days=random.randint(3, 10),
        checkin_date=f"2026-{random.randint(1, 12):02d}-{random.randint(1, 28):02d}",
        review_date=f"2026-{random.randint(1, 12):02d}-{random.randint(1, 28):02d}",
        # Performance review
        level=random.choice(["L3", "L4", "L5", "L6", "L7"]),
        achievements=random.choice(["Delivered Project X on time", "Mentored 3 junior engineers", "Reduced latency by 40%", "Led migration to Kubernetes"]),
        strengths=random.choice(["Technical leadership", "Cross-team collaboration", "Code quality advocacy", "Mentoring"]),
        growth_areas=random.choice(["Public speaking", "Strategic planning", "Delegation", "Documentation"]),
        growth_areas=random.choice(["Public speaking", "Strategic planning", "Delegation", "Documentation"]),
        next_goals=random.choice(["Lead Project Y", "Get promoted to L6", "Present at conference", "Build new team"]),
        current_comp=random.randint(150000, 400000),
        market_comp=random.randint(160000, 450000),
        adjustment_pct=random.randint(-5, 20),
        # IT & Security
        advisory_id=f"SEC-{random.randint(2026001, 2026999)}",
        severity=random.choice(["CRITICAL", "HIGH", "MEDIUM", "LOW"]),
        status=random.choice(["Open", "In Progress", "Resolved", "Monitoring"]),
        affected_systems=random.choice(["Auth Service", "API Gateway", "Database", "Message Queue", "Cache Layer", "Load Balancer"]),
        summary=random.choice(["Vulnerability in dependency", "Misconfigured IAM role", "Exposed debug endpoint", "Weak encryption detected"]),
        technical_details=random.choice(["CVE-2026-XXXXX in library v1.2.3", "Security group allows 0.0.0.0/0", "Debug endpoint returns stack traces", "TLS 1.0 still enabled on legacy endpoint"]),
        impact_assessment=random.choice(["Potential data exposure", "Service disruption risk", "Compliance violation", "Low - internal only"]),
        action_1=random.choice(["Patch library to v1.2.4", "Restrict security group", "Disable debug endpoint", "Enable TLS 1.2+"]),
        owner_1=random.choice(["Platform Team", "Security Team", "Backend Team"]),
        due_1=f"2026-{random.randint(1, 12):02d}-{random.randint(1, 28):02d}",
        action_2=random.choice(["Rotate affected credentials", "Run vulnerability scan", "Update firewall rules", "Enable WAF"]),
        owner_2=random.choice(["Security Team", "Infra Team", "Backend Team"]),
        due_2=f"2026-{random.randint(1, 12):02d}-{random.randint(1, 28):02d}",
        action_3=random.choice(["Deploy WAF rules", "Monitor for anomalies", "Schedule follow-up scan", "Update runbook"]),
        owner_3=random.choice(["Platform Team", "Security Team"]),
        due_3=f"2026-{random.randint(1, 12):02d}-{random.randint(1, 28):02d}",
        workaround=random.choice(["Use alternative endpoint", "Disable feature temporarily", "Manual approval required", "Route via VPN"]),
        cve_year=2026,
        cve_id=random.randint(10000, 99999),
        ticket_id=f"SEC-{random.randint(1000, 9999)}",
        # Incident retrospective
        incident_id=f"{random.randint(1000, 9999)}",
        duration_min=random.randint(15, 480),
        timeline=random.choice(["T+0m: Alert fired\nT+5m: On-call acknowledged\nT+15m: Root cause identified\nT+45m: Fix deployed\nT+60m: All clear"]),
        root_cause=random.choice(["Database connection pool exhaustion", "Memory leak in new release", "Third-party API rate limit", "Configuration drift"]),
        users_affected=random.randint(100, 100000),
        revenue_impact=random.randint(1000, 100000),
        sla_breach=random.choice(["Yes - 99.9% availability", "No - within SLA", "Partial degradation"]),
        went_well=random.choice(["Fast detection via alerting", "Clear communication", "Rollback worked smoothly"]),
        went_wrong=random.choice(["Slow initial diagnosis", "Missing runbook", "Communication gaps"]),
        action_items=random.choice(["- Add connection pool monitoring\n- Improve runbook\n- Add integration test"]),
        followup_date=f"2026-{random.randint(1, 12):02d}-{random.randint(1, 28):02d}",
        # Project & Finance
        project_name=random.choice(["Atlas", "Orion", "Phoenix", "Nexus", "Vanguard", "Horizon", "Apex"]),
        author_name=name,
        author_email=gen_email(),
        sponsor_name=f"{random.choice(['Alice', 'Bob', 'Carol'])} {random.choice(['Smith', 'Jones'])}",
        sponsor_email=gen_email(),
        exec_summary=random.choice(["New payment processing service", "Migration to cloud-native architecture", "Real-time analytics platform", "Customer-facing API v2"]),
        problem_statement=random.choice(["Current system doesn't scale", "High operational overhead", "Vendor lock-in risk", "Technical debt slowing delivery"]),
        solution_description=random.choice(["Build new service with event-driven architecture", "Migrate to Kubernetes with GitOps", "Adopt serverless for variable workloads", "Implement CDC for real-time sync"]),
        eng_fte=random.randint(3, 15),
        eng_cost=random.randint(15000, 25000),
        design_fte=random.randint(1, 3),
        design_cost=random.randint(12000, 20000),
        pm_fte=random.randint(1, 2),
        pm_cost=random.randint(14000, 22000),
        infra_cost=random.randint(5000, 50000),
        total_cost=random.randint(500000, 5000000),
        duration_months=random.randint(6, 18),
        success_metrics=random.choice(["99.99% availability, <50ms p99", "Process 1M events/sec", "Reduce deployment time to <10min", "Zero-downtime deployments"]),
        risks_mitigations=random.choice(["Risk: Vendor dependency\nMit: Multi-cloud strategy\nRisk: Team bandwidth\nMit: Hire 2 contractors"]),
        approvers=random.choice(["VP Engineering, CTO", "Director, VP Engineering", "CTO, CFO"]),
        # Budget review
        department=random.choice(["Engineering", "Product", "Security", "Data", "Platform"]),
        quarter=random.randint(1, 4),
        allocated=random.randint(500000, 10000000),
        spent=random.randint(400000, 9000000),
        spent_pct=random.randint(60, 110),
        variance=random.randint(-1000000, 1000000),
        variance_pct=random.randint(-20, 20),
        expense_1=random.choice(["Personnel", "Cloud Infrastructure", "Software Licenses", "Contractors"]),
        amt_1=random.randint(100000, 5000000),
        expense_2=random.choice(["Personnel", "Cloud Infrastructure", "Software Licenses", "Contractors"]),
        amt_2=random.randint(50000, 2000000),
        expense_3=random.choice(["Personnel", "Cloud Infrastructure", "Software Licenses", "Contractors"]),
        amt_3=random.randint(25000, 1000000),
        forecast=random.choice(["Expect 10% increase due to hiring", "Stable with optimization", "Decrease after migration"]),
        decisions=random.choice(["Approve Q3 hiring plan", "Fund migration project", "Optimize cloud spend"]),
        # Team sync
        team_sync_name=random.choice(["Platform", "Backend", "Frontend", "Security", "Data", "ML", "DevOps", "QA"]),
        attendees=", ".join(random.sample(["John Smith", "Jane Doe", "Bob Johnson", "Alice Williams", "Mike Brown", "Sarah Davis", "Chris Wilson", "Lisa Anderson"], k=random.randint(4, 8))),
        updates=random.choice(["Sprint on track, 80% complete\nNew hire started Monday\nSecurity patch deployed"]),
        discussion_1=random.choice(["Technical debt in auth service", "Q3 planning timeline", "New hiring targets"]),
        discussion_2=random.choice(["Architecture review for Project X", "Incident response improvements", "Tool evaluation"]),
        discussion_3=random.choice(["On-call rotation changes", "Documentation standards", "CI/CD pipeline upgrades"]),
        decisions=random.choice(["Proceed with Option A\nSchedule follow-up for Option B"]),
        action_items=random.choice(["- John: Draft RFC by Friday\n- Jane: Schedule architecture review\n- Bob: Update runbook"]),
        parking_lot=random.choice(["Long-term: Microservices migration", "Future: Rust adoption"]),
        # Design review
        feature_name=random.choice(["Real-time Notifications", "Payment Processing v2", "Audit Logging", "Rate Limiting", "Feature Flags"]),
        reviewers=", ".join(random.sample(["John Smith", "Jane Doe", "Bob Johnson", "Alice Williams"], k=random.randint(2, 4))),
        context=random.choice(["Current system uses polling", "Legacy payment gateway deprecated", "No centralized audit trail", "Rate limiting at LB only"]),
        design_description=random.choice(["Event-driven with Kafka\nWebSocket for real-time\nIdempotent consumers", "New payment abstraction\nProvider-agnostic interface\nWebhook retry with backoff"]),
        alternatives=random.choice(["Polling with Redis\nSSE instead of WebSocket\nThird-party notification service"]),
        tradeoffs=random.choice(["Complexity vs real-time\nCost vs latency\nBuild vs buy"]),
        security_considerations=random.choice(["Encrypt PII in events\nValidate webhook signatures\nRate limit per tenant"]),
        testing_strategy=random.choice(["Unit: 80% coverage\nIntegration: contract tests\nLoad: 2x peak traffic\nChaos: dependency failure"]),
        rollout_plan=random.choice(["Canary 5% -> 25% -> 100%\nFeature flag per tenant\nRollback in <2min"]),
        open_questions=random.choice(["Event ordering guarantees?\nSchema evolution strategy?\nCross-region replication?"]),
    )
    return SyntheticDocument(text=text, label="Internal", metadata={})


def gen_confidential() -> SyntheticDocument:
    template = random.choice(CONFIDENTIAL_TEMPLATES)
    name = f"{random.choice(['John', 'Jane', 'Bob', 'Alice'])} {random.choice(['Smith', 'Doe'])}"
    text = template.format(
        # Short templates
        id=random.randint(10000, 99999),
        card=gen_payment_card(),
        iban=gen_iban(),
        national_id=gen_national_id(),
        passport=gen_passport(),
        amount=f"${random.randint(100, 10000):,.2f}",
        ref=f"REF{random.randint(10000, 99999)}",
        name=name,
        date=f"2026-{random.randint(1, 12):02d}-{random.randint(1, 28):02d}",
        # Legal contracts
        msa_id=f"MSA-{random.randint(2026001, 2026999)}",
        client_name=f"{random.choice(['Acme', 'Globex', 'Wayne', 'Stark', 'Umbrella', 'Apex', 'Nexus'])} {random.choice(['Corp', 'Inc', 'LLC', 'Ltd', 'Group'])}",
        vendor_name=f"{random.choice(['DataFlow', 'CloudScale', 'SecureNet', 'PayTech', 'APIHub'])} {random.choice(['Inc', 'LLC', 'Corp'])}",
        effective_date=f"2026-{random.randint(1, 12):02d}-01",
        service_description=random.choice(["Payment processing", "Data analytics", "Security auditing", "Cloud migration", "API development"]),
        total_value=random.randint(100000, 10000000),
        payment_terms=random.choice(["Net 30", "Net 45", "Monthly", "Quarterly", "Milestone-based"]),
        invoicing_schedule=random.choice(["Monthly in arrears", "Quarterly in advance", "Per milestone", "Per usage"]),
        bank_name=random.choice(["Chase", "Wells Fargo", "Bank of America", "Citi", "SVB"]),
        account_number=f"{random.randint(1000000000, 9999999999)}",
        routing_number=f"{random.randint(100000000, 999999999)}",
        swift_code=random.choice(["CHASUS33", "WFBIUS6S", "BOFAUS3N", "CITIUS33", "SVBKUS6S"]),
        term_months=random.randint(12, 60),
        # NDA
        nda_id=f"NDA-{random.randint(2026001, 2026999)}",
        party_a=f"{random.choice(['Acme', 'Globex', 'Wayne'])} Corp",
        party_b=f"{random.choice(['DataFlow', 'CloudScale', 'SecureNet'])} Inc",
        purpose=random.choice(["Technical evaluation", "Partnership discussion", "Acquisition due diligence", "Vendor assessment"]),
        term_years=random.randint(2, 5),
        survival_years=random.randint(3, 7),
        governing_law=random.choice(["Delaware", "California", "New York", "England & Wales"]),
        jurisdiction=random.choice(["Delaware Chancery Court", "SF Superior Court", "NY Commercial Division", "London High Court"]),
        # Financial reports
        entity_name=random.choice(["TechCorp Inc", "DataFlow Ltd", "SecureNet Group", "PayTech Solutions"]),
        quarter=random.randint(1, 4),
        year=2026,
        preparer_name=f"{random.choice(['John', 'Jane', 'Bob', 'Alice'])} {random.choice(['Smith', 'Doe', 'Johnson', 'Williams'])}",
        revenue=random.randint(10000000, 1000000000),
        rev_growth=random.randint(-10, 50),
        cogs=random.randint(2000000, 300000000),
        cogs_pct=random.randint(20, 40),
        gross_profit=random.randint(8000000, 700000000),
        gross_margin=random.randint(50, 85),
        rd_expense=random.randint(1000000, 100000000),
        rd_pct=random.randint(10, 25),
        sm_expense=random.randint(2000000, 150000000),
        sm_pct=random.randint(15, 30),
        ga_expense=random.randint(1000000, 50000000),
        ga_pct=random.randint(8, 15),
        total_opex=random.randint(5000000, 250000000),
        opex_pct=random.randint(40, 65),
        operating_income=random.randint(1000000, 500000000),
        op_margin=random.randint(10, 40),
        net_income=random.randint(500000, 400000000),
        net_margin=random.randint(5, 30),
        cash=random.randint(10000000, 500000000),
        ar=random.randint(5000000, 200000000),
        dso=random.randint(30, 90),
        total_assets=random.randint(50000000, 2000000000),
        total_liabilities=random.randint(10000000, 800000000),
        equity=random.randint(20000000, 1500000000),
        arr=random.randint(10000000, 500000000),
        arr_growth=random.randint(10, 60),
        nrr=random.randint(95, 130),
        burn_rate=random.randint(100000, 5000000),
        runway_months=random.randint(6, 36),
        card_count=random.randint(10000, 10000000),
        card_volume=random.randint(100000000, 10000000000),
        chargeback_count=random.randint(10, 10000),
        chargeback_rate=random.randint(0, 2),
        refund_count=random.randint(100, 10000),
        refund_rate=random.randint(0, 1),
        iban_primary=gen_iban(),
        iban_reserve=gen_iban(),
        iban_payroll=gen_iban(),
        # Payroll
        pay_period=random.choice(["2026-01", "2026-02", "2026-03", "2026-04", "2026-05", "2026-06", "2026-07", "2026-08", "2026-09", "2026-10", "2026-11", "2026-12"]),
        entity_name=random.choice(["TechCorp Inc", "DataFlow Ltd", "SecureNet Group"]),
        ein=f"{random.randint(10, 99)}-{random.randint(1000000, 9999999)}",
        payroll_processor=random.choice(["ADP", "Gusto", "Rippling", "Paylocity", "Workday"]),
        process_date=f"2026-{random.randint(1, 12):02d}-{random.randint(1, 28):02d}",
        employee_count=random.randint(50, 2000),
        gross_wages=random.randint(5000000, 200000000),
        employer_taxes=random.randint(500000, 20000000),
        benefits_cost=random.randint(1000000, 40000000),
        net_pay=random.randint(4000000, 150000000),
        total_cost=random.randint(6000000, 250000000),
        top1_name=f"{random.choice(['Alice', 'Bob', 'Carol'])} {random.choice(['Smith', 'Johnson'])}",
        top1_gross=random.randint(300000, 800000),
        top1_role=random.choice(["CTO", "VP Engineering", "Chief Architect"]),
        top2_name=f"{random.choice(['David', 'Eve', 'Frank'])} {random.choice(['Jones', 'Brown'])}",
        top2_gross=random.randint(250000, 500000),
        top2_role=random.choice(["Director", "Principal Engineer", "Engineering Manager"]),
        top3_name=f"{random.choice(['Grace', 'Henry', 'Iris'])} {random.choice(['Williams', 'Davis'])}",
        top3_gross=random.randint(200000, 400000),
        top3_role=random.choice(["Staff Engineer", "Tech Lead", "Security Lead"]),
        top4_name=f"{random.choice(['Jack', 'Karen', 'Leo'])} {random.choice(['Miller', 'Wilson'])}",
        top4_gross=random.randint(180000, 350000),
        top4_role=random.choice(["Senior Engineer", "Security Engineer", "Data Engineer"]),
        top5_name=f"{random.choice(['Mia', 'Nathan', 'Olivia'])} {random.choice(['Taylor', 'Anderson'])}",
        top5_gross=random.randint(160000, 300000),
        top5_role=random.choice(["Senior Engineer", "DevOps Engineer", "ML Engineer"]),
        fed_tax=random.randint(1000000, 50000000),
        fed_due=f"2026-{random.randint(1, 12):02d}-15",
        state_tax=random.randint(100000, 10000000),
        state_due=f"2026-{random.randint(1, 12):02d}-15",
        local_tax=random.randint(10000, 2000000),
        local_due=f"2026-{random.randint(1, 12):02d}-15",
        k401=random.randint(500000, 20000000),
        health=random.randint(1000000, 30000000),
        hsa=random.randint(50000, 2000000),
        bank_name=random.choice(["Chase", "Wells Fargo", "Bank of America", "Citi"]),
        payroll_account=f"{random.randint(1000000000, 9999999999)}",
        payroll_routing=f"{random.randint(100000000, 999999999)}",
        # Vendor contract
        vendor_contract_id=f"VC-{random.randint(2026001, 2026999)}",
        vendor_name=f"{random.choice(['DataFlow', 'CloudScale', 'SecureNet', 'PayTech', 'APIHub'])} {random.choice(['Inc', 'LLC', 'Corp'])}",
        vendor_tax_id=f"{random.randint(10, 99)}-{random.randint(1000000, 9999999)}",
        vendor_address=f"{random.randint(100, 9999)} {random.choice(['Main', 'Market', 'Mission', 'Howard', 'Folsom'])} St, {random.choice(['San Francisco', 'New York', 'Seattle', 'Austin', 'Boston'])} {random.choice(['CA', 'NY', 'WA', 'TX', 'MA'])} {random.randint(10000, 99999)}",
        vendor_contact=f"{random.choice(['Alex', 'Sam', 'Jordan'])} {random.choice(['Chen', 'Lee', 'Park'])}",
        vendor_email=gen_email(),
        contract_start=f"2026-{random.randint(1, 6):02d}-01",
        contract_end=f"2026-{random.randint(7, 12):02d}-31",
        auto_renewal=random.choice(["Yes", "No"]),
        services_description=random.choice(["Managed Kubernetes platform", "Security monitoring", "Payment processing", "Data warehousing", "API gateway"]),
        pricing_details=random.choice(["$50K/month base + $0.01/transaction", "$200K/year enterprise", "Usage-based: $0.001/request", "Tiered: $10K-$500K/month"]),
        payment_terms=random.choice(["Net 30", "Net 45", "Monthly in advance"]),
        availability_sla=random.randint(99, 100),
        response_time_sla=random.choice(["15 min", "1 hour", "4 hours"]),
        resolution_time_sla=random.choice(["1 hour", "4 hours", "8 hours", "24 hours"]),
        data_categories=random.choice(["Customer PII, Transaction data", "Application logs, Metrics", "Source code, Build artifacts", "HR data, Payroll"]),
        processing_location=random.choice(["US-East", "US-West", "EU-Central", "Multi-region"]),
        subprocessors_list=random.choice(["AWS (US), CloudFlare (Global)", "GCP (US), Datadog (US)", "Azure (EU), Snowflake (US)"]),
        certifications=random.choice(["SOC 2 Type II, ISO 27001", "SOC 2 Type II, HIPAA", "ISO 27001, PCI DSS", "SOC 2 Type II"]),
        notice_period=random.randint(30, 90),
        transition_days=random.randint(30, 90),
        data_return_days=random.randint(30, 60),
    )
    return SyntheticDocument(text=text, label="Confidential", metadata={})


def gen_highly_confidential() -> SyntheticDocument:
    template = random.choice(HIGHLY_CONFIDENTIAL_TEMPLATES)
    text = template.format(
        # Short templates
        key=gen_aws_key(),
        secret=gen_secret(),
        pwd=gen_secret(),
        token=gen_api_token(),
        user=f"user{random.randint(1, 100)}",
        email=gen_email(),
        endpoint=f"/api/webhook/{random.randint(100, 999)}",
        system=random.choice(["prod-db", "staging-api", "analytics", "payments"]),
        date=f"2026-{random.randint(1, 12):02d}-{random.randint(1, 28):02d}",
        # Deployment runbook
        deployment_id=f"DEP-{random.randint(2026001, 2026999)}",
        service_name=random.choice(["API Gateway", "Auth Service", "Payment Service", "Notification Service", "Search Service", "Analytics Pipeline"]),
        version=f"{random.randint(1, 5)}.{random.randint(0, 9)}.{random.randint(0, 9)}",
        window_start=f"{random.randint(0, 23):02d}:00",
        window_end=f"{random.randint(0, 23):02d}:00",
        oncall_name=random.choice(["John Smith", "Jane Doe", "Bob Johnson", "Alice Williams", "Mike Brown", "Sarah Davis"]),
        oncall_phone=gen_phone(),
        pagerduty_escalation=f"PAGERDUTY-{random.randint(1000, 9999)}",
        aws_key=gen_aws_key(),
        aws_secret=gen_secret(),
        db_password=gen_secret(),
        redis_password=gen_secret(),
        api_keys=", ".join([gen_api_token() for _ in range(random.randint(3, 8))]),
        jwt_key=gen_jwt_key(),
        encryption_keys=", ".join([gen_encryption_key() for _ in range(random.randint(3, 6))]),
        cert_pem=gen_private_key_fragment(),
        canary_namespace=random.choice(["canary", "staging-canary", "prod-canary"]),
        pagerduty_service=random.choice(["api-gateway", "auth-service", "payment-service", "platform"]),
        security_email="security@company.com",
        infra_email="infra@company.com",
        mgmt_email="management@company.com",
        # Incident response
        incident_id=f"INC-{random.randint(2026001, 2026999)}",
        severity=random.randint(1, 3),
        status=random.choice(["Investigating", "Identified", "Monitoring", "Resolved"]),
        detection_time=f"2026-{random.randint(1, 12):02d}-{random.randint(1, 28):02d} {random.randint(0, 23):02d}:{random.randint(0, 59):02d}",
        reporter=random.choice(["Datadog Alert", "PagerDuty", "Customer Report", "Internal Monitoring", "Security Team"]),
        affected_services=random.choice(["API Gateway, Auth Service", "Payment Service, Notification Service", "Database Cluster, Cache Layer", "Search Service, Analytics Pipeline", "All Services (cascading)"]),
        users_impacted=random.randint(100, 1000000),
        impact_pct=random.randint(1, 100),
        revenue_at_risk=random.randint(10000, 10000000),
        sla_breach=random.choice(["Yes - 99.9% availability", "No - within SLA", "Partial - degraded performance"]),
        timeline=random.choice(["T+0m: Alert fired\nT+5m: On-call acknowledged\nT+15m: Root cause identified\nT+45m: Fix deployed\nT+60m: All clear", "T+0m: SEV-1 declared\nT+10m: War room started\nT+30m: DB failover\nT+120m: Recovery complete"]),
        root_cause=random.choice(["Database connection pool exhaustion", "Memory leak in v2.3.1 release", "Third-party API rate limit exceeded", "Configuration drift in Kubernetes", "Bad deploy: missing migration", "Certificate expiration", "DNS misconfiguration"]),
        compromised_aws_key=gen_aws_key(),
        compromised_aws_secret=gen_secret(),
        compromised_db_user=random.choice(["admin", "app_user", "readonly", "replication", "backup_user"]),
        compromised_db_password=gen_secret(),
        compromised_api_tokens=", ".join([gen_api_token() for _ in range(random.randint(2, 6))]),
        compromised_ssh_keys=random.choice(["bastion host key", "CI/CD deploy key", "backup server key", "developer laptop key", "monitoring agent key"]),
        compromised_certs=random.choice(["*.api.company.com", "internal CA", "mTLS client certs", "wildcard cert"]),
        containment_actions=random.choice(["Revoked all API keys", "Blocked malicious IPs", "Failed over to standby DB", "Disabled compromised feature", "Rotated all credentials", "Isolated affected namespace"]),
        patch_details=random.choice(["Upgrade library to v2.3.2", "Apply Kubernetes security patch", "Fix connection pool config", "Update certificate", "Rollback to v2.3.0"]),
        access_removal=random.choice(["Removed SSH keys", "Revoked IAM roles", "Deleted service accounts", "Rotated SSH certificates"]),
        integrity_checks=random.choice(["DB checksum verification", "File integrity monitoring", "Log analysis complete", "No tampering detected"]),
        forensic_details=random.choice(["Logs preserved in S3", "Memory dumps captured", "Network captures saved", "Timeline documented"]),
        recovery_plan=random.choice(["Full credential rotation", "System rebuild from clean images", "Data restoration from backup", "Gradual service restoration"]),
        recovery_eta=random.choice(["2 hours", "4 hours", "8 hours", "24 hours"]),
        lessons_learned=random.choice(["Add connection pool monitoring", "Automate dependency scanning", "Improve runbook accuracy", "Add chaos testing", "Implement circuit breakers", "Enhance alerting thresholds"]),
        postmortem_due=f"2026-{random.randint(1, 12):02d}-{random.randint(1, 28):02d}",
        postmortem_owner=random.choice(["John Smith", "Jane Doe", "Bob Johnson", "Alice Williams"]),
        review_date=f"2026-{random.randint(1, 12):02d}-{random.randint(1, 28):02d}",
        responder_name=random.choice(["John Smith", "Jane Doe", "Bob Johnson", "Alice Williams", "Mike Brown", "Sarah Davis"]),
        responder_email=gen_email(),
        approver_name=random.choice(["Alice Williams", "Mike Brown", "Sarah Davis", "Chris Wilson"]),
        approver_email=gen_email(),
        # Infrastructure config
        config_id=f"CFG-{random.randint(2026001, 2026999)}",
        environment=random.choice(["PRODUCTION", "STAGING", "DR"]),
        region=random.choice(["us-east-1", "us-west-2", "eu-west-1", "ap-southeast-1"]),
        account_id=f"{random.randint(100000000000, 999999999999)}",
        primary_db_host=random.choice(["prod-db-primary.cluster-xyz.us-east-1.rds.amazonaws.com", "prod-db-primary.cluster-abc.eu-west-1.rds.amazonaws.com"]),
        primary_az=random.choice(["us-east-1a", "us-east-1b", "us-west-2a", "eu-west-1a"]),
        primary_db_port=5432,
        primary_db_user=random.choice(["app_user", "service_account", "admin"]),
        primary_db_password=gen_secret(),
        primary_connection_string=random.choice(["postgresql://app_user:xxx@prod-db-primary.cluster-xyz.us-east-1.rds.amazonaws.com:5432/app", "postgresql://service_account:xxx@prod-db-primary.cluster-abc.eu-west-1.rds.amazonaws.com:5432/app"]),
        db_engine=random.choice(["PostgreSQL", "MySQL", "Aurora PostgreSQL"]),
        db_version=random.choice(["14.9", "15.4", "16.0", "8.0.35"]),
        db_encryption=random.choice(["AES-256", "AES-256-GCM"]),
        backup_retention=random.randint(7, 35),
        replica_count=random.randint(1, 3),
        replication_mode=random.choice(["sync", "async", "semi-sync"]),
        replica_db_host=random.choice(["prod-db-replica1.cluster-xyz.us-east-1.rds.amazonaws.com", "prod-db-replica2.cluster-xyz.us-east-1.rds.amazonaws.com"]),
        replica_az=random.choice(["us-east-1c", "us-west-2b", "eu-west-1b"]),
        replica_db_port=5432,
        replica_db_user=random.choice(["app_user", "readonly", "replication"]),
        replica_db_password=gen_secret(),
        redis_endpoint=random.choice(["prod-redis.xyz.use1.cache.amazonaws.com", "prod-redis-cluster.abc.euw1.cache.amazonaws.com"]),
        redis_nodes=random.randint(3, 12),
        redis_password=gen_secret(),
        redis_encryption=random.choice(["in-transit", "at-rest", "both"]),
        redis_eviction=random.choice(["allkeys-lru", "volatile-lru", "noeviction"]),
        redis_backup_schedule=random.choice(["daily", "hourly", "continuous"]),
        kafka_brokers=random.choice(["b-1.prod-kafka.xyz.us-east-1.amazonaws.com:9092,b-2.prod-kafka.xyz.us-east-1.amazonaws.com:9092", "kafka-prod.internal:9092"]),
        kafka_user=random.choice(["app_producer", "app_consumer", "admin"]),
        kafka_password=gen_secret(),
        kafka_topics=random.choice(["orders, payments, notifications", "events, logs, metrics", "transactions, audit, analytics"]),
        kafka_retention=random.randint(24, 168),
        rabbitmq_host=random.choice(["prod-rabbitmq.internal", "rabbitmq-prod.xyz.us-east-1.amazonaws.com"]),
        rabbitmq_user=random.choice(["app_user", "admin", "monitoring"]),
        rabbitmq_password=gen_secret(),
        rabbitmq_queues=random.choice(["orders, payments, notifications, dlq", "events, tasks, webhooks, retries"]),
        vault_addr=random.choice(["https://vault.company.internal", "https://vault-prod.company.internal", "https://vault.company.com:8200"]),
        vault_namespace=random.choice(["prod/", "prod/platform/", "prod/infra/"]),
        vault_token=gen_secret(),
        vault_ttl=random.choice(["1h", "4h", "24h", "7d"]),
        vault_mounts=random.choice(["secret/data, secret/metadata, kv/data", "secret/, kv/, transit/"]),
        vault_audit_enabled=random.choice(["true", "false"]),
        aws_sm_arns=random.choice(["arn:aws:secretsmanager:us-east-1:123456789012:secret:prod/*", "arn:aws:secretsmanager:us-west-2:123456789012:secret:prod/*"]),
        aws_sm_rotation=random.choice(["30d", "60d", "90d", "manual"]),
        prometheus_url=random.choice(["https://prometheus.company.internal", "https://monitoring.company.internal", "https://prometheus.company.com"]),
        grafana_url=random.choice(["https://grafana.company.internal", "https://dashboards.company.internal", "https://grafana.company.com"]),
        grafana_admin=random.choice(["admin", "grafana_admin", "platform_admin"]),
        grafana_password=gen_secret(),
        alertmanager_url=random.choice(["https://alertmanager.company.internal", "https://alerts.company.internal"]),
        pagerduty_integration=random.choice(["api-gateway", "auth-service", "payment-service", "platform", "infra"]),
        datadog_api_key=gen_secret(),
        wildcard_cert=random.choice(["*.company.com", "*.api.company.com", "*.internal.company.com"]),
        wildcard_expiry=f"2026-{random.randint(1, 12):02d}-{random.randint(1, 28):02d}",
        internal_ca_cert=random.choice(["company-root-ca", "company-intermediate-ca", "prod-internal-ca"]),
        internal_ca_expiry=f"2027-{random.randint(1, 12):02d}-{random.randint(1, 28):02d}",
        mtls_enabled=random.choice(["true", "false"]),
        # Key ceremony
        ceremony_id=f"CER-{random.randint(2026001, 2026999)}",
        location=random.choice(["Secure Room A (HSM)", "Air-gapped Lab", "Bank Vault Room", "Colocation Cage"]),
        participants=", ".join(random.sample(["John Smith", "Jane Doe", "Bob Johnson", "Alice Williams", "Mike Brown", "Sarah Davis", "Chris Wilson", "Lisa Anderson"], k=random.randint(4, 8))),
        witnesses=", ".join(random.sample(["Auditor A", "Auditor B", "Legal Counsel", "Compliance Officer"], k=random.randint(2, 4))),
        key_type=random.choice(["RSA", "ECDSA", "Ed25519", "X25519"]),
        system_name=random.choice(["Auth Service", "Payment Gateway", "Data Pipeline", "API Platform", "Internal CA"]),
        compliance_frameworks=random.choice(["SOC 2, PCI DSS", "ISO 27001, FedRAMP", "HIPAA, GDPR", "All of the above"]),
        algorithm=random.choice(["RSA-4096", "ECDSA-P384", "Ed25519", "X25519"]),
        key_size=random.choice([256, 384, 4096, 521]),
        entropy_source=random.choice(["HSM (FIPS 140-2 Level 3)", "Cloud KMS (Cloud HSM)", "Hardware RNG (TRNG)", "Multiple sources mixed"]),
        entropy_validation=random.choice(["FIPS 140-2 validated", "NIST SP 800-90B", "AIS 31 PTG.2", "Common Criteria EAL4+"]),
        kdf_algorithm=random.choice(["HKDF-SHA256", "PBKDF2-SHA256", "Argon2id"]),
        kdf_iterations=random.randint(100000, 1000000),
        root_ca_key=gen_private_key_fragment(),
        intermediate_ca_keys=", ".join([gen_private_key_fragment() for _ in range(random.randint(2, 4))]),
        leaf_certificates=", ".join([f"cert-{i}" for i in range(random.randint(10, 50))]),
        encryption_keys=", ".join([gen_encryption_key() for _ in range(random.randint(5, 20))]),
        signing_keys=", ".join([gen_jwt_key() for _ in range(random.randint(3, 10))]),
        hsm_partitions=random.choice(["Partition 1 (Root CA), Partition 2 (Intermediate)", "Partition 1 (Keys), Partition 2 (Certs)", "Separate HSMs per environment"]),
        distribution_method=random.choice(["HSM import (PKCS#11)", "Secure courier (tamper-evident)", "Encrypted email (PGP)", "Key ceremony (in-person)"]),
        recipients=", ".join(random.sample(["Platform Team", "Security Team", "Infra Team", "App Teams", "External Auditors"], k=random.randint(2, 5))),
        verification_method=random.choice(["Fingerprint verification", "Checksum validation", "HSM attestation", "Ceremony witness signatures"]),
        offline_backup_location=random.choice(["Offsite vault (geographically separate)", "Bank safe deposit box", "Air-gapped HSM", "Multiple locations"]),
        escrow_agent=random.choice(["Iron Mountain", "EscrowTech", "NCC Group", "Legal Firm A"]),
        escrow_conditions=random.choice(["Bankruptcy", "Acquisition/Merger", "Key personnel loss", "Regulatory action", "All of the above"]),
        escrow_verification_schedule=random.choice(["Annual", "Quarterly", "Semi-annual", "On-demand"]),
        revocation_procedure=random.choice(["CRL publication (daily)", "OCSP stapling", "Automated (ACME)", "Manual (emergency only)"]),
        crl_ocsp_endpoints=random.choice(["https://pki.company.com/crl, https://pki.company.com/ocsp", "https://ca.company.com/ocsp"]),
        emergency_revocation_contact=random.choice(["Security On-call: security-oncall@company.com", "PKI Admin: pki-admin@company.com", "24/7 Hotline: +1-800-XXX-XXXX"]),
        signatures=", ".join(random.sample(["John Smith", "Jane Doe", "Bob Johnson", "Alice Williams", "Mike Brown", "Sarah Davis", "Chris Wilson", "Lisa Anderson"], k=random.randint(4, 8))),
        notarized=random.choice(["true", "false"]),
        notary_name=random.choice(["Notary Public A", "Notary Public B", "Mobile Notary Service"]),
        notary_commission=random.choice(["Commission #123456", "Commission #789012", "Valid through 2028"]),
    )
    return SyntheticDocument(text=text, label="Highly Confidential", metadata={})


def gen_mixed_sensitivity() -> SyntheticDocument:
    """Generate mixed-sensitivity document labeled as Highly Confidential (highest-sensitivity-wins)."""
    template = random.choice(MIXED_SENSITIVITY_TEMPLATES)
    text = template.format(
        # Common variables
        date=f"2026-{random.randint(1, 12):02d}-{random.randint(1, 28):02d}",
        project_name=random.choice(["Atlas", "Orion", "Phoenix", "Nexus", "Vanguard"]),
        team_name=random.choice(["Platform", "Security", "Data", "API", "Frontend"]),
        completed_tickets=random.randint(10, 50),
        velocity=random.randint(20, 100),
        upcoming_feature_1=random.choice(["OAuth2 integration", "Rate limiting", "Audit logging", "Cache layer"]),
        upcoming_feature_2=random.choice(["Performance optimization", "New API endpoints", "UI improvements", "Tests"]),
        upcoming_feature_3=random.choice(["Documentation update", "Security hardening", "Migration", "Monitoring"]),
        action_items=random.choice(["Review PRs", "Update docs", "Deploy to staging", "Run load tests"]),
        db_host=random.choice(["db-internal-1", "db-internal-2", "db-staging"]),
        db_user=random.choice(["app_user", "readonly", "admin"]),
        db_password=gen_secret(),
        api_key=gen_api_token(),
        employee_name=f"{random.choice(['John', 'Jane', 'Bob', 'Alice', 'Mike', 'Sarah'])} {random.choice(['Smith', 'Doe', 'Johnson', 'Williams'])}",
        manager_name=f"{random.choice(['John', 'Jane', 'Bob', 'Alice'])} {random.choice(['Smith', 'Doe'])}",
        manager_email=gen_email(),
        buddy_name=f"{random.choice(['Mike', 'Sarah', 'Chris'])} {random.choice(['Brown', 'Davis', 'Wilson'])}",
        buddy_email=gen_email(),
        hr_name=f"{random.choice(['Lisa', 'Tom'])} {random.choice(['Anderson', 'Taylor'])}",
        hr_email=gen_email(),
        jira_url=random.choice(["https://jira.company.com", "https://jira.internal"]),
        gitlab_url=random.choice(["https://gitlab.company.com", "https://gitlab.internal"]),
        confluence_url=random.choice(["https://confluence.company.com", "https://wiki.internal"]),
        vpn_config=random.choice(["vpn.company.com", "vpn.internal", "wireguard://..."]),
        prod_db_host=random.choice(["prod-db-1", "prod-db-2", "prod-db-primary"]),
        prod_db_port=random.choice([5432, 3306, 1433]),
        prod_db_user=random.choice(["app_user", "service_account", "admin"]),
        prod_db_password=gen_secret(),
        aws_key=gen_aws_key(),
        aws_secret=gen_secret(),
        client_name=f"{random.choice(['Acme', 'Globex', 'Wayne', 'Stark', 'Umbrella'])} {random.choice(['Corp', 'Inc', 'LLC', 'Ltd'])}",
        project_overview=random.choice(["Build new API platform", "Migrate to cloud", "Security audit", "Performance optimization"]),
        scope_deliverables=random.choice(["API design", "Implementation", "Testing", "Documentation", "Deployment"]),
        timeline=random.choice(["3 months", "6 months", "9 months", "12 months"]),
        budget=random.randint(100000, 2000000),
        iban=gen_iban(),
        payment_ref=f"PAY-{random.randint(10000, 99999)}",
        api_endpoint=random.choice(["https://api.client.com/v1", "https://api.partner.io", "https://integration.client.net"]),
        client_api_key=gen_api_token(),
        webhook_secret=gen_webhook_secret(),
        review_id=f"SEC-REV-{random.randint(2026001, 2026999)}",
        reviewer_name=f"{random.choice(['John', 'Jane', 'Bob', 'Alice'])} {random.choice(['Smith', 'Doe'])}",
        reviewer_email=gen_email(),
        system_name=random.choice(["Auth Service", "Payment Gateway", "Data Pipeline", "API Platform"]),
        posture=random.choice(["Strong", "Acceptable", "Needs Improvement"]),
        finding_1=random.choice(["Missing rate limiting", "Weak password policy", "Insufficient logging", "Outdated dependencies"]),
        severity_1=random.choice(["HIGH", "MEDIUM", "LOW"]),
        finding_2=random.choice(["CORS misconfiguration", "Missing security headers", "Weak encryption", "Exposed debug endpoint"]),
        severity_2=random.choice(["HIGH", "MEDIUM", "LOW"]),
        finding_3=random.choice(["Insufficient input validation", "Missing authorization checks", "Weak session management", "Information disclosure"]),
        severity_3=random.choice(["HIGH", "MEDIUM", "LOW"]),
        found_aws_key=gen_aws_key(),
        found_github_token="".join(random.choices(string.ascii_letters + string.digits, k=36)),
        found_db_password=gen_secret(),
        approver_name=f"{random.choice(['Alice', 'Mike', 'Sarah'])} {random.choice(['Williams', 'Brown', 'Davis'])}",
        approver_email=gen_email(),
        topic=random.choice(["Database Setup", "API Security", "Docker Basics", "Kubernetes Intro", "CI/CD Pipeline"]),
        objective=random.choice(["connect to PostgreSQL", "secure your API", "containerize your app", "deploy to Kubernetes", "set up CI/CD"]),
        prereq_1=random.choice(["Python 3.8+", "Node.js 16+", "Go 1.18+", "Docker installed"]),
        prereq_2=random.choice(["Git configured", "Cloud account", "IDE setup"]),
    )
    return SyntheticDocument(text=text, label="Highly Confidential", metadata={})


GENERATORS = {
    "Public": gen_public,
    "Internal": gen_internal,
    "Confidential": gen_confidential,
    "Highly Confidential": gen_highly_confidential,
}

def generate_dataset(samples_per_class: int = SAMPLES_PER_CLASS) -> list[SyntheticDocument]:
    """Generate balanced synthetic dataset."""
    documents = []
    for label in CLASSIFICATION_LABELS:
        for i in range(samples_per_class):
            doc = GENERATORS[label]()
            doc.metadata = {
                "id": f"{label.lower().replace(' ', '_')}_{i:03d}",
                "generator": "synthetic",
                "seed": SEED,
            }
            documents.append(doc)
    random.shuffle(documents)
    return documents


def train_val_test_split(
    documents: list[SyntheticDocument], 
    train_ratio: float = 0.7, 
    val_ratio: float = 0.15, 
    test_ratio: float = 0.15
) -> tuple[list, list, list]:
    """Split dataset into train/val/test maintaining class balance.
    
    Args:
        documents: List of synthetic documents
        train_ratio: Proportion for training (default 0.7)
        val_ratio: Proportion for validation (default 0.15)
        test_ratio: Proportion for testing (default 0.15)
    
    Returns:
        Tuple of (train, val, test) document lists
    """
    assert abs(train_ratio + val_ratio + test_ratio - 1.0) < 1e-6, "Ratios must sum to 1.0"
    
    by_label = {label: [] for label in CLASSIFICATION_LABELS}
    for doc in documents:
        by_label[doc.label].append(doc)
    
    train, val, test = [], [], []
    for label in CLASSIFICATION_LABELS:
        random.shuffle(by_label[label])
        n = len(by_label[label])
        train_end = int(n * train_ratio)
        val_end = train_end + int(n * val_ratio)
        
        train.extend(by_label[label][:train_end])
        val.extend(by_label[label][train_end:val_end])
        test.extend(by_label[label][val_end:])
    
    random.shuffle(train)
    random.shuffle(val)
    random.shuffle(test)
    return train, val, test


def save_dataset(documents: list[SyntheticDocument], split: str) -> None:
    """Save dataset as text files with labels."""
    split_dir = OUTPUT_DIR / split
    split_dir.mkdir(parents=True, exist_ok=True)
    
    labels_file = split_dir / "labels.txt"
    with labels_file.open("w") as f:
        for doc in documents:
            text_file = split_dir / f"{doc.metadata['id']}.txt"
            text_file.write_text(doc.text, encoding="utf-8")
            f.write(f"{doc.metadata['id']}\t{doc.label}\n")
def generate_readme() -> None:
    """Generate README for the synthetic dataset."""
    total = SAMPLES_PER_CLASS * 4
    train_count = int(total * 0.8)
    test_count = total - train_count
    readme = f"""# SecureWaste Synthetic Classification Dataset

Generated for Sprint 2 (SCRUM-19, SCRUM-20, SCRUM-21) - AI/ML document classification.

## Overview

This dataset contains **synthetic/fictional documents** for training and evaluating
a document sensitivity classifier. **No real company data, personal information,
or credentials are included.**

## Classes (4 labels)

| Label | Description | Example Content |
|-------|-------------|-----------------|
| `Public` | No sensitive data | Meeting agendas, announcements, policies |
| `Internal` | Emails, phones, keywords | Contact info, team directories, internal memos |
| `Confidential` | Payment cards, IBANs, IDs, labels | Invoices, contracts, payroll, travel docs |
| `Highly Confidential` | API keys, secrets, private keys | Credentials, tokens, encryption keys |

## Dataset Statistics

- **Total samples**: {total}
- **Samples per class**: {SAMPLES_PER_CLASS}
- **Train/Test split**: 80/20 (stratified)
- **Train samples**: {train_count}
- **Test samples**: {test_count}
- **Random seed**: {SEED} (reproducible)

## Features for Classification

The classifier uses these heuristic features (rule-based, no ML model):

1. **Explicit labels**: CONFIDENTIAL, INTERNAL, RESTRICTED keywords
2. **High-sensitivity patterns**:
   - AWS keys (AKIA...)
   - API keys, secrets, passwords
   - Private keys (BEGIN PRIVATE KEY)
3. **Payment cards**: 16-digit Luhn-valid numbers
4. **IBANs**: Country code + check digits + BBAN
5. **National IDs**: 8-digit numbers
6. **Passports**: Letter + 7 digits
7. **Emails**: Standard email format
8. **Phones**: Various international/national formats

## Label Criteria (Decision Logic)

```
if has_secret_pattern:           -> Highly Confidential
elif has_card_or_iban_or_id:     -> Confidential
elif has_confidentiality_label:  -> Confidential
elif has_email_or_phone:         -> Internal
else:                            -> Public
```

Priority order: Highly Confidential > Confidential > Internal > Public

## File Structure

```
synthetic_dataset/
├── train/
│   ├── labels.txt          # id\\tlabel mapping
│   ├── public_000.txt
│   ├── internal_001.txt
│   └── ...
└── test/
    ├── labels.txt
    ├── confidential_000.txt
    └── ...
```

## Usage

```python
# Load training data
train_docs = []
with open("synthetic_dataset/train/labels.txt") as f:
    for line in f:
        doc_id, label = line.strip().split("\\t")
        text = Path(f"synthetic_dataset/train/{{doc_id}}.txt").read_text()
        train_docs.append((text, label))

# Train/test classifier (rule-based, no training needed)
from securewaste.core import predict_classification

for text, true_label in train_docs:
    pred_label = predict_classification(text)
    print(f"True: {{true_label}}, Pred: {{pred_label.value}}")
```

## Regenerating

```bash
python scripts/generate_synthetic_dataset.py
```

## Disclaimer

**All data is synthetic.** Generated values (cards, IBANs, keys, IDs) are randomly
created and have no real-world validity. Luhn check digits are computed for cards
but these are not real payment instruments.
"""
    (OUTPUT_DIR / "README.md").write_text(readme, encoding="utf-8")


def main():
    print(f"Generating synthetic dataset ({SAMPLES_PER_CLASS} samples per class)...")
    
    documents = generate_dataset(SAMPLES_PER_CLASS)
    train, val, test = train_val_test_split(documents, train_ratio=0.7, val_ratio=0.15, test_ratio=0.15)
    
    print(f"Train: {len(train)} samples")
    print(f"Val: {len(val)} samples")
    print(f"Test: {len(test)} samples")
    
    # Verify balance
    for split_name, split_docs in [("train", train), ("val", val), ("test", test)]:
        counts = {label: sum(1 for d in split_docs if d.label == label) for label in CLASSIFICATION_LABELS}
        print(f"  {split_name}: {counts}")
    
    save_dataset(train, "train")
    save_dataset(val, "val")
    save_dataset(test, "test")
    generate_readme()
    
    print(f"\nDataset saved to {OUTPUT_DIR}")
    print("Done!")


if __name__ == "__main__":
    main()