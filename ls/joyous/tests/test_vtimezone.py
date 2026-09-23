# ------------------------------------------------------------------------------
# vtimezone functions copied from https://github.com/pimutils/khal
# ------------------------------------------------------------------------------
import datetime as dt
import pytz
from ls.joyous.formats.vtimezone import create_timezone
from django.test import TestCase


# ------------------------------------------------------------------------------
class TestVDt(TestCase):
    def setUp(self):
        self.berlin = pytz.timezone('Europe/Berlin')
        self.bogota = pytz.timezone('America/Bogota')

    def testBerlin(self):
        atime = dt.datetime(2014, 10, 28, 10, 10)
        vberlin = create_timezone(self.berlin, atime, atime)
        self.assertEqual(str(vberlin['TZID']), 'Europe/Berlin')
        std = vberlin.standard[0]
        self.assertEqual(str(std['TZNAME']), 'CET')
        self.assertEqual(std['TZOFFSETFROM'].td, dt.timedelta(hours=2))
        self.assertEqual(std['TZOFFSETTO'].td, dt.timedelta(hours=1))

    def testBerlinRdate(self):
        atime = dt.datetime(2014, 10, 28, 10, 10)
        btime = dt.datetime(2016, 10, 28, 10, 10)
        vberlin = create_timezone(self.berlin, atime, btime)
        self.assertEqual(str(vberlin['TZID']), 'Europe/Berlin')
        stdNames = {str(std['TZNAME']) for std in vberlin.standard}
        dstNames = {str(dst['TZNAME']) for dst in vberlin.daylight}
        self.assertEqual(stdNames, {'CET'})
        self.assertEqual(dstNames, {'CEST'})
        for std in vberlin.standard:
            self.assertEqual(std['TZOFFSETTO'].td, dt.timedelta(hours=1))
        for dst in vberlin.daylight:
            self.assertEqual(dst['TZOFFSETTO'].td, dt.timedelta(hours=2))

    def testBogota(self):
        atime = dt.datetime(2014, 10, 28, 10, 10)
        vbogota = create_timezone(self.bogota, atime, atime)
        self.assertEqual(str(vbogota['TZID']), 'America/Bogota')
        std = vbogota.standard[0]
        self.assertEqual(std['TZOFFSETTO'].td, dt.timedelta(hours=-5))

    def testPST(self):
        pst = pytz.timezone('Etc/GMT-8')
        atime = dt.datetime(2014, 10, 28, 10, 10)
        btime = dt.datetime(2016, 10, 28, 10, 10)
        vtz = create_timezone(pst, atime, btime)
        self.assertEqual(str(vtz['TZID']), 'Etc/GMT-8')
        std = vtz.standard[0]
        self.assertEqual(std['TZOFFSETFROM'].td, dt.timedelta(hours=8))
        self.assertEqual(std['TZOFFSETTO'].td,   dt.timedelta(hours=8))

# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
