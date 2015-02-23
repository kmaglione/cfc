# coding=utf8
"""
find.py - Willie Spelling correction module
Copyright 2011, Michael Yanovich, yanovich.net
Copyright 2013, Edward Powell, embolalia.net
Licensed under the Eiffel Forum License 2.

http://willie.dftba.net

Contributions from: Matt Meinwald and Morgan Goose
This module will fix spelling errors if someone corrects them
using the sed notation (s///) commonly found in vi/vim.
"""
from __future__ import print_function, unicode_literals

import operator
import re
from willie.tools import Nick, WillieMemory
from willie.module import rule, priority


def setup(bot):
    bot.memory['find_lines'] = WillieMemory()


@rule('.*')
@priority('low')
def collectlines(bot, trigger):
    """Create a temporary log of what people say"""

    # Don't log things in PM
    if trigger.is_privmsg:
        return

    # Add a log for the channel and nick, if there isn't already one
    if trigger.sender not in bot.memory['find_lines']:
        bot.memory['find_lines'][trigger.sender] = WillieMemory()
    if Nick(trigger.nick) not in bot.memory['find_lines'][trigger.sender]:
        bot.memory['find_lines'][trigger.sender][Nick(trigger.nick)] = list()

    # Create a temporary list of the user's lines in a channel
    templist = bot.memory['find_lines'][trigger.sender][Nick(trigger.nick)]
    line = trigger.group()
    if line.startswith("s/"):  # Don't remember substitutions
        return
    elif line.startswith("\x01ACTION"):  # For /me messages
        line = line[:-1]
        templist.append(line)
    else:
        templist.append(line)

    del templist[:-10]  # Keep the log to 10 lines per person

    bot.memory['find_lines'][trigger.sender][Nick(trigger.nick)] = templist


#Match nick, s/find/replace/flags. Flags and nick are optional, nick can be
#followed by comma or colon, anything after the first space after the third
#slash is ignored, you can escape slashes with backslashes, and if you want to
#search for an actual backslash followed by an actual slash, you're shit out of
#luck because this is the fucking regex of death as it is.
@rule(r"""(?:
            (\S+)           # Catch a nick in group 1
          [:,]\s+)?         # Followed by colon/comma and whitespace, if given
          s/                # The literal s/
          (                 # Group 2 is the thing to find
            (?:\\. | [^\\/])+ # One or more non-slashes or escaped slashes
          )/(               # Group 3 is what to replace with
            (?:\\. | [^\\/])* # One or more non-slashes or escaped slashes
          )
          (?:/(\S+))?       # Optional slash, followed by group 4 (flags)
          """)
@priority('high')
def findandreplace(bot, trigger):
    # Don't bother in PM
    if trigger.is_privmsg:
        return

    # Correcting other person vs self.
    rnick = Nick(trigger.group(1) or trigger.nick)

    search_dict = bot.memory['find_lines']
    # only do something if there is conversation to work with
    if trigger.sender not in search_dict:
        return
    if Nick(rnick) not in search_dict[trigger.sender]:
        return

    FLAGS = {
        'i': re.I,
    }

    pattern = trigger.group(2)
    replacement = trigger.group(3)
    me = False  # /me command

    flags = (trigger.group(4) or '')

    # If g flag is given, replace all. Otherwise, replace once.
    count = 0 if 'g' in flags else 1

    flags = reduce(operator.add,
                   (FLAGS.get(f, 0) for f in flags),
                   re.U)

    def replacer(match):
        def replacer(m):
            if m.group(0) == '&':
                return match.group(0)

            if m.group(1).isdigit():
                try:
                    return match.group(int(m.group(1)))
                except IndexError:
                    return ''

            return m.group(1)

        return re.sub(r'\\(.)|&', replacer, replacement)

    repl = lambda s: re.sub(pattern, replacer, s, count)

    # Look back through the user's lines in the channel until you find a line
    # where the replacement works
    for line in reversed(search_dict[trigger.sender][rnick]):
        if line.startswith("\x01ACTION"):
            me = True  # /me command
            line = line[8:]
        else:
            me = False
        new_phrase = repl(line)
        if new_phrase != line:  # we are done
            break

    if not new_phrase or new_phrase == line:
        return  # Didn't find anything

    # Save the new "edited" message.
    action = (me and '\x01ACTION ') or ''  # If /me message, prepend \x01ACTION
    templist = search_dict[trigger.sender][rnick]
    templist.append(action + new_phrase)
    search_dict[trigger.sender][rnick] = templist
    bot.memory['find_lines'] = search_dict

    # output
    if not me:
        new_phrase = '\x02meant\x02 to say: ' + new_phrase
    if trigger.group(1):
        phrase = '%s thinks %s %s' % (trigger.nick, rnick, new_phrase)
    else:
        phrase = '%s %s' % (trigger.nick, new_phrase)

    bot.say(phrase)
