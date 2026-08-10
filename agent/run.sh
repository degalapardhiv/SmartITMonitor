#!/bin/bash
cd "$(dirname "$0")/.."
exec .venv-agent/bin/python agent/smartit_agent.py
