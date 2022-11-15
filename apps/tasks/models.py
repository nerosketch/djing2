from datetime import timedelta, datetime, date
from types import GeneratorType
from typing import Optional

from django.contrib.sites.models import Site
from django.db import models, connection
from django.utils.translation import gettext_lazy as _

try:
    from customers.models import Customer
except ImportError as err:
    from django.core.exceptions import ImproperlyConfigured

    raise ImproperlyConfigured(
        '"tasks" application depends on "customers" application. Check if it installed'
    ) from err

from djing2.lib import safe_float, safe_int
from djing2.models import BaseAbstractModel
from profiles.models import UserProfile
from tasks.handle import handle as task_handle


class TaskStateChangeLogModelManager(models.Manager):
    def create_state_migration(self, task, author, old_data: dict, new_data: dict):
        changed_fields = [k for k, v in new_data.items() if old_data.get(k) is not None and v != old_data.get(k)]

        def _format_state_item(v):
            if issubclass(v.__class__, models.Model):
                return v.pk
            elif isinstance(v, (datetime, date)):
                return str(v)
            elif isinstance(v, (list, tuple, GeneratorType)):
                return tuple(map(_format_state_item, v))
            return v

        def _map_data(data) -> dict:
            return {k: _format_state_item(v) for k, v in data.items() if k in changed_fields}

        new_data = _map_data(new_data)
        old_data = _map_data(old_data)

        state_data = {k: {"from": v, "to": new_data.get(k)} for k, v in old_data.items()}
        return self.create(task=task, state_data=state_data, who=author)


class TaskStateChangeLogModel(BaseAbstractModel):
    task = models.ForeignKey("Task", on_delete=models.CASCADE)
    state_data = models.JSONField(_("State change data"))
    when = models.DateTimeField(auto_now_add=True)
    who = models.ForeignKey(
        UserProfile,
        on_delete=models.CASCADE,
        related_name="+"
    )

    objects = TaskStateChangeLogModelManager()

    def _human_log_text_general(self):
        text_tmpl = _("Task change.")
        text_item_tmpl = _('"%(field_name)s" from "%(from)s" -> "%(to)s"')

        def _format_item_text(field_name, field_value):
            field = self.task._meta.get_field(field_name)
            field_title = field.verbose_name
            field_from_val = field_value.get("from")
            field_to_val = field_value.get("to")
            if isinstance(field, models.ManyToManyField):
                # TODO: display UserProfile names instead of primary keys.
                pass
            elif hasattr(field, "choices"):
                try:
                    setattr(self.task, field_name, field_from_val)
                    field_from_val = self.task._get_FIELD_display(field)
                    setattr(self.task, field_name, field_to_val)
                    field_to_val = self.task._get_FIELD_display(field)
                except:
                    pass
            return text_item_tmpl % {"field_name": field_title, "from": field_from_val, "to": field_to_val}

        item_texts = (_format_item_text(*state_data_item) for state_data_item in self.state_data.items())

        return "{} {}".format(text_tmpl, "|".join(item_texts))

    def _human_log_text_state_change(self):
        task_state = self.state_data.get("task_state")
        state1 = task_state.get("from")
        state2 = task_state.get("to")
        if state1 == state2:
            return self._human_log_text_general()
        if state1 == TaskStates.TASK_STATE_NEW:
            if state2 == TaskStates.TASK_STATE_COMPLETED:
                return _("Completing task")
            elif state2 == TaskStates.TASK_STATE_CONFUSED:
                return _("Failing task")
        elif state1 == TaskStates.TASK_STATE_CONFUSED:
            if state2 == TaskStates.TASK_STATE_NEW:
                return _("Restore state from confused to new")
            elif state2 == TaskStates.TASK_STATE_COMPLETED:
                return _("Change state from confused to completed")
        elif state1 == TaskStates.TASK_STATE_COMPLETED:
            if state2 == TaskStates.TASK_STATE_NEW:
                return _("Restore state from completed to new")
            elif state2 == TaskStates.TASK_STATE_CONFUSED:
                return _("Change state from completed to confused")
        return _("Unknown change action")

    def human_log_text(self) -> Optional[str]:
        """Human-readable log representation."""
        dat = self.state_data
        if not dat:
            return None

        if len(dat.items()) > 1:
            return self._human_log_text_general()

        task_state = dat.get("task_state")
        if task_state is None:
            return self._human_log_text_general()

        return self._human_log_text_state_change()

    @property
    def who_name(self):
        if self.who:
            return self.who.get_full_name()
        return ''

    @property
    def human_representation(self):
        r = self.human_log_text()
        if r is None:
            return
        return str(r)

    class Meta:
        db_table = "task_state_change_log"
        verbose_name = _("Change log")
        verbose_name_plural = _("Change logs")


def delta_add_days():
    return datetime.now() + timedelta(days=3)


class TaskQuerySet(models.QuerySet):
    def task_mode_report(self):
        """
        Returns queryset with annotate how many
        tasks with each task mode was
        """
        return self.values("task_mode").annotate(task_count=models.Count("pk")).order_by("task_mode")

    @staticmethod
    def task_state_percent(task_state: int) -> tuple[int, float]:
        """
        Returns percent of specified task state
        :param task_state: int of task state
        :return: tuple(state_count: int, state_percent: float)
        """
        with connection.cursor() as c:
            c.execute(
                "SELECT count(id) as cnt, "
                "round(count(id) * 100.0 / (SELECT count(id) FROM task), 6) AS prc "
                "FROM task WHERE task_state=%s::int",
                [int(task_state)],
            )
            r = c.fetchone()
        state_count, state_percent = r
        return safe_int(state_count), safe_float(state_percent)


class TaskModeModel(models.Model):
    title = models.CharField(
        _('Title'),
        max_length=64,
    )

    def __str__(self):
        return self.title

    class Meta:
        db_table = 'task_modes'


class TaskPriorities(models.IntegerChoices):
    TASK_PRIORITY_LOW = 0, _('Low')
    TASK_PRIORITY_AVARAGE = 1, _('Average')
    TASK_PRIORITY_HIGHER = 2, _('Higher')


class TaskStates(models.IntegerChoices):
    TASK_STATE_NEW = 0, _('New')
    TASK_STATE_CONFUSED = 1, _('Confused')
    TASK_STATE_COMPLETED = 2, _('Completed')


class Task(BaseAbstractModel):
    descr = models.CharField(
        _("Description"),
        max_length=128, null=True, blank=True
    )
    recipients = models.ManyToManyField(
        UserProfile,
        verbose_name=_("Recipients"),
        related_name="them_task"
    )
    author = models.ForeignKey(
        UserProfile,
        related_name="+",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("Task author")
    )
    priority = models.PositiveSmallIntegerField(
        _("A priority"),
        choices=TaskPriorities.choices,
        default=TaskPriorities.TASK_PRIORITY_LOW
    )
    out_date = models.DateField(
        _("Reality"),
        null=True,
        blank=True,
        default=delta_add_days
    )
    time_of_create = models.DateTimeField(_("Date of create"), auto_now_add=True)
    task_state = models.PositiveSmallIntegerField(
        _("Condition"),
        choices=TaskStates.choices,
        default=TaskStates.TASK_STATE_NEW
    )
    task_mode = models.ForeignKey(
        to=TaskModeModel,
        verbose_name=_('Mode'),
        blank=True, null=True, default=None,
        on_delete=models.SET_DEFAULT
    )
    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        verbose_name=_("Customer")
    )
    site = models.ForeignKey(Site, blank=True, null=True, default=None, on_delete=models.CASCADE)

    objects = TaskQuerySet.as_manager()

    def finish(self, current_user):
        if self.task_state != TaskStates.TASK_STATE_COMPLETED:
            TaskStateChangeLogModel.objects.create_state_migration(
                task=self,
                author=current_user,
                new_data={"task_state": TaskStates.TASK_STATE_COMPLETED, "out_date": self.out_date},
                old_data={"task_state": int(self.task_state), "out_date": self.out_date},
            )
            self.task_state = TaskStates.TASK_STATE_COMPLETED  # Completed. Task done
            self.out_date = datetime.now().date()  # End time
            self.save(update_fields=("task_state", "out_date"))

    def do_fail(self, current_user):
        if self.task_state != TaskStates.TASK_STATE_CONFUSED:
            TaskStateChangeLogModel.objects.create_state_migration(
                task=self,
                author=current_user,
                new_data={"task_state": TaskStates.TASK_STATE_CONFUSED},
                old_data={"task_state": int(self.task_state)},
            )
            self.task_state = TaskStates.TASK_STATE_CONFUSED  # Confused(crashed)
            self.save(update_fields=("task_state",))

    def send_notification(self):
        task_handle(self, self.author, self.recipients.filter(is_active=True))

    @property
    def is_expired(self):
        if self.out_date:
            return self.out_date < datetime.now().date()
        return False

    def get_time_diff(self):
        now_date = datetime.now().date()
        if not self.out_date:
            return _("Out date not specified")
        if self.out_date > now_date:
            time_diff = "{}: {}".format(_("time left"), self.out_date - now_date)
        else:
            time_diff = _("Expired timeout -%(time_left)s") % {
                "time_left": (now_date - self.out_date)
            }
        return time_diff

    @property
    def author_full_name(self):
        if self.author_id:
            return self.author.get_full_name()
        return ''

    @property
    def author_uname(self):
        if self.author_id:
            return self.author.username
        return ''

    @property
    def priority_name(self):
        return self.get_priority_display()

    @property
    def time_diff(self):
        return str(self.get_time_diff())

    @property
    def customer_address(self):
        if self.customer_id:
            return self.customer.full_address
        return ''

    @property
    def customer_full_name(self):
        if self.customer_id:
            return self.customer.get_full_name()
        return ''

    @property
    def customer_uname(self):
        if self.customer_id:
            return self.customer.username
        return ''

    @property
    def customer_group(self) -> Optional[int]:
        if self.customer_id:
            return self.customer.group_id or None
        return None

    @property
    def state_str(self):
        return self.get_task_state_display()

    @property
    def mode_str(self):
        if self.task_mode:
            return self.task_mode.title
        return ''

    class Meta:
        db_table = "task"
        permissions = [
            ("can_remind", _("Reminders of tasks")),
            ("can_view_task_mode_report", _("Can view task mode report")),
            ("can_finish_task", _("Can finish tasks")),
            ("can_fail_task", _("Can mark task as failed")),
            ("can_view_reports", _("Can view reports")),
        ]


class ExtraComment(BaseAbstractModel):
    text = models.TextField(_("Text of comment"))
    task = models.ForeignKey(
        Task,
        verbose_name=_("Task"),
        on_delete=models.CASCADE
    )
    author = models.ForeignKey(
        UserProfile,
        verbose_name=_("Author"),
        on_delete=models.CASCADE
    )
    date_create = models.DateTimeField(
        _("Time of create"), auto_now_add=True
    )

    @property
    def author_name(self):
        if self.author:
            return self.author.get_full_name()
        return ''

    @property
    def author_avatar(self):
        if self.author:
            return self.author.get_avatar_url()
        return ''

    def __str__(self):
        return self.text

    class Meta:
        db_table = "task_extra_comments"
        verbose_name = _("Extra comment")
        verbose_name_plural = _("Extra comments")


class TaskDocumentAttachment(BaseAbstractModel):
    title = models.CharField(max_length=64)
    doc_file = models.FileField(upload_to="task_attachments/%Y/%m/", max_length=128)
    create_time = models.DateTimeField(auto_now_add=True)
    author = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    task = models.ForeignKey(Task, on_delete=models.CASCADE)

    def __str__(self):
        return self.title

    class Meta:
        db_table = "task_doc_attachments"


class TaskFinishDocumentModel(models.Model):
    code = models.CharField(
        _('Document code'),
        max_length=64,
    )
    act_num = models.CharField(
        _('Act num'),
        max_length=64,
        null=True,
        blank=True,
        default=None
    )
    author = models.ForeignKey(
        UserProfile,
        verbose_name=_("Author"),
        on_delete=models.CASCADE
    )
    task = models.OneToOneField(
        Task,
        verbose_name=_("Task"),
        on_delete=models.CASCADE
    )
    create_time = models.DateTimeField(_("Time of create"))
    finish_time = models.DateTimeField(_('Finish time'))
    cost = models.FloatField(_('Cost'))
    task_mode = models.ForeignKey(
        to=TaskModeModel,
        verbose_name=_('Mode'),
        blank=True, null=True, default=None,
        on_delete=models.SET_DEFAULT
    )
    recipients = models.ManyToManyField(
        UserProfile,
        verbose_name=_("Recipients"),
        related_name='finish_docs'
    )

    def __str__(self):
        return self.code

    class Meta:
        db_table = 'task_finish_docs'
