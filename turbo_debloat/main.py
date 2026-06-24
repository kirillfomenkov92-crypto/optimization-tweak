"""TurboDebloat — CLI (UI добавляется отдельными этапами).

Безопасно по умолчанию: без флагов делает СУХОЙ ПРОГОН (ничего не меняет).

  python -m turbo_debloat.main --list           показать шаги playbook
  python -m turbo_debloat.main                   сухой прогон (dry-run)
  python -m turbo_debloat.main --apply           применить (с подтверждением)
  python -m turbo_debloat.main --restore PATH    откатить из бэкапа
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Принудительно UTF-8 для вывода (иначе на Windows-консоли cp1252 ломает кириллицу).
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from turbo_debloat.core.engine import PlaybookEngine, iter_steps, load_playbook
from turbo_debloat.core import restore as restore_mod

_PLAYBOOKS = Path(__file__).resolve().parent / "playbooks"


def _playbook_path(name: str) -> Path:
    p = Path(name)
    if p.exists():
        return p
    return _PLAYBOOKS / f"{name}.json"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="turbo_debloat", description="TurboDebloat — деблоат Windows")
    ap.add_argument("--playbook", default="compatible_fast", help="имя playbook или путь к .json")
    ap.add_argument("--list", action="store_true", help="показать шаги")
    ap.add_argument("--apply", action="store_true", help="применить (иначе сухой прогон)")
    ap.add_argument("--yes", action="store_true", help="не спрашивать подтверждение (для --apply)")
    ap.add_argument("--restore", metavar="PATH", help="откатить из бэкапа")
    ap.add_argument("--gui", action="store_true", help="запустить графический интерфейс")
    args = ap.parse_args(argv)

    if args.gui:
        return _run_gui()

    if args.restore:
        report = restore_mod.restore(Path(args.restore), dry_run=not args.apply)
        print(f"Откат ({'применение' if args.apply else 'сухой прогон'}): действий {report['count']}")
        for a in report["actions"]:
            print("  •", a)
        return 0

    playbook = load_playbook(_playbook_path(args.playbook))
    steps = iter_steps(playbook)

    if args.list:
        print(f"Playbook: {playbook.get('name')} — шагов {len(steps)}")
        cur = None
        for s in steps:
            if s.category != cur:
                cur = s.category
                print(f"\n[{cur}]")
            print(f"  ({s.risk}) {s.label}")
        return 0

    dry = not args.apply
    if not dry:
        from turbo_debloat.core.admin import is_admin, IS_WINDOWS
        if IS_WINDOWS and not is_admin():
            print("Для применения нужны права администратора. Запустите от имени администратора.")
            return 1
    if not dry and not args.yes:
        print("ВНИМАНИЕ: будут применены изменения. Удалённые приложения не восстановятся.")
        print("Бэкап реестра/служб/hosts создаётся автоматически. Продолжить? [y/N] ", end="")
        if input().strip().lower() not in ("y", "yes", "д", "да"):
            print("Отменено.")
            return 1

    engine = PlaybookEngine(dry_run=dry)
    report = engine.run(playbook, progress_cb=lambda p, label: print(f"  [{p:3d}%] {label}"))
    print(f"\nИтог ({'СУХОЙ ПРОГОН' if dry else 'ПРИМЕНЕНО'}): "
          f"выполнено {report['done']}, пропущено {report['skipped']}, ошибок {report['failed']} из {report['total']}")
    if report.get("backup"):
        print(f"Бэкап: {report['backup']}")
    return 0


def _run_gui() -> int:
    # Повышаем права (UAC) — без них реальное применение не сработает.
    from turbo_debloat.core.admin import is_admin, run_as_admin, IS_WINDOWS
    if IS_WINDOWS and not is_admin():
        if run_as_admin(["--gui"]):
            return 0
    try:
        from PyQt6.QtWidgets import QApplication
    except Exception as e:
        print(f"Требуется PyQt6: {e}")
        return 2
    from turbo_debloat.ui.main_window import MainWindow

    app = QApplication(sys.argv)
    app.setApplicationName("TurboDebloat")
    win = MainWindow()
    win.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
