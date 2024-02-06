# Copyright: Ren Tatsumoto <tatsu at autistici.org> and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

from collections.abc import Iterable, Sequence
from gettext import ngettext
from typing import NamedTuple

from anki.notes import Note
from anki.utils import html_to_text_line
from aqt.qt import *

from .collection_manager import NameId
from .note_importer import ImportResultCounter, ImportResult
from .note_previewer import NotePreviewer

WIDGET_MIN_HEIGHT = 29
COMBO_MIN_WIDTH = 120


class CroProPushButton(QPushButton):
    def __init__(self, *__args):
        super().__init__(*__args)
        self.setMinimumHeight(WIDGET_MIN_HEIGHT)


class CroProLineEdit(QLineEdit):
    def __init__(self, *__args):
        super().__init__(*__args)
        self.setMinimumHeight(WIDGET_MIN_HEIGHT)


class SpinBox(QSpinBox):
    def __init__(self, min_val: int, max_val: int, step: int, value: int):
        super().__init__()
        self.setRange(min_val, max_val)
        self.setSingleStep(step)
        self.setValue(value)


class ProfileNameLabel(QLabel):
    def __init__(self, *args):
        super().__init__(*args)
        font = QFont()
        font.setBold(True)
        self.setFont(font)


class CroProComboBox(QComboBox):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setMaximumHeight(WIDGET_MIN_HEIGHT)
        self.setMinimumWidth(COMBO_MIN_WIDTH)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def all_items(self) -> Iterable[str]:
        """Returns an iterable of all items stored in the combo box."""
        for i in range(self.count()):
            yield self.itemText(i)


class DeckCombo(CroProComboBox):
    def set_decks(self, decks: Iterable[NameId]):
        self.clear()
        for deck_name, deck_id in decks:
            self.addItem(deck_name, deck_id)

    def current_deck(self) -> NameId:
        return NameId(self.currentText(), self.currentData())


class SearchResultLabel(QLabel):
    def __init__(self, *args, ):
        super().__init__(*args, )
        self.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Maximum)

    def hide_count(self):
        self.setText("")
        self.setStyleSheet("")
        self.hide()

    def set_count(self, found: int, displayed: int):
        if found == 0:
            self.setText(f'No notes found')
            self.setStyleSheet('QLabel { color: red; }')
        elif displayed == found:
            self.setText(f'{found} notes found')
            self.setStyleSheet('QLabel { color: green; }')
        else:
            self.setText(f'{found} notes found (displaying first {displayed})')
            self.setStyleSheet('QLabel { color: orange; }')
        if self.isHidden():
            self.show()


class NGetTextVariant(NamedTuple):
    singular: str
    plural: str


class ColoredCounter(QLabel):
    def __init__(self, color: str, description: NGetTextVariant):
        super().__init__()
        self.setStyleSheet("QLabel { color: %s; }" % color)
        self._description = description
        assert color.startswith('#')
        assert all(s.count('%d') == 1 for s in description)
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
        self.addWidget(self._success_label)
        self.addWidget(self._dupes_label)
        self.addStretch()

    def hide_counters(self):
        self._success_label.hide()
        self._dupes_label.hide()

    def set_import_status(self, results: ImportResultCounter):
        self._success_label.set_count(results.successes)
        self._dupes_label.set_count(results.duplicates)

    def set_import_count(self, success_count: int = 0, dupe_count: int = 0):
        self.set_import_status(ImportResultCounter({
            ImportResult.success: success_count,
            ImportResult.dupe: dupe_count
        }))


class ItemBox(QWidget):
    """Displays tag-like labels with × icons. Pressing on the × deletes the tag."""

    class ItemButton(QPushButton):
        _close_icon = QIcon(QPixmap(os.path.join(os.path.dirname(__file__), 'img', 'close.png')))

        def __init__(self, item_box: 'ItemBox', text: str):
            super().__init__(text)
            self.item_box = item_box
            self.setStyleSheet('''
                QPushButton {
                    background-color: #eef0f2;
                    color: #292c31;
                    border-radius: 12px;
                    padding: 3px 6px;
                    border: 0px;
                }
            ''')
            self.setIcon(self._close_icon)
            self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
            qconnect(self.clicked, lambda: self.item_box.remove_item(text))

    def __init__(self, parent: QWidget, initial_values: list[str]):
        super().__init__(parent=parent)
        self.items = dict.fromkeys(initial_values)
        self.setLayout(self._make_layout())

    def values(self) -> list[str]:
        return list(self.items)

    def _make_layout(self) -> QLayout:
        self.layout = QHBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        for text in self.items:
            self._add_item(text)
        self.layout.addStretch()
        return self.layout

    def count(self) -> int:
        # The last element in the layout is a stretch.
        return self.layout.count() - 1

    def _add_item(self, text: str) -> None:
        b = self.items[text] = self.ItemButton(self, text)
        self.layout.insertWidget(self.count(), b)

    def remove_item(self, text: str) -> None:
        if widget := self.items.pop(text, None):
            widget.deleteLater()

    def new_item(self, edit: QLineEdit) -> None:
        separators = (',', ' ', ';')
        if (text := edit.text()).endswith(separators):
            text = text.strip(''.join(separators))
            if text and text not in self.items:
                self._add_item(text)
            edit.setText('')


class NoteList(QWidget):
    """Lists notes and previews them."""
    _role = Qt.ItemDataRole.UserRole

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._note_list = QListWidget(self)
        self._previewer = NotePreviewer(self)
        self._other_media_dir = None
        self._enable_previewer = True
        self._setup_ui()
        self.itemDoubleClicked = self._note_list.itemDoubleClicked
        qconnect(self._note_list.currentItemChanged, self._on_current_item_changed)

    def _setup_ui(self):
        self.setLayout(layout := QHBoxLayout())
        self.setSizePolicy(QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.MinimumExpanding)

        layout.addWidget(splitter := QSplitter(Qt.Orientation.Horizontal))
        splitter.addWidget(self._note_list)
        splitter.addWidget(self._previewer)
        splitter.setCollapsible(0, False)
        splitter.setCollapsible(1, True)
        splitter.setSizes([200, 100])

        self._note_list.setAlternatingRowColors(True)
        self._note_list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self._note_list.setContentsMargins(0, 0, 0, 0)

        self._previewer.setHidden(True)

    def _on_current_item_changed(self, current: QListWidgetItem, _previous: QListWidgetItem):
        if current is None or self._enable_previewer is False:
            self._previewer.setHidden(True)
        else:
            self._previewer.setHidden(False)
            self._previewer.load_note(current.data(self._role), self._other_media_dir)

    def selected_notes(self) -> Sequence[Note]:
        return [item.data(self._role) for item in self._note_list.selectedItems()]

    def clear_selection(self):
        return self._note_list.clearSelection()

    def clear(self):
        self._note_list.clear()

    def set_notes(self, notes: Iterable[Note], hide_fields: list[str], media_dir: str, previewer: bool = True):
        self._other_media_dir = media_dir
        self._enable_previewer = previewer

        def is_hidden(field_name: str) -> bool:
            field_name = field_name.lower()
            return any(hidden_field.lower() in field_name for hidden_field in hide_fields)

        self.clear()
        for note in notes:
            item = QListWidgetItem()
            item.setText(' | '.join(
                html_to_text_line(field_content)
                for field_name, field_content in note.items()
                if not is_hidden(field_name) and field_content.strip())
            )
            item.setData(self._role, note)
            self._note_list.addItem(item)
