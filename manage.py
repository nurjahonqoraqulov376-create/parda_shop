#!/usr/bin/env python
import os
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent


def venv_python():
    """Loyihaning .venv ichidagi python (mavjud bo'lmasa None)."""
    if os.name == 'nt':
        path = BASE_DIR / '.venv' / 'Scripts' / 'python.exe'
    else:
        path = BASE_DIR / '.venv' / 'bin' / 'python'
    return path if path.exists() else None


def reexec_in_venv():
    """.venv faollashtirilmagan bo'lsa, buyruqni o'sha python bilan qayta
    ishga tushiradi.

    Kompyuterda bir nechta python bor (Miniconda, tizim python'i). Ular
    loyiha paketlarisiz, shuning uchun to'g'ridan-to'g'ri ishlatilsa
    `ModuleNotFoundError: No module named 'environ'` kabi xato chiqadi.
    """
    python = venv_python()
    if python is None or Path(sys.executable).resolve() == python.resolve():
        return
    print(f"[manage.py] .venv faollashtirilmagan - {python} bilan ishga tushirilmoqda.", file=sys.stderr)
    argv = [str(python), str(Path(__file__).resolve()), *sys.argv[1:]]
    proc = subprocess.Popen(argv)
    while True:
        try:
            # Ctrl+C konsoldagi barcha jarayonlarga yetadi; bola jarayon
            # o'zini to'xtatgunicha kutamiz.
            sys.exit(proc.wait())
        except KeyboardInterrupt:
            continue


if __name__ == '__main__':
    reexec_in_venv()
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'parda_shop.settings')
    from django.core.management import execute_from_command_line
    execute_from_command_line(sys.argv)
