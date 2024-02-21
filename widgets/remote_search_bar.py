# Copyright: Ajatt-Tools and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import dataclasses
from typing import Sequence

from aqt.qt import *

try:
    from .utils import CroProComboBox, CroProLineEdit, CroProPushButton, CroProSpinBox
except ImportError:
    from utils import CroProComboBox, CroProLineEdit, CroProPushButton, CroProSpinBox


@dataclasses.dataclass
class RemoteComboBoxItem:
    http_arg: Union[str, int, None]
    visible_name: str = ""

    def __post_init__(self):
        self.visible_name = (self.visible_name or str(self.http_arg)).capitalize()


def new_combo_box(add_items: Sequence[Union[RemoteComboBoxItem, str]], key: str):
    b = CroProComboBox(key=key)
    for item in add_items:
        if not isinstance(item, RemoteComboBoxItem):
            item = RemoteComboBoxItem(item)
        b.addItem(item.visible_name, item)
    return b


class RemoteSearchBar(QWidget):
    """
    Search bar for https://docs.immersionkit.com/public%20api/search/
    """
    # noinspection PyArgumentList
    search_requested = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self._current_request_url = ""
        self._keyword_edit = CroProLineEdit()  # keyword
        self._category_combo = new_combo_box(
            [RemoteComboBoxItem(None, "all"), "anime", "drama", "games", "literature", ],
            key="category"
        )
        self._sort_combo = new_combo_box(
            [RemoteComboBoxItem(None, "none"), "shortness", "longness", ],
            key="sort"
        )
        self._jlpt_level_combo = new_combo_box(
            [RemoteComboBoxItem(None, "all"), *map(str, range(1, 6)), ],
            key="jlpt"
        )

        self._search_button = CroProPushButton("Search")
        self._setup_layout()
        self._connect_elements()

    def get_request_url(self) -> str:
        url = ""
        if keyword := self._keyword_edit.text():
            url = f"https://api.immersionkit.com/look_up_dictionary?keyword={keyword}"
            for widget in (self._sort_combo, self._category_combo, self._jlpt_level_combo):
                if param := widget.currentData().http_arg:
                    url = f"{url}&{widget.key}={param}"
        return url

    def focus(self):
        self._keyword_edit.setFocus()

    def _setup_layout(self) -> None:
        self.setLayout(layout := QVBoxLayout())
        layout.addLayout(self._make_search_settings_box())
        layout.addLayout(self._make_filter_row())
        self._keyword_edit.setPlaceholderText('<text to search>')
        self.setSizePolicy(QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.Maximum)
        self.focus()

    def _make_search_settings_box(self) -> QLayout:
        layout = QHBoxLayout()
        layout.addWidget(QLabel("Category:"))
        layout.addWidget(self._category_combo)
        layout.addWidget(QLabel("Sort:"))
        layout.addWidget(self._sort_combo)
        layout.addWidget(QLabel("JLPT:"))
        layout.addWidget(self._jlpt_level_combo)
        return layout

    def _make_filter_row(self) -> QLayout:
        layout = QHBoxLayout()
        layout.addWidget(self._keyword_edit)
        layout.addWidget(self._search_button)
        return layout

    def _connect_elements(self):
        def handle_search_requested():
            if (url := self.get_request_url()) != self._current_request_url:
                # noinspection PyUnresolvedReferences
                self.search_requested.emit(url)
                self._current_request_url = url

        qconnect(self._search_button.clicked, handle_search_requested)
        qconnect(self._keyword_edit.editingFinished, handle_search_requested)


# Debug
##########################################################################


class App(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Test")
        self.search_bar = RemoteSearchBar()
        self.initUI()
        qconnect(self.search_bar.search_requested, self.on_search_requested)

    def on_search_requested(self, text: str):
        print(f"Search: {text}")
        print(f"GET url: {self.search_bar.get_request_url()}")

    def initUI(self):
        self.setMinimumSize(640, 480)
        self.setLayout(layout := QVBoxLayout())
        layout.addWidget(self.search_bar)
        layout.addStretch(1)


def main():
    app = QApplication(sys.argv)
    ex = App()
    ex.show()
    app.exec()
    sys.exit()


if __name__ == '__main__':
    main()
