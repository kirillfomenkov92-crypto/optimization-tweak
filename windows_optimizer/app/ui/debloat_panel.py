"""Раздел «Деблоат» внутри Windows Optimizer Pro.

Встраивает движок TurboDebloat (app/debloat) как панель: выбор профиля →
список шагов → выполнение → отчёт. Безопасность та же: сухой прогон по
умолчанию, бэкап перед изменениями, защита Defender/Store/Update, откат.
Права администратора запрашивает само приложение при старте — отдельная
элевация здесь не нужна.
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox, QDialog, QDialogButtonBox, QFrame, QHBoxLayout, QLabel,
    QProgressBar, QPushButton, QStackedWidget, QTextEdit, QTreeWidget,
    QTreeWidgetItem, QVBoxLayout, QWidget,
)

from app.core.logger import get_logger
from app.debloat import restore as restore_mod
from app.debloat.engine import PlaybookEngine, Step, iter_steps, load_playbook
from app.ui.widgets.worker import active_workers
from app.utils.resources import resource_path

_log = get_logger()
_PLAYBOOKS = resource_path("app", "debloat", "playbooks")
_RISK_ICON = {"safe": "🟢", "caution": "🟡", "advanced": "🔴"}


class _RunWorker(QThread):
    """Фоновое выполнение playbook (чтобы окно не зависало)."""
    progress = pyqtSignal(int, str)
    done = pyqtSignal(dict)
    failed = pyqtSignal(str)

    def __init__(self, playbook: dict, selected_ids: Optional[set], dry_run: bool) -> None:
        super().__init__()
        self._playbook = playbook
        self._selected = selected_ids
        self._dry_run = dry_run

    def run(self) -> None:
        # Регистрируемся, чтобы MainWindow.closeEvent → stop_all() дождался
        # завершения потока и не уронил «QThread: Destroyed while running».
        active_workers.add(self)
        try:
            engine = PlaybookEngine(dry_run=self._dry_run)
            report = engine.run(
                self._playbook, selected_ids=self._selected,
                progress_cb=lambda p, label: self.progress.emit(p, label),
            )
            self.done.emit(report)
        except Exception as e:  # pragma: no cover
            self.failed.emit(str(e))
        finally:
            active_workers.discard(self)


class _WarningDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Прочитайте перед запуском")
        v = QVBoxLayout(self)
        v.addWidget(QLabel("Что нельзя полностью отменить:"))
        v.addWidget(QLabel("• Удалённые приложения придётся переустанавливать из Microsoft Store."))
        v.addWidget(QLabel("\nЧто легко отменить:"))
        v.addWidget(QLabel("• Службы, реестр, сеть, hosts — восстанавливаются из бэкапа.\n"
                           "Бэкап создаётся автоматически перед стартом."))
        self.chk = QCheckBox("Я понимаю, что удалённые приложения не восстановятся")
        v.addWidget(self.chk)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self._ok = bb.button(QDialogButtonBox.StandardButton.Ok)
        self._ok.setEnabled(False)
        self.chk.stateChanged.connect(lambda _=0: self._ok.setEnabled(self.chk.isChecked()))
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        v.addWidget(bb)


class DebloatPanel(QWidget):
    """Панель деблоата: 4 экрана во внутреннем QStackedWidget."""

    def __init__(self) -> None:
        super().__init__()
        self.playbook: Optional[dict] = None
        self.steps: List[Step] = []
        self._worker: Optional[_RunWorker] = None
        self._last_report: Optional[Dict] = None

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        self.stack = QStackedWidget()
        root.addWidget(self.stack)
        self.stack.addWidget(self._screen_profiles())          # 0
        self.page_steps = QWidget(); self.stack.addWidget(self.page_steps)   # 1
        self.page_run = self._screen_run(); self.stack.addWidget(self.page_run)  # 2
        self.page_report = QWidget(); self.stack.addWidget(self.page_report)     # 3
        self.stack.setCurrentIndex(0)

    # ---------- экран 1: профили ----------
    def _screen_profiles(self) -> QWidget:
        w = QWidget()
        rt = QVBoxLayout(w)
        rt.setContentsMargins(24, 24, 24, 24)
        title = QLabel("Деблоат — выберите профиль")
        title.setObjectName("Title")
        rt.addWidget(title)
        rt.addWidget(self._sub("Defender, Microsoft Store и Обновления сохраняются в любом профиле."))

        cards = QHBoxLayout()
        cards.addWidget(self._profile_card("🚀 Турбо", "Максимум скорости при полной совместимости.\n✓ Браузер ✓ Офис ✓ Принтер", "compatible_fast"))
        cards.addWidget(self._profile_card("🎮 Геймер", "Минимум задержек, приоритет GPU, без фоновой записи.\n✓ Steam ✓ Discord ✓ Анти-читы", "gaming"))
        rt.addLayout(cards)

        ultra = QFrame(); ultra.setObjectName("Card")
        uv = QVBoxLayout(ultra)
        uv.addWidget(QLabel("⚠️ Ультра режим"))
        uv.addWidget(self._sub("Агрессивное удаление. Часть функций Windows отключится. Только если понимаете, что делаете."))
        ub = QPushButton("Выбрать Ультра"); ub.clicked.connect(lambda: self._choose("ultra"))
        uv.addWidget(ub)
        rt.addWidget(ultra)
        self.profiles_status = self._sub("")
        rt.addWidget(self.profiles_status)
        rt.addStretch(1)
        return w

    def _profile_card(self, title: str, desc: str, pid: str) -> QFrame:
        card = QFrame(); card.setObjectName("Card")
        v = QVBoxLayout(card)
        t = QLabel(title); t.setObjectName("Subtitle")
        v.addWidget(t)
        v.addWidget(self._sub(desc))
        b = QPushButton("Выбрать"); b.setObjectName("Primary")
        b.clicked.connect(lambda: self._choose(pid))
        v.addWidget(b)
        return card

    def _choose(self, pid: str) -> None:
        try:
            self.playbook = load_playbook(_PLAYBOOKS / f"{pid}.json")
            self.steps = iter_steps(self.playbook)
        except Exception as e:
            _log.error("Деблоат: не удалось загрузить профиль %s: %s", pid, e)
            self.profiles_status.setText(f"Ошибка загрузки профиля: {e}")
            return
        self._build_steps_screen()
        self.stack.setCurrentIndex(1)

    # ---------- экран 2: список шагов ----------
    def _build_steps_screen(self) -> None:
        old = self.page_steps.layout()
        if old:
            QWidget().setLayout(old)
        rt = QVBoxLayout(self.page_steps)
        rt.setContentsMargins(24, 24, 24, 24)
        head = QHBoxLayout()
        back = QPushButton("← Назад"); back.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        head.addWidget(back)
        head.addStretch(1)
        head.addWidget(QLabel(f"Профиль: {self.playbook.get('name')}"))
        rt.addLayout(head)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Шаг", "Риск"])
        groups: Dict[str, QTreeWidgetItem] = {}
        for s in self.steps:
            parent = groups.get(s.category)
            if parent is None:
                parent = QTreeWidgetItem(self.tree, [s.category, ""])
                parent.setFlags(parent.flags() | Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsAutoTristate)
                parent.setCheckState(0, Qt.CheckState.Checked)
                groups[s.category] = parent
            it = QTreeWidgetItem(parent, [s.label, _RISK_ICON.get(s.risk, "")])
            it.setFlags(it.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            it.setCheckState(0, Qt.CheckState.Unchecked if s.risk == "advanced" else Qt.CheckState.Checked)
            it.setData(0, Qt.ItemDataRole.UserRole, s.step_id)
        self.tree.expandAll()
        rt.addWidget(self.tree, 1)

        bottom = QHBoxLayout()
        self.dry = QCheckBox("Сухой прогон (ничего не менять) — рекомендуется первым")
        self.dry.setChecked(True)
        bottom.addWidget(self.dry)
        bottom.addStretch(1)
        start = QPushButton("Начать →"); start.setObjectName("Primary")
        start.clicked.connect(self._start)
        bottom.addWidget(start)
        rt.addLayout(bottom)

    def _selected_ids(self) -> set:
        ids = set()
        for i in range(self.tree.topLevelItemCount()):
            grp = self.tree.topLevelItem(i)
            for j in range(grp.childCount()):
                ch = grp.child(j)
                if ch.checkState(0) == Qt.CheckState.Checked:
                    ids.add(ch.data(0, Qt.ItemDataRole.UserRole))
        return ids

    # ---------- экран 3: выполнение ----------
    def _screen_run(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(24, 24, 24, 24)
        self.run_title = QLabel("Выполнение…"); self.run_title.setObjectName("Title")
        v.addWidget(self.run_title)
        self.bar = QProgressBar(); self.bar.setRange(0, 100)
        v.addWidget(self.bar)
        self.run_log = QTextEdit(); self.run_log.setReadOnly(True)
        v.addWidget(self.run_log, 1)
        return w

    def _start(self) -> None:
        dry = self.dry.isChecked()
        if not dry:
            dlg = _WarningDialog(self)
            if dlg.exec() != QDialog.DialogCode.Accepted:
                return
        ids = self._selected_ids()
        self.run_log.clear()
        self.run_title.setText("Сухой прогон…" if dry else "Выполнение…")
        self.stack.setCurrentIndex(2)
        self._worker = _RunWorker(self.playbook, ids, dry)
        self._worker.progress.connect(self._on_progress)
        self._worker.done.connect(self._on_done)
        self._worker.failed.connect(lambda m: self.run_log.append(f"Ошибка: {m}"))
        self._worker.start()

    def _on_progress(self, percent: int, label: str) -> None:
        self.bar.setValue(percent)
        self.run_log.append(f"[{percent:3d}%] {label}")

    # ---------- экран 4: отчёт ----------
    def _on_done(self, report: Dict) -> None:
        self._last_report = report
        old = self.page_report.layout()
        if old:
            QWidget().setLayout(old)
        v = QVBoxLayout(self.page_report)
        v.setContentsMargins(24, 24, 24, 24)
        t = QLabel("Готово! ✓" if not report["dry_run"] else "Сухой прогон завершён")
        t.setObjectName("Title")
        v.addWidget(t)
        v.addWidget(QLabel(f"Выполнено: {report['done']} · пропущено: {report['skipped']} · "
                           f"ошибок: {report['failed']} из {report['total']}"))
        if report.get("backup"):
            v.addWidget(self._sub(f"Бэкап для отката: {report['backup']}"))
        if report["dry_run"]:
            v.addWidget(self._sub("Это был сухой прогон — система не изменена. "
                                  "Снимите галочку «Сухой прогон» для реального применения."))

        details = QTextEdit(); details.setReadOnly(True)
        for r in report["results"]:
            mark = "•" if r.get("skipped") else ("✓" if r["ok"] else "✗")
            details.append(f"{mark} {r['label']} — {r.get('message','')}")
        v.addWidget(details, 1)

        self.report_status = self._sub("")
        v.addWidget(self.report_status)
        row = QHBoxLayout()
        again = QPushButton("В начало"); again.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        row.addWidget(again)
        row.addStretch(1)
        if report.get("backup"):
            undo = QPushButton("Откатить всё"); undo.setObjectName("Danger")
            undo.clicked.connect(lambda: self._restore(report["backup"]))
            row.addWidget(undo)
        v.addLayout(row)
        self.stack.setCurrentIndex(3)

    def _restore(self, backup_path: str) -> None:
        rep = restore_mod.restore(Path(backup_path), dry_run=False)
        failed = rep.get("failed", 0)
        if failed:
            self.report_status.setText(
                f"Откат завершён с ошибками: действий {rep['count']}, неуспешных {failed} — см. лог.")
        else:
            self.report_status.setText(f"Откат выполнен: действий {rep['count']}.")

    # ---------- утилиты ----------
    def _sub(self, text: str) -> QLabel:
        lbl = QLabel(text); lbl.setObjectName("Subtitle"); lbl.setWordWrap(True)
        return lbl
