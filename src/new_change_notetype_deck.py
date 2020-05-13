# add-on for Anki 2.1
# License: AGPLv3
# Copyright: 2019 ijgnd

import uuid
from pprint import pprint as pp

from anki.hooks import addHook, runHook, wrap
from aqt import gui_hooks
from aqt import mw
from aqt.qt import *
from aqt.utils import showInfo, tooltip
from aqt.addcards import AddCards


some_valid_qt_keys = [
    "0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "A", "B", "C", "D",
    "E", "F", "G", "H", "I", "J", "K", "L", "M", "N", "O", "P", "Q", "R", "S", "T",
    "U", "V", "W", "X", "Y", "Z", "Space", "Tab", "CapsLock", "F1", "F2", "F3", "F4",
    "F5", "F6", "F7", "F8", "F9", "F10", "F11", "F12"
]


def gc(arg, fail=False):
    conf = mw.addonManager.getConfig(__name__)
    if conf:
        return conf.get(arg, fail)
    return fail


basic_stylesheet = """
QMenu::item {
    padding-top: 16px;
    padding-bottom: 16px;
    padding-right: 75px;
    padding-left: 20px;
    font-size: 15px;
}
QMenu::item:selected {
    background-color: #fd4332;
}
"""

# adapted from modelchooser.onModelChange
#  in modelchooser self.deck is mw.col !
def change_note_type(self, new):
    current = self.mw.col.models.current()["name"]
    print(f"in change_note_type and current is: {current}")
    m = self.mw.col.models.byName(new)
    print(f"in change_note_type and m is: {m}")
    if not m:
        msg = f"Can't select the notetype '{new}'. Do you really have a notetype with this name?"
        tooltip(msg)
        return
    self.mw.col.conf['curModel'] = m['id']
    cdeck = mw.col.decks.current()
    cdeck['mid'] = m['id']
    self.mw.col.decks.save(cdeck)
    print(f"keepModel is {keepModel}")
    if not keepModel:
        gui_hooks.current_note_type_did_change(current)
        self.modelChooser.mw.reset()
    else:  # Add-on 424778276 "Keep model of add cards" is installed
        self.modelChooser.updateModels()
        gui_hooks.current_note_type_did_change(m)
        self.modelChooser.parent.onModelChange()
        self.modelChooser.updateModels()
        self.modelChooser.parent.setAndFocusNote(self.modelChooser.parent.note)


def change_deck_to(self, deck_name):
    allnames = mw.col.decks.allNames(dyn=False)
    if deck_name not in allnames:
        m = "The Deck you selected named '%s' doesn't exist. Check your add-on config." % deck_name
        tooltip(m)
    else:
        self.deckChooser.deck.setText(deck_name)
        self.deckChooser._deckName = deck_name


def qtkey_from_config(value):
    key = gc(value)
    if not key:
        return None
    if not key.title() in some_valid_qt_keys:
        # tooltip("Illegal value for key")
        return None
    return eval('Qt.Key_' + str(key).title())


class keyFilter(QObject):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent

    def eventFilter(self, obj, event):
        if event.type() == QEvent.KeyPress:
            if event.key() == qtkey_from_config("menu_keyalt_for_return"):
                self.parent.alternative_keys(self.parent, Qt.Key_Return)
                return True
            elif event.key() == qtkey_from_config("menu_keyalt_for_arrow_left"):
                self.parent.alternative_keys(self.parent, Qt.Key_Left)
                return True
            elif event.key() == qtkey_from_config("menu_keyalt_for_arrow_down"):
                self.parent.alternative_keys(self.parent, Qt.Key_Down)
                return True
            elif event.key() == qtkey_from_config("menu_keyalt_for_arrow_up"):
                self.parent.alternative_keys(self.parent, Qt.Key_Up)
                return True
            elif event.key() == qtkey_from_config("menu_keyalt_for_arrow_right"):
                self.parent.alternative_keys(self.parent, Qt.Key_Right)
                return True
        return False


def alternative_keys(self, key):
    # https://stackoverflow.com/questions/56014149/mimic-a-returnpressed-signal-on-qlineedit
    # from PyQt5 import QtCore, QtGui
    # keyEvent = QtGui.QKeyEvent(QtCore.QEvent.KeyPress, key, QtCore.Qt.NoModifier)
    # QtCore.QCoreApplication.postEvent(self, keyEvent)
    keyEvent = QKeyEvent(QEvent.KeyPress, key, Qt.NoModifier)
    QCoreApplication.postEvent(self, keyEvent)


def process_entry(self, menus, e, currentlevel, func, errormsg):
    if isinstance(e, dict):
        menus[currentlevel].addAction(e["label"], lambda s=self, n=e["name"]: func(s, n))
    elif isinstance(e, list):
        newlevel = uuid.uuid4()
        menus[newlevel] = menus[currentlevel].addMenu(e[0]["label"])
        if gc("menu_use_alternative_keys_for_navigation", True):
            subnotetypefilter = keyFilter(menus[newlevel])
            menus[newlevel].installEventFilter(subnotetypefilter)
            menus[newlevel].alternative_keys = alternative_keys
        for i in e[1:]:
            menus = process_entry(self, menus, i, newlevel, func, errormsg)
    else:
        print(errormsg)
        pp(e)
    return menus


def qmenu_helper(self, label, conflist, func, errormsg):
    # menu = MyMenu(self)  # P: addMenu creates another QMenu
    menus = {}
    baselevel = uuid.uuid4()
    menus[baselevel] = QMenu(self)
    if gc("menu_use_alternative_keys_for_navigation", True):
        notetypefilter = keyFilter(menus[baselevel])
        menus[baselevel].installEventFilter(notetypefilter)
        menus[baselevel].alternative_keys = alternative_keys
    menus[baselevel].setStyleSheet(basic_stylesheet)
    label = QLabel(label)
    action = QWidgetAction(self)
    action.setDefaultWidget(label)
    menus[baselevel].addAction(action)
    for e in conflist:
        menus = process_entry(self, menus, e, baselevel, func, errormsg)
    menus[baselevel].exec(QCursor.pos())


def quick_change_notetype_menu(self):
    qmenu_helper(
        self,
        "Select Notetype (%s)" % gc("hotkey_notetypes", ""),
        gc("quick_notetypes", []),
        change_note_type,
        "error in quick_change_notetype_menu"
        )


def quick_change_deck_menu(self):
    qmenu_helper(
        self,
        "Select Deck (%s)" % gc("hotkey_decks", ""),
        gc("quick_decks", []),
        change_deck_to,
        "error in quick_change_deck_menu"
        )


def EditorContextMenu(view, menu):
    if isinstance(view.editor.parentWindow, AddCards) and gc("display_in_contextmenu", False):
        a = menu.addAction('change notetype')
        a.triggered.connect(lambda _, a=view.editor.parentWindow: quick_change_notetype_menu(a))
        a = menu.addAction('change deck')
        a.triggered.connect(lambda _, a=view.editor.parentWindow: quick_change_deck_menu(a))
addHook('EditorWebView.contextMenuEvent', EditorContextMenu)


def afterinit(self, mw):
    self.shortcut = QShortcut(gc('hotkey_notetypes', "Alt+q"), self)
    self.shortcut.activated.connect(self.quick_change_notetype_menu)
    self.modelChooser.models.setContextMenuPolicy(Qt.CustomContextMenu)
    self.modelChooser.models.customContextMenuRequested.connect(self.quick_change_notetype_menu)
    self.shortcut = QShortcut(gc('hotkey_decks', "Alt+w"), self)
    self.shortcut.activated.connect(self.quick_change_deck_menu)
    self.deckChooser.deck.setContextMenuPolicy(Qt.CustomContextMenu)
    self.deckChooser.deck.customContextMenuRequested.connect(self.quick_change_deck_menu)



AddCards.quick_change_notetype_menu = quick_change_notetype_menu
AddCards.change_note_type = change_note_type
AddCards.change_deck_to = change_deck_to
AddCards.quick_change_deck_menu = quick_change_deck_menu
AddCards.__init__ = wrap(AddCards.__init__, afterinit, "after")

def onload():
    global keepModel
    try:
        # __import__("424778276").keepModelInAddCards # Keep Model of Add Cards before 2020-04
         __import__("424778276").modelChooser.ModelChooser
    except:
        keepModel = False
    else:
        keepModel = True
addHook("profileLoaded", onload)