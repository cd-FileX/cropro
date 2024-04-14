# Copyright: Ajatt-Tools and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import dataclasses
from collections.abc import Sequence

from aqt import AnkiQt
from aqt.qt import *

try:
    from .search_bar import CroProSearchBar
    from ..remote_search import get_request_url
    from .utils import CroProComboBox, CroProLineEdit, CroProPushButton, CroProSpinBox
except ImportError:
    from utils import CroProComboBox, CroProLineEdit, CroProPushButton, CroProSpinBox
    from remote_search import get_request_url
    from search_bar import CroProSearchBar


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


class RemoteSearchOptions(QWidget):
    def __init__(self):
        super().__init__()
        self._category_combo = new_combo_box(
            [
                RemoteComboBoxItem(None, "all"),
                "anime",
                "drama",
                "games",
                "literature",
            ],
            key="category",
        )
        self._sort_combo = new_combo_box(
            [
                RemoteComboBoxItem(None, "none"),
                "shortness",
                "longness",
            ],
            key="sort",
        )
        self._jlpt_level_combo = new_combo_box(
            [
                RemoteComboBoxItem(None, "all"),
                *map(str, range(1, 6)),
            ],
            key="jlpt",
        )
        self._setup_layout()

    def _setup_layout(self) -> None:
        layout = QHBoxLayout()
        layout.addWidget(QLabel("Category:"))
        layout.addWidget(self._category_combo)
        layout.addWidget(QLabel("Sort:"))
        layout.addWidget(self._sort_combo)
        layout.addWidget(QLabel("JLPT:"))
        layout.addWidget(self._jlpt_level_combo)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

    @property
    def category_combo(self) -> QComboBox:
        return self._category_combo

    @property
    def sort_combo(self) -> QComboBox:
        return self._sort_combo

    @property
    def jlpt_level_combo(self) -> QComboBox:
        return self._jlpt_level_combo


class RemoteSearchWidget(QWidget):
    """
    Search bar for https://docs.immersionkit.com/public%20api/search/
    """

    # noinspection PyArgumentList
    search_requested = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.opts = RemoteSearchOptions()
        self.bar = CroProSearchBar()
        self._setup_layout()
        self._connect_elements()

    def get_request_args(self) -> dict[str, str]:
        args = {}
        if keyword := self.bar.search_text():
            args["keyword"] = keyword
            for widget in (self.opts.sort_combo, self.opts.category_combo, self.opts.jlpt_level_combo):
                if param := widget.currentData().http_arg:
                    args[widget.key] = param
        return args

    def get_request_url(self) -> str:
        return get_request_url(self.get_request_args())

    def _setup_layout(self) -> None:
        self.setLayout(layout := QVBoxLayout())
        layout.addWidget(self.opts)
        layout.addWidget(self.bar)
        self.setSizePolicy(QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.Maximum)
        self.bar.focus_search_edit()

    def _connect_elements(self):
        def handle_search_requested():
            if self.get_request_url():
                # noinspection PyUnresolvedReferences
                self.search_requested.emit(self.bar.search_text())

        qconnect(self.bar.search_requested, handle_search_requested)


# Debug
##########################################################################


class App(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Test")
        self.search_bar = RemoteSearchWidget()
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


if __name__ == "__main__":
    main()
