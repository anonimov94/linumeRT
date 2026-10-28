# SPDX-License-Identifier: GPL-2.0-or-later
"""Bounded diagnostic history, independent of CNC commands. Model-Author: Codex."""

import csv
import io
import sqlite3
from collections import deque
from datetime import datetime
from pathlib import Path


class Journal:
    def __init__(self, path, limit=1000):
        if limit < 1:
            raise ValueError("limit must be positive")
        self.entries = deque(maxlen=limit)
        self.db = None
        self.warning = ""
        try:
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            self.db = sqlite3.connect(path, timeout=0.05, check_same_thread=False)
            self.db.execute("CREATE TABLE IF NOT EXISTS messages "
                            "(id INTEGER PRIMARY KEY, stamp TEXT, level TEXT, message TEXT)")
            rows = self.db.execute("SELECT stamp, level, message FROM messages "
                                   "ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
            self.entries.extend(reversed(rows))
        except (OSError, sqlite3.Error) as exc:
            self._unavailable(exc)

    def _unavailable(self, exc):
        self.warning = f"Historia tylko w pamięci — zapis niedostępny: {exc}"
        self.close()

    def add(self, level, message):
        level = level if level in ("err", "warn") else "info"
        entry = (datetime.now().astimezone().isoformat(timespec="seconds"), level, str(message))
        self.entries.append(entry)
        if self.db is not None:
            try:
                with self.db:
                    self.db.execute("INSERT INTO messages (stamp, level, message) VALUES (?, ?, ?)",
                                    entry)
                    self.db.execute("DELETE FROM messages WHERE id NOT IN "
                                    "(SELECT id FROM messages ORDER BY id DESC LIMIT ?)",
                                    (self.entries.maxlen,))
            except sqlite3.Error as exc:
                self._unavailable(exc)

    def matching(self, level="", query=""):
        query = query.casefold()
        return [e for e in reversed(self.entries)
                if (not level or e[1] == level) and query in " ".join(e).casefold()]

    def csv(self, level="", query=""):
        stream = io.StringIO(newline="")
        writer = csv.writer(stream, delimiter=";")
        writer.writerow(("Czas ze strefą", "Poziom", "Komunikat"))
        writer.writerows(self.matching(level, query))
        return stream.getvalue()

    def close(self):
        if self.db is not None:
            self.db.close()
            self.db = None
