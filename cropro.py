"""
Anki Add-on: Cross-Profile Search and Import

This add-on allows you to find and import notes from another profile into your currently loaded profile.
For example, you can make a "sentence bank" profile where you store thousands of cards generated by subs2srs,
and then use this add-on to search for and import cards with certain words into your main profile.
This helps keep your main profile uncluttered and free of large amounts of unneeded media.

GNU AGPL
Copyright (c) 2021-2023 Ren Tatsumoto
Copyright (c) 2018 Russel Simmons
Original concept by CalculusAce, with help from Matt VS Japan (@mattvsjapan)

TODO:
- Handle case where user has only one profile
- Review duplicate checking: check by first field, or all fields?
- When matching model is found, verify field count (or entire map?)
"""

import json
import os.path
from collections import defaultdict
from typing import Optional
from aqt.qt import *
from anki.models import NotetypeDict
from aqt import mw, gui_hooks
from aqt.utils import showInfo, disable_help_button, restoreGeom, saveGeom, openHelp, tooltip, openLink, showWarning

from .widgets.note_list import NoteList
from .widgets.utils import ProfileNameLabel, DeckCombo, CroProPushButton, CroProComboBox
from .widgets.search_result_label import SearchResultLabel
from .widgets.status_bar import StatusBar
from .widgets.search_bar import SearchBar
from .ajt_common.about_menu import menu_root_entry
from .ajt_common.consts import COMMUNITY_LINK
from .collection_manager import CollectionManager, sorted_decks_and_ids, get_other_profile_names, NameId
from .common import ADDON_NAME, LogDebug
from .config import config
from .edit_window import AddDialogLauncher
from .note_importer import import_note, ImportResultCounter
from .settings_dialog import open_cropro_settings

logDebug = LogDebug()


#############################################################################
# UI layout
#############################################################################

class MainDialogUI(QMainWindow):
    name = "cropro_dialog"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.search_bar = SearchBar(mw)
        self.status_bar = StatusBar()
        self.search_result_label = SearchResultLabel()
        self.into_profile_label = ProfileNameLabel()
        self.current_profile_deck_combo = DeckCombo()
        self.edit_button = CroProPushButton('Edit')
        self.import_button = CroProPushButton('Import')
        self.note_list = NoteList()
        self.note_type_selection_combo = CroProComboBox()
        self.init_ui()

    def init_ui(self):
        central_widget = QWidget(self)
        central_widget.setLayout(self.make_main_layout())
        self.setWindowTitle(ADDON_NAME)
        self.setCentralWidget(central_widget)
        self.setMinimumSize(680, 500)

    def make_main_layout(self) -> QLayout:
        main_vbox = QVBoxLayout()
        main_vbox.addWidget(self.search_bar)
        main_vbox.addWidget(self.search_result_label)
        main_vbox.addWidget(self.note_list)
        main_vbox.addLayout(self.status_bar)
        main_vbox.addLayout(self.make_input_row())
        return main_vbox

    def make_input_row(self) -> QLayout:
        import_row = QHBoxLayout()
        import_row.addWidget(QLabel('Into Profile:'))
        import_row.addWidget(self.into_profile_label)
        import_row.addWidget(QLabel('Deck:'))
        import_row.addWidget(self.current_profile_deck_combo)
        import_row.addWidget(QLabel('Map to Note Type:'))
        import_row.addWidget(self.note_type_selection_combo)
        import_row.addStretch(1)
        import_row.addWidget(self.edit_button)
        import_row.addWidget(self.import_button)
        return import_row


#############################################################################
# UI logic
#############################################################################


class WindowState:
    def __init__(self, window: MainDialogUI):
        self._window = window
        self._json_filepath = os.path.join(os.path.dirname(__file__), 'user_files', 'window_state.json')
        self._map = {
            "from_profile": self._window.search_bar.other_profile_names_combo,
            "from_deck": self._window.search_bar.other_profile_deck_combo,
            "to_deck": self._window.current_profile_deck_combo,
            "note_type": self._window.note_type_selection_combo,
        }
        self._state = defaultdict(dict)

    def save(self):
        self._load()
        for key, widget in self._map.items():
            self._state[mw.pm.name][key] = widget.currentText()
        with open(self._json_filepath, 'w', encoding='utf8') as of:
            json.dump(self._state, of, indent=4, ensure_ascii=False)
        saveGeom(self._window, self._window.name)
        logDebug(f'saved window state.')

    def _load(self) -> bool:
        if self._state:
            return True
        elif os.path.isfile(self._json_filepath):
            with open(self._json_filepath, encoding='utf8') as f:
                self._state.update(json.load(f))
            return True
        else:
            return False

    def restore(self):
        if self._load() and (profile_settings := self._state.get(mw.pm.name)):
            for key, widget in self._map.items():
                if (value := profile_settings.get(key)) in widget.all_items():
                    widget.setCurrentText(value)
        restoreGeom(self._window, self._window.name, adjustSize=True)


class MainDialog(MainDialogUI):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.window_state = WindowState(self)
        self.other_col = CollectionManager()
        self._add_window_mgr = AddDialogLauncher(self)
        self.connect_elements()
        self.setup_menubar()
        disable_help_button(self)

    def setup_menubar(self):
        menu_bar = self.menuBar()

        options_menu = menu_bar.addMenu('&Options')
        help_menu = menu_bar.addMenu('&Help')

        options_menu.addAction("Options", lambda: open_cropro_settings(parent=self))
        options_menu.addAction("Close", lambda: self.close())

        help_menu.addAction("Searching", lambda: openHelp("searching"))
        help_menu.addAction("Note fields", self.show_target_note_fields)
        help_menu.addAction("Ask question", lambda: openLink(COMMUNITY_LINK))

    def show_target_note_fields(self):
        if note_type := self.get_target_note_type():
            names = '\n'.join(f"* {name}" for name in mw.col.models.field_names(note_type))
            showInfo(
                text=f"## Target note type has fields:\n\n{names}",
                textFormat="markdown",
                title=ADDON_NAME,
            )
        else:
            showWarning(
                text="Target note type is not assigned.",
                title=ADDON_NAME,
            )

    def get_target_note_type(self) -> Optional[NotetypeDict]:
        selected_note_type_id = self.note_type_selection_combo.currentData()
        if selected_note_type_id and selected_note_type_id > 0:
            return mw.col.models.get(selected_note_type_id)

    def connect_elements(self):
        qconnect(self.search_bar.selected_profile_changed, self.open_other_col)
        qconnect(self.search_bar.search_requested, self.update_notes_list)
        qconnect(self.edit_button.clicked, self.new_edit_win)
        qconnect(self.import_button.clicked, self.do_import)

    def show(self):
        super().show()
        self.populate_ui()
        self.search_bar.focus()

    def populate_ui(self):
        self.status_bar.hide_counters()
        self.populate_note_type_selection_combo()
        self.populate_current_profile_decks()
        if self.search_bar.needs_to_repopulate_profile_names():
            self.populate_other_profile_names()
        self.open_other_col()
        self.into_profile_label.setText(mw.pm.name or 'Unknown')
        self.window_state.restore()

    def populate_other_profile_names(self):
        logDebug("populating other profiles.")

        other_profile_names: list[str] = get_other_profile_names()
        if not other_profile_names:
            msg: str = 'This add-on only works if you have multiple profiles.'
            showInfo(msg)
            logDebug(msg)
            self.hide()
            return

        self.search_bar.set_profile_names(other_profile_names)

    def populate_note_type_selection_combo(self):
        self.note_type_selection_combo.clear()
        self.note_type_selection_combo.addItem(*NameId.none_type())
        for note_type in mw.col.models.all_names_and_ids():
            self.note_type_selection_combo.addItem(note_type.name, note_type.id)

    def open_other_col(self):
        selected_profile_name = self.search_bar.selected_profile_name()

        if not self.other_col.is_opened or selected_profile_name != self.other_col.name:
            self.reset_cropro_status()
            self.other_col.open(selected_profile_name)
            self.populate_other_profile_decks()

    def reset_cropro_status(self):
        self.status_bar.hide_counters()
        self.search_result_label.hide_count()
        self.note_list.clear()

    def populate_current_profile_decks(self):
        logDebug("populating current profile decks...")
        self.current_profile_deck_combo.set_decks(sorted_decks_and_ids(mw.col))

    def populate_other_profile_decks(self):
        logDebug("populating other profile decks...")
        self.search_bar.set_decks([self.other_col.col_name_and_id(), *self.other_col.deck_names_and_ids(), ])

    def update_notes_list(self):
        self.search_bar.focus()
        self.reset_cropro_status()
        self.open_other_col()

        if not (self.search_bar.search_text() or config.allow_empty_search):
            return

        if not self.search_bar.decks_populated():
            return

        note_ids = self.other_col.find_notes(self.search_bar.current_deck(), self.search_bar.search_text())
        limited_note_ids = note_ids[:config['max_displayed_notes']]

        self.note_list.set_notes(
            map(self.other_col.get_note, limited_note_ids),
            hide_fields=config['hidden_fields'],
            media_dir=self.other_col.media_dir,
            previewer=config['preview_on_right_side'],
        )

        self.search_result_label.set_count(len(note_ids), len(limited_note_ids))

    def do_import(self):
        logDebug('beginning import')

        # get selected notes
        notes = self.note_list.selected_notes()

        # clear the selection
        self.note_list.clear_selection()

        logDebug(f'importing {len(notes)} notes')

        results = ImportResultCounter()

        for note in notes:
            results[import_note(
                other_note=note,
                other_col=self.other_col.col,
                model_id=self.note_type_selection_combo.currentData(),
                deck_id=self.current_profile_deck_combo.currentData(),
            )] += 1

        self.status_bar.set_import_status(results)
        mw.reset()

    def new_edit_win(self):
        if len(selected_notes := self.note_list.selected_notes()) > 0:
            self._add_window_mgr.create_window(selected_notes[-1])
        else:
            tooltip("No note selected.", period=1000, parent=self)

    def done(self, result_code: int):
        self.window_state.save()
        self.other_col.close_all()
        return super().done(result_code)


######################################################################
# Entry point
######################################################################

def init():
    # init dialog
    d = mw._cropro_main_dialog = MainDialog(parent=mw)
    # get AJT menu
    root_menu = menu_root_entry()
    # create a new menu item
    action = QAction(ADDON_NAME, root_menu)
    # set it to call show function when it's clicked
    qconnect(action.triggered, d.show)
    # and add it to the tools menu
    root_menu.addAction(action)
    # react to anki's state changes
    gui_hooks.profile_will_close.append(d.close)
    gui_hooks.profile_did_open.append(d.search_bar.clear_profiles_list)
