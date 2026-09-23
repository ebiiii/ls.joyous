# ------------------------------------------------------------------------------
# Test Edit Handlers
# ------------------------------------------------------------------------------
import sys
import datetime as dt
from unittest import skipUnless
from django.test import RequestFactory, TestCase, override_settings
from django.conf import settings
from django.contrib.auth.models import User
from django.utils import timezone
from django.utils.formats import get_format
from wagtail.admin.panels.model_utils import get_edit_handler
from wagtail.admin.widgets import AdminTimeInput, AdminDateInput
from wagtail.models import Site, Page
from ls.joyous.models.recurring_events import HiddenNumDaysPanel
from ls.joyous.models import (CalendarPage, CancellationPage,
        RecurringEventPage, MultidayRecurringEventPage)
from ls.joyous.utils.recurrence import Recurrence, MONTHLY, YEARLY, TU, FR
from ls.joyous.edit_handlers import ExceptionDatePanel, ConcealedPanel
from ls.joyous.widgets import Time12hrInput, ExceptionDateInput
from .testutils import datetimetz, freeze_timetz, getPage
import ls.joyous.edit_handlers
import importlib
from wagtail import VERSION as _wt_version
WagtailVersion = _wt_version[:3]

def bindPanel(panel, instance=None, request=None, form=None):
    """
    Modern Wagtail panels bind in two steps: bind_to_model then
    get_bound_panel, rather than the old incremental bind_to() calls.
    """
    model = type(instance) if instance is not None else None
    return panel.bind_to_model(model).get_bound_panel(
        instance=instance, request=request, form=form)

# ------------------------------------------------------------------------------
class TestExceptionDatePanel(TestCase):
    def setUp(self):
        self.home = getPage("/home/")
        self.user = User.objects.create_superuser('i', 'i@joy.test', 's3(r3t')
        self.calendar = CalendarPage(owner = self.user,
                                     slug  = "events",
                                     title = "Events")
        self.home.add_child(instance=self.calendar)
        self.calendar.save_revision().publish()
        self.event = RecurringEventPage(slug      = "leaders-meeting",
                                        title     = "Leaders' Meeting",
                                        repeat    = Recurrence(dtstart=dt.date(2016,2,16),
                                                               freq=MONTHLY,
                                                               byweekday=[TU(3)]),
                                        time_from = dt.time(19),
                                        tz        = "Asia/Tokyo")
        self.calendar.add_child(instance=self.event)
        self.event.save_revision().publish()

    def _getRequest(self):
        request = RequestFactory().get("/test")
        request.user = self.user
        request.session = {}
        request.site = Site.objects.get(is_default_site=True)
        return request

    def testWidget(self):
        self.assertIs(ExceptionDatePanel.widget, ExceptionDateInput)

    @skipUnless(WagtailVersion >= (2, 5, 0), "Wagtail <2.5")
    def testBindWithoutForm25(self):
        cancellation = CancellationPage(owner = self.user,
                                        except_date = dt.date(2019,1,21))
        panel = ExceptionDatePanel('except_date', classname='full-width')
        panel = bindPanel(panel, instance=cancellation)
        self.assertIsNone(panel.form)

    @skipUnless(WagtailVersion >= (2, 5, 0), "Wagtail <2.5")
    def testBindWithoutOverrides25(self):
        cancellation = CancellationPage(owner = self.user,
                                        except_date = dt.date(2019,1,21))
        Form = get_edit_handler(CancellationPage).get_form_class()
        form = Form(instance=cancellation, parent_page=self.event)
        panel = ExceptionDatePanel('except_date', classname='full-width')
        panel = bindPanel(panel, instance=cancellation,
                          request=self._getRequest(), form=form)
        self.assertIsNotNone(panel.form)
        self.assertIsNone(panel.instance.overrides)

    @skipUnless(WagtailVersion >= (2, 5, 0), "Wagtail <2.5")
    def testBindOverridesRepeat25(self):
        cancellation = CancellationPage(owner = self.user,
                                        overrides = self.event,
                                        except_date = dt.date(2019,1,21))
        Form = get_edit_handler(CancellationPage).get_form_class()
        form = Form(instance=cancellation, parent_page=self.event)
        widget = form['except_date'].field.widget
        panel = ExceptionDatePanel('except_date', classname='full-width')
        panel = bindPanel(panel, instance=cancellation,
                          request=self._getRequest(), form=form)
        self.assertIs(widget.overrides_repeat, self.event.repeat)
        self.assertIsNone(panel.exceptionTZ)

    @skipUnless(WagtailVersion >= (2, 5, 0), "Wagtail <2.5")
    @timezone.override("America/Los_Angeles")
    def testBindExceptionTZ25(self):
        cancellation = CancellationPage(owner = self.user,
                                        overrides = self.event,
                                        except_date = dt.date(2019,1,21))
        Form = get_edit_handler(CancellationPage).get_form_class()
        form = Form(instance=cancellation, parent_page=self.event)
        panel = ExceptionDatePanel('except_date', classname='full-width')
        panel = bindPanel(panel, instance=cancellation,
                          request=self._getRequest(), form=form)
        self.assertEqual(panel.exceptionTZ, "Asia/Tokyo")

# ------------------------------------------------------------------------------
@override_settings(JOYOUS_TIME_INPUT=12)
class TestTime12hrPanel(TestCase):
    def testWidget(self):
        importlib.reload(ls.joyous.edit_handlers)
        from ls.joyous.edit_handlers import TimePanel
        self.assertIs(TimePanel.widget, Time12hrInput)

    def testDefaultTimeInput(self):
        importlib.reload(ls.joyous.edit_handlers)
        self.assertIn('%I:%M%p', settings.TIME_INPUT_FORMATS)
        self.assertIn('%I%p', settings.TIME_INPUT_FORMATS)

    @override_settings(LANGUAGE_CODE="en-nz")
    def testNZLocaleTimeInput(self):
        importlib.reload(ls.joyous.edit_handlers)
        format = get_format('TIME_INPUT_FORMATS')
        self.assertIn('%I:%M%p', format)
        self.assertIn('%I%p', format)


# ------------------------------------------------------------------------------
class TestConcealedPanel(TestCase):
    def setUp(self):
        self.home = getPage("/home/")
        self.user = User.objects.create_superuser('i', 'i@joy.test', 's3(r3t')
        self.calendar = CalendarPage(owner = self.user,
                                     slug  = "events",
                                     title = "Events")
        self.home.add_child(instance=self.calendar)
        self.calendar.save_revision().publish()
        self.event = RecurringEventPage(slug      = "leaders-meeting",
                                        title     = "Leaders' Meeting",
                                        repeat    = Recurrence(dtstart=dt.date(2016,2,16),
                                                               freq=MONTHLY,
                                                               byweekday=[TU(3)]),
                                        time_from = dt.time(19),
                                        tz        = "Asia/Tokyo")
        self.calendar.add_child(instance=self.event)
        self.event.save_revision().publish()

    def _getRequest(self):
        request = RequestFactory().get("/test")
        request.user = self.user
        request.session = {}
        request.site = Site.objects.get(is_default_site=True)
        return request

    def testInit(self):
        panel = ConcealedPanel([], "Test", help_text="Nothing")
        self.assertEqual(panel._heading, "Test")
        self.assertEqual(panel._help_text, "Nothing")
        self.assertEqual(panel.heading, "")
        self.assertEqual(panel.help_text, "")

    @skipUnless(WagtailVersion >= (2, 5, 0), "Wagtail <2.5")
    def testConcealed25(self):
        panel = ConcealedPanel([], "Test")
        panel = bindPanel(panel, instance=self.event, request=self._getRequest())
        self.assertFalse(panel.is_shown())
        self.assertEqual(panel.heading, "")
        self.assertEqual(panel.help_text, "")

    @skipUnless(WagtailVersion >= (2, 5, 0), "Wagtail <2.5")
    def testShown25(self):
        class ShownPanel(ConcealedPanel):
            def _show(self, bound_panel):
                return True

        panel = ShownPanel([], "Test", help_text="Nothing")
        panel = bindPanel(panel, instance=self.event, request=self._getRequest())
        self.assertTrue(panel.is_shown())
        content = panel.render_html()
        self.assertIn("Nothing", content)
        self.assertEqual(panel.heading, "Test")
        self.assertEqual(panel.help_text, "Nothing")

# ------------------------------------------------------------------------------
class TestHiddenNumDaysPanel(TestCase):
    FIELDSET_CONTENT = """
<fieldset>
  <legend>Number of days</legend>
  <ul class="fields">
    <li>
      <div class="field integer_field number_input ">
        <div class="field-content">
          <div class="input  ">
            <input type="number" name="num_days" value="1" required id="id_num_days">
            <span></span>
          </div>
        </div>
      </div>
    </li>
  </ul>
</fieldset>
"""
    COMMENT_CONTROL_CONTENT = """
<div class="field-comment-control field-comment-control--object">
  <button aria-label="Add comment" class="u-hidden" data-comment-add data-component="add-comment-button" type="button">
    <svg aria-hidden="true" class="icon icon-comment-add icon-default initial" focusable="false">
      <use href="#icon-comment-add">
    </svg>
    <svg aria-hidden="true" class="icon icon-comment-add icon-reversed initial" focusable="false">
      <use href="#icon-comment-add-reversed">
    </svg>
  </button>
</div>
"""

    def setUp(self):
        if WagtailVersion > (2, 13, 0):
            self.FIELD_CONTENT = """
<div data-contentpath="num_days">
    {}
    {}
</div>
""".format(self.FIELDSET_CONTENT, self.COMMENT_CONTROL_CONTENT)
        else:
            self.FIELD_CONTENT = self.FIELDSET_CONTENT
        self.maxDiff = None
        self.home = getPage("/home/")
        self.user = User.objects.create_superuser('i', 'i@joy.test', 's3(r3t')
        self.calendar = CalendarPage(owner = self.user,
                                     slug  = "events",
                                     title = "Events")
        self.home.add_child(instance=self.calendar)
        self.calendar.save_revision().publish()
        self.event = RecurringEventPage(slug      = "leaders-meeting",
                                        title     = "Leaders' Meeting",
                                        repeat    = Recurrence(dtstart=dt.date(2016,2,16),
                                                               freq=MONTHLY,
                                                               byweekday=[TU(3)]),
                                        time_from = dt.time(19),
                                        tz        = "Asia/Tokyo")
        self.calendar.add_child(instance=self.event)
        self.event.save_revision().publish()
        Form = get_edit_handler(RecurringEventPage).get_form_class()
        self.form = Form(instance=self.event, parent_page=self.calendar)

    def _getRequest(self):
        request = RequestFactory().get("/test")
        request.user = self.user
        request.session = {}
        request.site = Site.objects.get(is_default_site=True)
        return request

    def testHidden(self):
        panel = HiddenNumDaysPanel()
        panel = bindPanel(panel, instance=self.event,
                          request=self._getRequest(), form=self.form)
        self.assertFalse(panel.is_shown())

    def testShowWith2Days(self):
        self.event.num_days = 2
        Form = get_edit_handler(RecurringEventPage).get_form_class()
        form = Form(instance=self.event, parent_page=self.calendar)
        panel = HiddenNumDaysPanel()
        panel = bindPanel(panel, instance=self.event,
                          request=self._getRequest(), form=form)
        self.assertTrue(panel.is_shown())
        content = panel.render_html()
        self.assertIn('name="num_days"', content)
        self.assertIn('value="2"', content)

    def testShowMulidayRecurringEvent(self):
        event = MultidayRecurringEventPage(slug      = "leaders-retreat",
                                           title     = "Leaders' Retreet",
                                           repeat    = Recurrence(dtstart=dt.date(2016,2,16),
                                                                  freq=YEARLY,
                                                                  bymonth=3,
                                                                  byweekday=[FR(1)]),
                                           time_from = dt.time(19),
                                           num_days  = 3,
                                           tz        = "Asia/Tokyo")
        self.calendar.add_child(instance=event)
        event.save_revision().publish()
        Form = get_edit_handler(MultidayRecurringEventPage).get_form_class()
        form = Form(instance=event, parent_page=self.calendar)
        panel = HiddenNumDaysPanel()
        panel = bindPanel(panel, instance=event,
                          request=self._getRequest(), form=form)
        self.assertTrue(panel.is_shown())
        content = panel.render_html()
        self.assertIn('name="num_days"', content)
        self.assertIn('value="3"', content)

# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
