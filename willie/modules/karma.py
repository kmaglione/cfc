# coding=utf8
"""
karma.py - Willie Karma Module
"""
from __future__ import unicode_literals

from contextlib import contextmanager

from willie.tools import Ddict, Nick
from willie.module import commands, rule, priority


@contextmanager
def database(bot):
    if not bot.db:
        raise ConfigurationError("Database not set up, or unavailable.")
    conn = bot.db.connect()
    yield conn.cursor()
    conn.commit()
    conn.close()


def setup(bot):

    with database(bot) as cursor:
        cursor.execute('''CREATE TABLE IF NOT EXISTS karma (
            object TEXT PRIMARY KEY,
            karma INT
        )''')


@commands('karma')
def karma(bot, trigger):
    """Reports when and where the user was last seen."""
    target = trigger.group(2).strip()

    with database(bot) as cursor:
        for row in cursor.execute('''SELECT k.karma FROM karma AS k WHERE object = ?''',
                                  (target,)):
            bot.say('%s has %d points of karma.' % (target, row[0]))
            return

        bot.say("%s has no karma." % target)


@rule(r'^(\S+)(\+\+|--)$')
@priority('low')
def add_karma(bot, trigger):
    target = trigger.group(1);
    val = 1 if trigger.group(2) == '++' else -1

    if target == trigger.nick:
        val = -1

    with database(bot) as cursor:
        cursor.execute('''INSERT OR IGNORE INTO karma VALUES (?, 0);''',
                       (target,))
        cursor.execute('''UPDATE karma SET karma = karma + ? WHERE object = ?;''',
                       (val, target))
