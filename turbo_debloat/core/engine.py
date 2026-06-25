"""Движок выполнения playbook: парсинг, проверки, применение, отчёт.

Безопасность:
- dry_run по умолчанию (ничего не меняет, только показывает план);
- перед реальным применением создаётся бэкап;
- защищённые службы/пакеты/компоненты/ветки реестра пропускаются;
- сбой одного шага не останавливает остальные;
- для обратимых действий сохраняется undo в applied_steps.json.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, List, Optional

from turbo_debloat.core import backup as backup_mod
from turbo_debloat.core import safety
from turbo_debloat.core.compat_check import CompatibilityChecker
from turbo_debloat.core.logger import get_logger

IS_WINDOWS = sys.platform == "win32"
_log = get_logger()

_SC_ACTION = {"disable": "disabled", "manual": "demand", "auto": "auto"}


@dataclass
class Step:
    type: str
    label: str
    payload: dict
    category: str = ""
    risk: str = "safe"
    condition: str = ""
    step_id: str = ""


@dataclass
class StepResult:
    label: str
    ok: bool
    message: str = ""
    skipped: bool = False
    undo: List[str] = field(default_factory=list)


def load_playbook(path: Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def iter_steps(playbook: dict) -> List[Step]:
    """Развернуть категории playbook в плоский список шагов."""
    steps: List[Step] = []
    for cat in playbook.get("categories", []):
        cname = cat.get("name", cat.get("id", ""))
        crisk = cat.get("risk", "safe")

        for name in cat.get("services_disable", []):
            steps.append(Step("service", f"Отключить службу {name}", {"name": name, "action": "disable"}, cname, crisk))
        for svc in cat.get("services", []):
            steps.append(Step("service", f"Служба {svc.get('display', svc['name'])}: {svc.get('action','disable')}",
                              {"name": svc["name"], "action": svc.get("action", "disable")},
                              cname, "caution" if svc.get("action") == "manual" else crisk, svc.get("condition", "")))
        if cat.get("registry"):
            steps.append(Step("registry", f"{cname}: настройки реестра ({len(cat['registry'])})",
                              {"entries": cat["registry"]}, cname, crisk))
        for task in cat.get("scheduled_tasks_disable", []):
            steps.append(Step("sched", f"Отключить задачу {task.split(chr(92))[-1]}", {"path": task}, cname, crisk))
        if cat.get("hosts_block"):
            steps.append(Step("hosts", f"Заблокировать серверы телеметрии в hosts ({len(cat['hosts_block'])})",
                              {"hosts": cat["hosts_block"]}, cname, crisk))
        for feat in cat.get("dism_remove", []) + cat.get("dism_disable_optional", []):
            steps.append(Step("feature", f"Отключить компонент {feat}", {"name": feat}, cname, "caution"))
        keep = set(cat.get("appx_keep", []))
        for pkg in cat.get("appx_remove_all_users", []):
            steps.append(Step("appx", f"Удалить приложение {pkg}", {"name": pkg, "keep": keep}, cname, crisk))
        for b in cat.get("bcdedit_commands", []):
            steps.append(Step("cmd", b.get("description", b["cmd"]), {"cmd": b["cmd"], "undo": b.get("undo", "")}, cname, "caution"))
        for cmd in cat.get("powershell", []):
            steps.append(Step("powershell", cmd[:60], {"cmd": cmd}, cname, crisk))
    # уникальные id
    for i, s in enumerate(steps):
        s.step_id = f"{s.type}_{i}"
    return steps


class PlaybookEngine:
    def __init__(self, dry_run: bool = True) -> None:
        self.dry_run = dry_run
        self.checker = CompatibilityChecker()

    def run(self, playbook: dict, selected_ids: Optional[set] = None,
            progress_cb: Optional[Callable[[int, str], None]] = None) -> Dict:
        steps = iter_steps(playbook)
        if selected_ids is not None:
            steps = [s for s in steps if s.step_id in selected_ids]

        backup_path = None
        if not self.dry_run and IS_WINDOWS:
            svc_names = [s.payload["name"] for s in steps if s.type == "service"]
            backup_path = backup_mod.create_backup(services=svc_names)

        results: List[StepResult] = []
        applied_log: List[dict] = []
        n = max(1, len(steps))
        for i, step in enumerate(steps):
            if progress_cb:
                progress_cb(int(i / n * 100), step.label)
            ok, reason = self.checker.check(step.condition) if step.condition else (True, "")
            if not ok:
                results.append(StepResult(step.label, True, f"пропущено: {reason}", skipped=True))
                continue
            res = self._exec(step)
            results.append(res)
            if res.undo:
                applied_log.append({"label": step.label, "undo": res.undo})

        if backup_path is not None:
            try:
                (backup_path / "applied_steps.json").write_text(
                    json.dumps(applied_log, ensure_ascii=False, indent=2), encoding="utf-8")
            except Exception as e:
                _log.warning("Не удалось записать applied_steps.json (откат undo-команд будет недоступен): %s", e)

        done = sum(1 for r in results if r.ok and not r.skipped)
        skipped = sum(1 for r in results if r.skipped)
        failed = sum(1 for r in results if not r.ok)
        if progress_cb:
            progress_cb(100, "Готово")
        return {
            "total": len(results), "done": done, "skipped": skipped, "failed": failed,
            "dry_run": self.dry_run, "backup": str(backup_path) if backup_path else None,
            "results": [r.__dict__ for r in results],
        }

    # ---------- выполнение по типам ----------
    def _exec(self, step: Step) -> StepResult:
        try:
            handler = getattr(self, f"_do_{step.type}")
            return handler(step)
        except Exception as e:  # pragma: no cover
            return StepResult(step.label, False, f"ошибка: {e}")

    def _run(self, args: List[str], timeout: int = 60) -> subprocess.CompletedProcess:
        return subprocess.run(args, capture_output=True, text=True, timeout=timeout)

    def _do_service(self, step: Step) -> StepResult:
        name = step.payload["name"]
        if safety.is_protected_service(name):
            return StepResult(step.label, True, "защищено — пропуск", skipped=True)
        action = _SC_ACTION.get(step.payload.get("action", "disable"), "disabled")
        if self.dry_run or not IS_WINDOWS:
            return StepResult(step.label, True, f"[dry-run] sc config {name} start={action}",
                              undo=[f"sc config {name} start= auto"])
        cp = self._run(["sc", "config", name, f"start={action}"])
        return StepResult(step.label, cp.returncode == 0, cp.stderr.strip() or "ok",
                          undo=[f"sc config {name} start= auto"])

    def _do_registry(self, step: Step) -> StepResult:
        applied, undo = 0, []
        for entry in step.payload["entries"]:
            path, name, rtype, value = entry[0], entry[1], entry[2], entry[3]
            if safety.is_protected_registry(path):
                continue
            if self.dry_run or not IS_WINDOWS:
                applied += 1
                continue
            try:
                cp = self._run(["reg", "add", path, "/v", name, "/t", rtype, "/d", str(value), "/f"])
                if cp.returncode == 0:
                    applied += 1
                else:
                    _log.warning("reg add %s\\%s не удался: %s", path, name, cp.stderr.strip())
            except Exception as e:
                _log.warning("reg add %s\\%s упал: %s", path, name, e)
        return StepResult(step.label, True, f"{'[dry-run] ' if self.dry_run else ''}параметров: {applied}")

    def _do_sched(self, step: Step) -> StepResult:
        path = step.payload["path"]
        if self.dry_run or not IS_WINDOWS:
            return StepResult(step.label, True, f"[dry-run] disable {path}",
                              undo=[f'schtasks /change /tn "{path}" /enable'])
        cp = self._run(["schtasks", "/change", "/tn", path, "/disable"])
        return StepResult(step.label, cp.returncode == 0, cp.stderr.strip() or "ok",
                          undo=[f'schtasks /change /tn "{path}" /enable'])

    def _do_hosts(self, step: Step) -> StepResult:
        hosts = step.payload["hosts"]
        if self.dry_run or not IS_WINDOWS:
            return StepResult(step.label, True, f"[dry-run] добавить {len(hosts)} записей в hosts")
        try:
            hp = backup_mod._hosts_path()
            lines = hp.read_text(encoding="utf-8", errors="ignore").splitlines()
            existing = set(s.strip() for s in lines)
            added = 0
            # hosts на Windows — ASCII/ANSI с CRLF; пишем переводы строк \r\n.
            with hp.open("a", encoding="ascii", newline="") as f:
                for h in hosts:
                    entry = f"0.0.0.0 {h.split(':')[0]}"
                    if entry not in existing:
                        f.write("\r\n" + entry)
                        existing.add(entry)
                        added += 1
            return StepResult(step.label, True, f"добавлено записей: {added}")
        except Exception as e:
            return StepResult(step.label, False, f"ошибка hosts: {e}")

    def _do_feature(self, step: Step) -> StepResult:
        name = step.payload["name"]
        if safety.is_protected_feature(name):
            return StepResult(step.label, True, "защищено — пропуск", skipped=True)
        if self.dry_run or not IS_WINDOWS:
            return StepResult(step.label, True, f"[dry-run] DISM disable {name}",
                              undo=[f"dism /Online /Enable-Feature /FeatureName:{name} /NoRestart"])
        cp = self._run(["dism", "/Online", "/Disable-Feature", f"/FeatureName:{name}", "/NoRestart"], timeout=120)
        return StepResult(step.label, cp.returncode == 0, "ok" if cp.returncode == 0 else cp.stderr.strip(),
                          undo=[f"dism /Online /Enable-Feature /FeatureName:{name} /NoRestart"])

    def _do_appx(self, step: Step) -> StepResult:
        name = step.payload["name"]
        if safety.is_protected_appx(name) or name in step.payload.get("keep", set()):
            return StepResult(step.label, True, "защищено — пропуск", skipped=True)
        if self.dry_run or not IS_WINDOWS:
            return StepResult(step.label, True, f"[dry-run] удалить {name} (необратимо)")
        ps = (f"Get-AppxPackage -Name {name} -AllUsers | Remove-AppxPackage -AllUsers; "
              f"Get-AppxProvisionedPackage -Online | Where-Object DisplayName -like '{name}' | "
              f"Remove-AppxProvisionedPackage -Online")
        cp = self._run(["powershell", "-NoProfile", "-Command", ps], timeout=120)
        return StepResult(step.label, cp.returncode == 0, "удалено" if cp.returncode == 0 else cp.stderr.strip())

    def _do_cmd(self, step: Step) -> StepResult:
        cmd = step.payload["cmd"]
        undo = [step.payload["undo"]] if step.payload.get("undo") else []
        if self.dry_run or not IS_WINDOWS:
            return StepResult(step.label, True, f"[dry-run] {cmd}", undo=undo)
        cp = self._run(cmd.split())
        return StepResult(step.label, cp.returncode == 0, cp.stdout.strip() or cp.stderr.strip() or "ok", undo=undo)

    def _do_powershell(self, step: Step) -> StepResult:
        cmd = step.payload["cmd"]
        if self.dry_run or not IS_WINDOWS:
            return StepResult(step.label, True, f"[dry-run] {cmd[:70]}")
        cp = self._run(["powershell", "-NonInteractive", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", cmd], timeout=60)
        return StepResult(step.label, cp.returncode == 0, "ok" if cp.returncode == 0 else cp.stderr.strip())
