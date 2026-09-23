# ------------------------------------------------------------------------------
# Wagtail 3.x+ style Panels
# ------------------------------------------------------------------------------
from django.conf import settings
from django.utils import timezone
from django.utils.formats import get_format_modules
from wagtail.admin.panels import (FieldPanel, MultiFieldPanel)
from wagtail.admin.widgets import AdminDateInput, AdminTimeInput
try:
    from wagtail.admin.localization import get_available_admin_languages
except ImportError:        # pragma: no cover
    from wagtail.admin.utils import get_available_admin_languages
from .widgets import ExceptionDateInput, Time12hrInput


# ------------------------------------------------------------------------------
class TZDatePanel(FieldPanel):
    """
    Will display the timezone of the date if it is not the current TZ
    """
    widget = AdminDateInput

    def __init__(self, *args, **kwargs):
        # FieldPanel.__init__ always sets self.widget from its widget=
        # argument (defaulting to None), so the class-level widget above
        # has to be forwarded explicitly here for subclasses to keep it.
        kwargs.setdefault('widget', self.widget)
        super().__init__(*args, **kwargs)

    class BoundPanel(FieldPanel.BoundPanel):
        template_name = "joyous/edit_handlers/tz_date_field.html"

        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            self.exceptionTZ = None
            if self.form is None:
                # wait for the form to be set, it will eventually be
                return
            localTZ = timezone.get_current_timezone()
            localTZName = timezone._get_timezone_name(localTZ)
            myTZ = getattr(self.instance, "tz", localTZ)
            myTZName = timezone._get_timezone_name(myTZ)
            if myTZName != localTZName:
                self.exceptionTZ = myTZName

# ------------------------------------------------------------------------------
class ExceptionDatePanel(TZDatePanel):
    """
    Used to select from the dates of the recurrence
    """
    widget = ExceptionDateInput

    class BoundPanel(TZDatePanel.BoundPanel):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            if self.form is None:
                # wait for the form to be set, it will eventually be
                return
            if not self.instance.overrides:
                return
            widget = self.form[self.field_name].field.widget
            widget.overrides_repeat = self.instance.overrides_repeat

# ------------------------------------------------------------------------------
def _add12hrFormats():
    # Time12hrInput will not work unless django.forms.fields.TimeField
    # can process 12hr times, so sneak them into the default and all the
    # selectable locales that define TIME_INPUT_FORMATS.

    # strptime does not accept %P, %p is for both cases here.
    _12hrFormats = ['%I:%M%p', # 2:30pm
                    '%I%p']    # 7am

    # TIME_INPUT_FORMATS is defined in django.conf.global_settings if not
    # by the user's local settings.
    if (_12hrFormats[0] not in settings.TIME_INPUT_FORMATS or
        _12hrFormats[1] not in settings.TIME_INPUT_FORMATS):
        settings.TIME_INPUT_FORMATS += _12hrFormats

    # Many of the built-in locales define TIME_INPUT_FORMATS
    langCodes = [language[0] for language in get_available_admin_languages()]
    langCodes.append(settings.LANGUAGE_CODE)
    for lang in langCodes:
        for module in get_format_modules(lang):
            inputFormats = getattr(module, 'TIME_INPUT_FORMATS', None)
            if (inputFormats is not None and
                (_12hrFormats[0] not in inputFormats or
                 _12hrFormats[1] not in inputFormats)):
                inputFormats += _12hrFormats

# ------------------------------------------------------------------------------
class TimePanel(FieldPanel):
    """
    Used to select time using either a 12 or 24 hour time widget
    """
    if getattr(settings, "JOYOUS_TIME_INPUT", "24") in (12, "12"):
        widget = Time12hrInput
        _add12hrFormats()
    else:
        widget = AdminTimeInput

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('widget', self.widget)
        super().__init__(*args, **kwargs)

# ------------------------------------------------------------------------------
try:
    # Use wagtailgmaps for location if it is installed
    # but don't depend upon it
    settings.INSTALLED_APPS.index('wagtailgmaps')
    from wagtailgmaps.panels import MapFieldPanel
    MapFieldPanel.UsingWagtailGMaps = True
except (ValueError, ImportError):       # pragma: no cover
    MapFieldPanel = FieldPanel

# ------------------------------------------------------------------------------
class ConcealedPanel(MultiFieldPanel):
    """
    A panel that can be hidden.  Subclasses should override _show(bound_panel)
    to decide whether the panel is visible for that request/instance, e.g.

        class Panel(ConcealedPanel):
            def _show(self, bound_panel):
                return bound_panel.instance.some_condition
    """
    def __init__(self, children, heading, classname='', help_text=''):
        super().__init__(children, '', classname, '')
        self._heading   = heading
        self._help_text = help_text

    def clone_kwargs(self):
        return dict(children=self.children,
                    heading=self._heading,
                    classname=self.classname,
                    help_text=self._help_text)

    def _show(self, bound_panel):
        return False

    class BoundPanel(MultiFieldPanel.BoundPanel):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            if self.panel._show(self):
                self.heading   = self.panel._heading
                self.help_text = self.panel._help_text

        def is_shown(self):
            return self.panel._show(self)

# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
