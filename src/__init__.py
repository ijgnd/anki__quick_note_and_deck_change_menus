from anki import version as anki_version

old_anki = tuple(int(i) for i in anki_version.split(".")) < (2, 1, 20)

if old_anki:
    from . import old_change_notetype_deck
else:
    from . import new_change_notetype_deck
