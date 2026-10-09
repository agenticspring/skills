# Operator Archetypes ((Hermes-native operator roles))

Kill-chain order:

```text
RECON → WEAPONIZE → DELIVER → EXPLOIT → INSTALL → C2 → ACTIONS
```

Team factories:

```text
createBalancedTeam()
createStealthTeam()
createBreachTeam()
```

## recon — Reconnaissance Operator

- MITRE: TA0043
- Phases: RECON
- Status: stable
- Caps: osint, dns_enum, subdomain_discovery, port_scanning, service_detection
- Default tools:
  `dns_lookup`, `reverse_dns`, `whois_lookup`, `subdomain_enum`, `subdomain_takeover_check`, `nmap_scan`, `port_scan`, `network_trace`, `version_detect`, `robots_txt_fetch`, `cidr_expand`, `technology_detect`, `http_request`, `curl_request`, `header_analysis`, `api_endpoint_discovery`

## scanner — Vulnerability Scanner

- MITRE: TA0007
- Phases: WEAPONIZE
- Status: stable
- Caps: vuln_scanning, web_scanning, service_enum, config_audit
- Default tools:
  `nuclei_scan`, `ssl_scan`, `cors_check`, `csp_analysis`, `clickjacking_test`, `cookie_analysis`, `http_methods_test`, `open_redirect_test`, `port_scan`, `version_detect`, `technology_detect`, `api_endpoint_discovery`, `header_analysis`, `http_request`, `curl_request`

## exploiter — Exploitation Specialist

- MITRE: TA0001, TA0002
- Phases: DELIVER, EXPLOIT
- Status: experimental as swarm member
- Caps: exploit_dev, payload_delivery, initial_access, code_execution
- Default tools:
  `sqli_scan`, `xss_scan`, `ssti_test`, `lfi_test`, `open_redirect_test`, `nuclei_scan`, `ffuf_fuzz`, `dir_bruteforce`, `api_endpoint_discovery`, `http_methods_test`, `password_spray`, `hash_crack`, `base64_decode`, `url_encode`, `jwt_decode`, `http_request`, `curl_request`, `technology_detect`, `header_analysis`

## infiltrator — Lateral Movement Specialist

- MITRE: TA0008, TA0004
- Phases: INSTALL
- Status: experimental swarm
- Caps: priv_esc, lateral_movement, credential_access, domain_enum
- Default tools:
  `hash_crack`, `password_spray`, `jwt_decode`, `cookie_analysis`, `dns_lookup`, `port_scan`, `subdomain_enum`, `network_trace`, `nmap_scan`, `sqli_scan`, `lfi_test`, `cve_lookup`, `base64_decode`, `http_request`, `curl_request`, `technology_detect`

## exfiltrator — Data Exfiltration Specialist

- MITRE: TA0009, TA0010
- Phases: ACTIONS
- Status: experimental swarm
- Caps: data_collection, exfiltration, staging, compression
- Default tools:
  `http_request`, `curl_request`, `api_endpoint_discovery`, `dir_bruteforce`, `base64_decode`, `url_encode`, `jwt_decode`, `cookie_analysis`, `subdomain_enum`, `robots_txt_fetch`, `technology_detect`, `lfi_test`, `sqli_scan`, `header_analysis`, `cve_lookup`

## ghost — Persistence Specialist

- MITRE: TA0003, TA0005
- Phases: INSTALL, C2
- Status: experimental swarm
- Caps: persistence, evasion, cleanup, anti_forensics
- Default tools:
  `http_request`, `curl_request`, `cookie_analysis`, `header_analysis`, `csp_analysis`, `clickjacking_test`, `technology_detect`, `http_methods_test`, `jwt_decode`, `base64_decode`, `url_encode`, `robots_txt_fetch`, `subdomain_enum`, `open_redirect_test`, `ssl_scan`

## coordinator — Mission Coordinator

- MITRE: TA0011
- Phases: C2
- Status: experimental swarm
- Caps: orchestration, task_management, communication, decision_making
- Default tools:
  `cve_lookup`, `technology_detect`, `http_request`, `curl_request`, `header_analysis`, `nmap_scan`, `port_scan`, `dns_lookup`, `subdomain_enum`, `nuclei_scan`, `sqli_scan`, `api_endpoint_discovery`, `version_detect`, `ssl_scan`

## analyst — Security Analyst

- MITRE: reporting
- Phases: ACTIONS
- Status: stable
- Caps: analysis, reporting, recommendations, risk_assessment
- Default tools:
  `cve_lookup`, `jwt_decode`, `hash_crack`, `base64_decode`, `url_encode`, `technology_detect`, `ssl_scan`, `header_analysis`, `cors_check`, `csp_analysis`, `cookie_analysis`, `whois_lookup`, `dns_lookup`, `http_request`, `curl_request`

## Hermes assignment rule

```text
start with recon + scanner
only escalate to exploiter/infiltrator when scope + RoE + evidence justify
always finish with analyst report
```
