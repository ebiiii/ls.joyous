# ------------------------------------------------------------------------------
# Test ical utility clases
# ------------------------------------------------------------------------------
import sys
import datetime as dt
import pytz
from django.test import TestCase
from django.utils import timezone
from wagtail.models import Page
from icalendar import vDatetime, vDate, vRecur, vDDDTypes, vText
from ls.joyous.utils.telltime import getLocalDatetime
from ls.joyous.formats.ical import (VResults, vDt, vSmart, TimeZoneSpan, VMatch,
                                    VEventFactory, CalendarTypeError,
                                    Event, VEvent, SimpleVEvent)
from freezegun import freeze_time

# ------------------------------------------------------------------------------
class TestVResults(TestCase):
    def testEmpty(self):
        results = VResults()
        self.assertEqual(results.success, 0)
        self.assertEqual(results.fail,    0)
        self.assertEqual(results.error,   0)

    def testInit(self):
        results = VResults(3, 2, 1)
        self.assertEqual(results.success, 3)
        self.assertEqual(results.fail,    2)
        self.assertEqual(results.error,   1)

    def testEquals(self):
        a = VResults()
        b = VResults()
        self.assertTrue(a == b)
        b.success = 1
        self.assertFalse(a == b)
        a += b
        self.assertTrue(a == b)
        b.error = 1
        self.assertFalse(a == b)

    def testRepr(self):
        results = VResults()
        self.assertEqual(repr(results), "Success=0, Fail=0, Error=0")
        results.error = 1
        self.assertEqual(repr(results), "Success=0, Fail=0, Error=1")

# ------------------------------------------------------------------------------
class TestVDt(TestCase):
    def testNone(self):
        v = vDt()
        self.assertFalse(v)
        self.assertEqual(v, None)
        self.assertEqual(v.date(), None)
        self.assertEqual(v.time(), None)
        self.assertEqual(v.datetime(), None)
        self.assertEqual(v.tzinfo(), None)
        self.assertEqual(v.zone(), None)
        self.assertEqual(str(v.timezone()), "Asia/Tokyo")

    def testNaiveDt(self):
        mo = dt.datetime(1987, 6, 21, 3, 54, 0)
        v = vDt(mo)
        self.assertTrue(v)
        self.assertEqual(v, mo)
        self.assertEqual(v, vDatetime(mo))
        self.assertEqual(v, vDatetime.from_ical("19870621T035400"))
        self.assertEqual(v.date(), mo.date())
        self.assertEqual(v.time(), mo.time())
        self.assertEqual(v.datetime(), timezone.make_aware(mo))
        self.assertEqual(v.tzinfo(), None)
        self.assertEqual(v.zone(), None)
        self.assertEqual(str(v.timezone()), "Asia/Tokyo")

    def testTzinfoDt(self):
        mo = dt.datetime(2020, 2, 2, 2, tzinfo=dt.timezone.utc)
        v = vDt(mo)
        self.assertTrue(v)
        self.assertEqual(v, mo)
        self.assertEqual(v, vDatetime(mo))
        self.assertEqual(v, vDatetime.from_ical("20200202T020000Z"))
        self.assertEqual(v.date(), mo.date())
        self.assertEqual(v.time(), mo.time())
        self.assertEqual(v.datetime(), mo)
        self.assertEqual(v.tzinfo(), mo.tzinfo)
        self.assertEqual(v.zone()[:3], "UTC") # changed in Python 3.6
        self.assertEqual(v.timezone(), dt.timezone.utc)

    def testAwareDt(self):
        mo = vDatetime(pytz.timezone("Pacific/Chatham").localize(
                        dt.datetime(2013, 4, 25, 6, 0)))
        v = vDt(mo)
        self.assertTrue(v)
        self.assertEqual(v, mo)
        self.assertEqual(v, mo.dt)
        self.assertEqual(v, vDatetime.from_ical("20130425T060000",
                                                "Pacific/Chatham"))
        self.assertEqual(v.date(), mo.dt.date())
        self.assertEqual(v.time(), mo.dt.time())
        self.assertEqual(v.datetime(), mo.dt)
        self.assertEqual(v.tzinfo(), mo.dt.tzinfo)
        self.assertEqual(v.zone(), "Pacific/Chatham")
        self.assertEqual(str(v.timezone()), "Pacific/Chatham")

    def testUnknownTZDt(self):
        tz = pytz.FixedOffset(540)
        tz.zone = "Japan/Edo"
        mo = timezone.make_aware(dt.datetime(2013, 4, 25, 6, 0), tz)
        v = vDt(mo)
        self.assertTrue(v)
        self.assertEqual(v, mo)
        self.assertEqual(v, vDatetime(mo))
        self.assertEqual(v.date(), mo.date())
        self.assertEqual(v.time(), mo.time())
        self.assertEqual(v.datetime(), mo)
        self.assertEqual(v.tzinfo(), mo.tzinfo)
        self.assertEqual(v.zone(), "Japan/Edo")
        with self.assertRaises(CalendarTypeError):
            v.timezone()

    def testDate(self):
        day = dt.date(1979, 8, 16)
        v = vDt(day)
        self.assertTrue(v)
        self.assertEqual(v, day)
        self.assertEqual(v, vDate(day))
        self.assertEqual(v, vDate.from_ical("19790816"))
        self.assertEqual(v.date(), day)
        self.assertEqual(v.time(), None)
        self.assertEqual(v.datetime(), getLocalDatetime(day, dt.time.min))
        self.assertEqual(v.tzinfo(), None)
        self.assertEqual(v.zone(), None)
        self.assertEqual(str(v.timezone()), "Asia/Tokyo")

    def testDateInc(self):
        day = dt.date(1979, 8, 16)
        v = vDt(day, inclusive=True)
        self.assertTrue(v)
        self.assertEqual(v, dt.date(1979, 8, 17))
        self.assertEqual(v.date(), dt.date(1979, 8, 17))
        self.assertEqual(v.date(inclusive=True), day)

# ------------------------------------------------------------------------------
class TestVSmart(TestCase):
    def testEmpty(self):
        v = vSmart("")
        self.assertFalse(v)
        self.assertEqual(str(v), "")

    def testStr(self):
        v = vSmart("ġedæġhwāmlīcan")
        self.assertTrue(v)
        self.assertEqual(str(v), "ġedæġhwāmlīcan")

    def testQuoPri(self):
        v = vSmart(b'=C4=A1ed=C3=A6=C4=A1hw=C4=81ml=C4=ABcan')
        v.params['ENCODING'] = "QUOTED-PRINTABLE"
        self.assertEqual(str(v), "ġedæġhwāmlīcan")

    def testBase64(self):
        v = vSmart(b'xKFlZMOmxKFod8SBbWzEq2Nhbg==')
        v.params['ENCODING'] = "BASE64"
        self.assertEqual(str(v), "ġedæġhwāmlīcan")

# ------------------------------------------------------------------------------
def addProps(vev, **kwargs):
    dtProps = {'dtstart', 'dtend', 'dtstamp', 'created', 'last-modified'}
    for prop, v in kwargs.items():
        if prop in dtProps:
            if not hasattr(v, 'dt'):
                v = vDt(v)
            vev.add(prop, v)
        else:
            vev.add(prop, v)

class TestTimeZoneSpan(TestCase):
    def testEmpty(self):
        span = TimeZoneSpan()
        with self.assertRaises(TimeZoneSpan.NotInitializedError):
            span.createVTimeZone(pytz.utc)

    def _assertHasSegment(self, vtz, subcomponents, tzname, offsetFrom, offsetTo):
        for sub in subcomponents:
            if (str(sub.get('TZNAME')) == tzname and
                sub['TZOFFSETFROM'].td == offsetFrom and
                sub['TZOFFSETTO'].td == offsetTo):
                return
        self.fail("No {} segment {} -> {} found in {}"
                 .format(tzname, offsetFrom, offsetTo, vtz.to_ical()))

    def test1LunchTime(self):
        tz = pytz.timezone("Pacific/Auckland")
        vev = SimpleVEvent()
        addProps(vev,
                 summary = "Friday lunch",
                 uid = "1800",
                 dtstart = timezone.make_aware(dt.datetime(1996, 3, 1, 12), tz),
                 dtend   = timezone.make_aware(dt.datetime(1996, 3, 1, 13), tz))
        span = TimeZoneSpan(vev)
        vtz = span.createVTimeZone(tz)
        self.assertEqual(vtz['TZID'], "Pacific/Auckland")
        self._assertHasSegment(vtz, vtz.daylight, "NZDT",
                               dt.timedelta(hours=12), dt.timedelta(hours=13))
        self._assertHasSegment(vtz, vtz.standard, "NZST",
                               dt.timedelta(hours=13), dt.timedelta(hours=12))

    def testLunchTimes(self):
        tz = pytz.timezone("Pacific/Auckland")
        vev = SimpleVEvent()
        addProps(vev, summary = "All lunch times", uid = "999",
                 dtstart = timezone.make_aware(dt.datetime(1996, 3, 1, 12), tz),
                 dtend   = timezone.make_aware(dt.datetime(1996, 3, 1, 13), tz),
                 rrule   = vRecur.from_ical("FREQ=WEEKLY;WKST=SU;BYDAY=MO,TU,WE,TH,FR"))
        span = TimeZoneSpan(vev)
        vev = SimpleVEvent()
        addProps(vev, summary = "Saturday Brunch", uid = "2000",
                 dtstart = timezone.make_aware(dt.datetime(2019, 6, 4, 10), tz),
                 dtend   = timezone.make_aware(dt.datetime(2019, 6, 4, 11, 30), tz))
        span.add(vev)
        vtz = span.createVTimeZone(tz)
        self.assertEqual(vtz['TZID'], "Pacific/Auckland")
        self._assertHasSegment(vtz, vtz.daylight, "NZDT",
                               dt.timedelta(hours=12), dt.timedelta(hours=13))
        self._assertHasSegment(vtz, vtz.standard, "NZST",
                               dt.timedelta(hours=13), dt.timedelta(hours=12))

    def testOverlapping(self):
        tz = pytz.timezone("Pacific/Auckland")
        vev = SimpleVEvent()
        addProps(vev, summary = "Storytelling", uid = "1000",
                 dtstart = timezone.make_aware(dt.datetime(2016, 4, 5, 10), tz),
                 dtend   = timezone.make_aware(dt.datetime(2016, 4, 5, 11), tz),
                 rrule   = vRecur.from_ical("FREQ=WEEKLY;WKST=SU;BYDAY=TU;UNTIL=20160519"))
        span = TimeZoneSpan(vev)
        vev = SimpleVEvent()
        addProps(vev, summary = "Parade", uid = "1002",
                 dtstart = timezone.make_aware(dt.datetime(2016, 4, 5, 9), tz),
                 dtend   = timezone.make_aware(dt.datetime(2016, 4, 5, 13), tz))
        span.add(vev)
        vtz = span.createVTimeZone(tz)
        self.assertEqual(vtz['TZID'], "Pacific/Auckland")
        self._assertHasSegment(vtz, vtz.daylight, "NZDT",
                               dt.timedelta(hours=12), dt.timedelta(hours=13))
        self._assertHasSegment(vtz, vtz.standard, "NZST",
                               dt.timedelta(hours=13), dt.timedelta(hours=12))

# ------------------------------------------------------------------------------
class TestVMatch(TestCase):
    def testEmpty(self):
        match = VMatch()
        self.assertIs(match.parent, None)
        self.assertEqual(match.orphans, [])

    def testDuplicate(self):
        match = VMatch()
        vev1 = SimpleVEvent()
        addProps(vev1, summary = "Event1", uid = "1234",
                 dtstart = dt.datetime(2016, 4, 5, 9),
                 dtend   = dt.datetime(2016, 4, 5, 13))
        match.add(vev1)
        vev2 = SimpleVEvent()
        addProps(vev2, summary = "Event2", uid = "1234",
                 dtstart = dt.datetime(2016, 4, 5, 9),
                 dtend   = dt.datetime(2016, 4, 5, 13))
        with self.assertRaises(VMatch.DuplicateError):
            match.add(vev2)

# ------------------------------------------------------------------------------
class TestVEventFactory(TestCase):
    def setUp(self):
        self.factory = VEventFactory()

    def testMissingUid(self):
        props = Event()
        addProps(props, summary = "Event",
                 dtstart = dt.datetime(2016, 4, 5, 9),
                 dtend   = dt.datetime(2016, 4, 5, 13))
        with self.assertRaises(CalendarTypeError) as expected:
            self.factory.makeFromProps(props, None)
        self.assertEqual(str(expected.exception), "Missing UID")

    def testMissingDtstamp(self):
        props = Event()
        addProps(props, summary = "Event", uid = "1234",
                 dtstart = dt.datetime(2016, 4, 5, 9),
                 dtend   = dt.datetime(2016, 4, 5, 13))
        with self.assertRaises(CalendarTypeError) as expected:
            self.factory.makeFromProps(props, None)
        self.assertEqual(str(expected.exception), "Missing DTSTAMP")

    def testMissingDtstart(self):
        props = Event()
        addProps(props, summary = "Event", uid = "1234",
                 dtend   = dt.datetime(2016, 4, 5, 13),
                 dtstamp = dt.datetime(2016, 4, 5, 13))
        with self.assertRaises(CalendarTypeError) as expected:
            self.factory.makeFromProps(props, None)
        self.assertEqual(str(expected.exception), "Missing DTSTART")

    def testDtendAndDuration(self):
        props = Event()
        addProps(props, summary = "Event", uid = "1234",
                 dtstart  = dt.datetime(2016, 4, 5, 9),
                 dtend    = dt.datetime(2016, 4, 5, 13),
                 dtstamp  = dt.datetime(2016, 4, 5, 13),
                 duration = dt.timedelta(2))
        with self.assertRaises(CalendarTypeError) as expected:
            self.factory.makeFromProps(props, None)
        self.assertEqual(str(expected.exception), "Both DURATION and DTEND set")

    def testDtstartDtendTypes(self):
        props = Event()
        addProps(props, summary = "Event", uid = "1234",
                 dtstart  = dt.datetime(2016, 4, 5, 9),
                 dtend    = dt.date(2016, 4, 5),
                 dtstamp  = dt.datetime(2016, 4, 5, 13))
        with self.assertRaises(CalendarTypeError) as expected:
            self.factory.makeFromProps(props, None)
        self.assertEqual(str(expected.exception), "DTSTART and DTEND types do not match")

    def testDiffTZsDtstartDtEnd(self):
        tz1 = pytz.timezone("Pacific/Auckland")
        tz2 = pytz.timezone("Australia/Sydney")
        props = Event()
        addProps(props, summary = "Event", uid = "1234",
                 dtstart  = timezone.make_aware(dt.datetime(2016, 6, 1, 7), tz1),
                 dtend    = timezone.make_aware(dt.datetime(2016, 6, 1, 8), tz2),
                 dtstamp  = timezone.make_aware(dt.datetime(2016, 6, 1, 8), tz2))
        with self.assertRaises(CalendarTypeError) as expected:
            self.factory.makeFromProps(props, None)
        self.assertEqual(str(expected.exception), "DTSTART.timezone != DTEND.timezone")

    def testMultipleRRules(self):
        props = Event()
        addProps(props, summary = "Event", uid = "1234",
                 dtstart  = dt.datetime(2016, 4, 5, 9),
                 dtend    = dt.datetime(2016, 4, 5, 13),
                 dtstamp  = dt.datetime(2016, 4, 5, 13),
                 rrule   = vRecur.from_ical("FREQ=WEEKLY;WKST=SU;BYDAY=MO,TU,WE,TH,FR"))
        props.add('rrule', vRecur.from_ical("FREQ=MONTHLY;WKST=SU;BYDAY=-1SA,-1SU"))
        with self.assertRaises(CalendarTypeError) as expected:
            self.factory.makeFromProps(props, None)
        self.assertEqual(str(expected.exception), "Multiple RRULEs")

    def testDiffTZsDtstartRecurrenceId(self):
        tz1 = pytz.timezone("Pacific/Auckland")
        tz2 = pytz.timezone("Australia/Sydney")
        props = Event()
        addProps(props, summary = "Event", uid = "1234",
                 dtstart  = timezone.make_aware(dt.datetime(2016, 6, 1, 7), tz1),
                 dtend    = timezone.make_aware(dt.datetime(2016, 6, 1, 10), tz1),
                 dtstamp  = timezone.make_aware(dt.datetime(2016, 6, 1, 8), tz2))
        props.add('RECURRENCE-ID', timezone.make_aware(dt.datetime(2016, 6, 1, 8), tz2))
        with self.assertRaises(CalendarTypeError) as expected:
            self.factory.makeFromProps(props, None)
        self.assertEqual(str(expected.exception),
                         "DTSTART.timezone != RECURRENCE-ID.timezone")

    def testWholeDayEvent(self):
        props = Event(summary = "Event", uid = "1234")
        props.add('dtstart', dt.date(2017, 6, 5))
        props.add('dtend',   dt.date(2017, 6, 6))
        props.add('dtstamp', vDt(timezone.make_aware(dt.datetime(2016, 6, 7, 8))))
        vev = self.factory.makeFromProps(props, None)
        self.assertIs(type(vev), SimpleVEvent)

    def test1hrDuration(self):
        props = Event()
        addProps(props, summary = "Event", uid = "1234",
                 dtstart  = timezone.make_aware(dt.datetime(2016, 6, 1, 7)),
                 duration = dt.timedelta(hours=1),
                 dtstamp  = timezone.make_aware(dt.datetime(2016, 6, 1, 8)))
        vev = self.factory.makeFromProps(props, None)
        self.assertIs(type(vev), SimpleVEvent)
        self.assertEqual(vev['DTSTART'], timezone.make_aware(dt.datetime(2016, 6, 1, 7)))
        self.assertEqual(vev['DTEND'],   timezone.make_aware(dt.datetime(2016, 6, 1, 8)))

    def testNoDuration(self):
        props = Event()
        addProps(props, summary = "Event", uid = "1234",
                 dtstart  = dt.date(2016, 6, 1),
                 dtstamp  = timezone.make_aware(dt.datetime(2016, 6, 1, 8)))
        vev = self.factory.makeFromProps(props, None)
        self.assertIs(type(vev), SimpleVEvent)
        self.assertEqual(vev['DTSTART'], dt.date(2016, 6, 1))
        self.assertEqual(vev['DTEND'],   dt.date(2016, 6, 2))

    def testUnsupportedPageType(self):
        page = Page(title = "Event", slug = "event")
        with self.assertRaises(CalendarTypeError) as expected:
            vev = self.factory.makeFromPage(page, None)
        self.assertEqual(str(expected.exception), "Unsupported page type")

# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
