# ------------------------------------------------------------------------------
# vtimezone functions copied from https://github.com/pimutils/khal
# ------------------------------------------------------------------------------
# Copyright (c) 2013-2017 Christian Geier et al.
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import datetime as dt
import icalendar

def _tzid(tz):
    """
    Get the IANA zone id from a pytz or zoneinfo tzinfo object
    """
    return getattr(tz, 'zone', None) or getattr(tz, 'key', None) or str(tz)

def create_timezone(tz, first_date=None, last_date=None):
    """
    create an icalendar VTIMEZONE component for the given tzinfo object
    (pytz or zoneinfo), covering the transitions between first_date and
    last_date, typically the span of the event(s) being exported.

    :param tz: the timezone
    :param first_date: the very first datetime that needs to be included in the
    transition times, typically the DTSTART value of the (first recurring)
    event
    :type first_date: datetime.datetime
    :param last_date: the last datetime that needs to included, typically the
    end of the (very last) event (of a recursion set)
    :returns: timezone information
    :rtype: icalendar.Timezone()
    """
    first_date = dt.date.today() if not first_date else _asDate(first_date)
    last_date = dt.date.today() if not last_date else _asDate(last_date)
    # Search from well before first_date to well after last_date so the
    # transitions either side of the actual event span are discovered too
    # (not just whichever segment is active during it) -- 400 days
    # guarantees crossing any DST transition the timezone has.
    search_from = first_date - dt.timedelta(days=400)
    search_to = last_date + dt.timedelta(days=400)
    return icalendar.Timezone.from_tzid(_tzid(tz), first_date=search_from,
                                         last_date=search_to)

def _asDate(dtime):
    return dtime.date() if isinstance(dtime, dt.datetime) else dtime
