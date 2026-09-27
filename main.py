#!/usr/bin/env python3
"""
PladixAgentIA_CLI - Ponto de Entrada Principal
Desenvolvido por PladixOficial
Telegram: t.me/pladixoficial
"""

import sys

# Force UTF-8 on Windows consoles to prevent cp1252 UnicodeEncodeError
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from deepseek_cli.cli import main

if __name__ == "__main__":
    main()

