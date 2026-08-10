# SmartITMonitor USB Monitoring

The USB monitor detects USB device connection/removal events on
authorized managed lab computers.

Current stage:

- Detect USB connection
- Detect USB removal
- Record basic USB information
- Prepare events for the SmartITMonitor backend

Future managed-lab integration:

USB detected
→ backend event
→ admin approval request
→ approve/reject
→ audit log
→ policy enforcement
