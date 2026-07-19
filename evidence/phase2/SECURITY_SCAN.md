# Security scan

Required gate record: **PASS**

`make secret-scan` fails closed across source and evidence while keeping
matched values silent. Final status is authoritative only when the gate
record and post-assembly secret scan both pass.
