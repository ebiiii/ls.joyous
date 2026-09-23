# ------------------------------------------------------------------------------
# Test Event Base
# ------------------------------------------------------------------------------
import sys
import datetime as dt
import pytz
import calendar
from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone
from wagtail.models import Page, PageViewRestriction
from wagtail.admin.panels import ObjectList
from ls.joyous.models import (EventBase, removeContentPanels, SimpleEventPage,
            MultidayEventPage, RecurringEventPage, MultidayRecurringEventPage,
            PostponementPage, RescheduleMultidayEventPage)
from .testutils import datetimetz, freeze_timetz

# ------------------------------------------------------------------------------
class Test(TestCase):
    def testRemoveContentPanels(self):
        removeContentPanels(["tz", "location"])
        removeContentPanels("website")
        removed = ("tz", "location", "website")

        for cls in (SimpleEventPage, MultidayEventPage, RecurringEventPage,
                    MultidayRecurringEventPage, PostponementPage,
                    RescheduleMultidayEventPage):
            with self.subTest(classname = cls.__name__):
                fields = (ObjectList(cls.content_panels).bind_to_model(cls)
                          .get_form_options().get('fields', []))
                self.assertFalse(any(field in removed for field in fields))

# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
