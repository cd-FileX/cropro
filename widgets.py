# Copyright: Ren Tatsumoto <tatsu at autistici.org>
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

from typing import Iterable, List

from aqt.qt import *

from .collection_manager import NameId

WIDGET_HEIGHT = 29


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


class PreferencesButton(QPushButton):
    _icon = QIcon(os.path.join(os.path.dirname(__file__), 'img', 'gear.svg'))

    def __init__(self, *args):
        super().__init__(*args)
        self.setText('Preferences')
        self.setIcon(self._icon)
        self.setMaximumHeight(WIDGET_HEIGHT)


class ComboBox(QComboBox):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setMaximumHeight(WIDGET_HEIGHT)

    def all_items(self) -> Iterable[str]:
        """Returns an iterable of all items stored in the combo box."""
        for i in range(self.count()):
            yield self.itemText(i)


class DeckCombo(ComboBox):
    def set_decks(self, decks: Iterable[NameId]):
        self.clear()
        for deck_name, deck_id in decks:
            self.addItem(deck_name, deck_id)

    def current_deck(self) -> NameId:
        return NameId(self.currentText(), self.currentData())


class SearchResultLabel(QLabel):
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


class StatusBar(QHBoxLayout):
    def __init__(self):
        super().__init__()
        self._add_success_label()
        self._add_dupes_label()
        self.addStretch()
        self.hide()

    def _add_dupes_label(self):
        self._dupes_label = QLabel()
        self._dupes_label.setStyleSheet('QLabel { color: #FF8C00; }')
        self.addWidget(self._dupes_label)

    def _add_success_label(self):
        self._success_label = QLabel()
        self._success_label.setStyleSheet('QLabel { color: #228B22; }')
        self.addWidget(self._success_label)

    def hide(self):
        self._dupes_label.hide()
        self._success_label.hide()

    def set_status(self, successes: int, dupes: int):
        if successes:
            self._success_label.setText(f'{successes} notes successfully imported.')
            self._success_label.show()
        else:
            self._success_label.hide()

        if dupes:
            self._dupes_label.setText(f'{dupes} notes were duplicates, and skipped.')
            self._dupes_label.show()
        else:
            self._dupes_label.hide()


class ItemBox(QWidget):
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
            self.setLayoutDirection(Qt.RightToLeft)
            qconnect(self.clicked, lambda: self.item_box.remove_item(text))

    def __init__(self, parent: QWidget, initial_values: List[str]):
        super().__init__(parent=parent)
        self.items = dict.fromkeys(initial_values)
        self.setLayout(self._make_layout())

    def values(self) -> List[str]:
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
