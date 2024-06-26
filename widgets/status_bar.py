# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

from gettext import ngettext
from typing import NamedTuple

from aqt.qt import *

from ..note_importer import ImportResultCounter


class NGetTextVariant(NamedTuple):
    singular: str
    plural: str


class ColoredCounter(QLabel):
    def __init__(self, color: str, description: NGetTextVariant):
        super().__init__()
        self.setStyleSheet("QLabel { color: %s; }" % color)
        self._description = description
        assert color.startswith("#")
        assert all(s.count("%d") == 1 for s in description)
        # by default, the counter is not visible.
        self.hide()

    def set_count(self, count: int):
        if count > 0:
            self.setText(ngettext(self._description.singular, self._description.plural, count) % count)
            self.show()
        else:
            self.hide()


class StatusBar(QHBoxLayout):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._success_label = ColoredCounter(
            color="#228B22",
            description=NGetTextVariant(
                singular="%d note was successfully imported.",
                plural="%d notes were successfully imported.",
            ),
        )
        self._dupes_label = ColoredCounter(
            color="#FF8C00",
            description=NGetTextVariant(
                singular="%d note was a duplicate and was skipped.",
                plural="%d notes were duplicates and were skipped.",
            ),
        )
        self._error_label = ColoredCounter(
            color="#C63434",
            description=NGetTextVariant(
                singular="%d note encountered connection errors.",
                plural="%d notes encountered connection errors.",
            ),
        )
        self.addWidget(self._success_label)
        self.addWidget(self._dupes_label)
        self.addWidget(self._error_label)
        self.addStretch()

    def hide_counters(self) -> None:
        self._success_label.hide()
        self._dupes_label.hide()
        self._error_label.hide()

    def set_import_status(self, results: ImportResultCounter) -> None:
        return self.set_import_count(
            len(results.successes),
            len(results.duplicates),
            len(results.errors),
        )

    def set_import_count(self, success_count: int = 0, dupe_count: int = 0, error_count: int = 0) -> None:
        self._success_label.set_count(success_count)
        self._dupes_label.set_count(dupe_count)
        self._error_label.set_count(error_count)
