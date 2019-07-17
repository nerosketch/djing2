from datetime import timedelta, datetime
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.db import models
from django.conf import settings
from customers.models import Customer
from tasks.handle import handle as task_handle


TASK_PRIORITIES = (
    (0, _('Low')),
    (1, _('Average')),
    (2, _('Higher'))
)

TASK_STATES = (
    (0, _('New')),
    (1, _('Confused')),
    (2, _('Completed'))
)

TASK_TYPES = (
    (0, _('not chosen')),
    (1, _('ip conflict')),
    (2, _('yellow triangle')),
    (3, _('red cross')),
    (4, _('weak speed')),
    (5, _('cable break')),
    (6, _('connection')),
    (7, _('periodic disappearance')),
    (8, _('router setup')),
    (9, _('configure onu')),
    (10, _('crimp cable')),
    (11, _('Internet crash')),
    (12, _('other'))
)


class ChangeLog(models.Model):
    task = models.ForeignKey('Task', on_delete=models.CASCADE)
    ACT_CHOICES = (
        (1, _('Change task')),
        (2, _('Create task')),
        (3, _('Delete task')),
        (4, _('Completing tasks')),
        (5, _('The task failed'))
    )
    act_type = models.PositiveSmallIntegerField(choices=ACT_CHOICES)
    when = models.DateTimeField(auto_now_add=True)
    who = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE, related_name='+'
    )

    def __str__(self):
        return self.get_act_type_display()

    class Meta:
        db_table = 'task_change_log'
        verbose_name = _('Change log')
        verbose_name_plural = _('Change logs')
        ordering = ('-when',)


def delta_add_days():
    return timezone.now() + timedelta(days=3)


class Task(models.Model):
    descr = models.CharField(
        _('Description'), max_length=128,
        null=True, blank=True
    )
    recipients = models.ManyToManyField(
        settings.AUTH_USER_MODEL, verbose_name=_('Recipients'),
        related_name='them_task'
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, related_name='+',
        on_delete=models.SET_NULL, null=True,
        blank=True, verbose_name=_('Task author')
    )
    priority = models.PositiveSmallIntegerField(
        _('A priority'),
        choices=TASK_PRIORITIES, default=0
    )
    out_date = models.DateField(
        _('Reality'), null=True,
        blank=True, default=delta_add_days
    )
    time_of_create = models.DateTimeField(
        _('Date of create'), auto_now_add=True
    )
    state = models.PositiveSmallIntegerField(
        _('Condition'), choices=TASK_STATES,
        default=0
    )
    mode = models.PositiveSmallIntegerField(
        _('The nature of the damage'),
        choices=TASK_TYPES, default=0
    )
    customer = models.ForeignKey(
        Customer, on_delete=models.CASCADE,
        verbose_name=_('Customer')
    )

    def finish(self, current_user):
        self.state = 2  # Completed. Task done
        self.out_date = timezone.now()  # End time
        ChangeLog.objects.create(
            task=self,
            act_type=4,  # Completing tasks
            who=current_user
        )
        self.save(update_fields=('state', 'out_date'))

    def do_fail(self, current_user):
        self.state = 1  # Confused(crashed)
        ChangeLog.objects.create(
            task=self,
            act_type=5,  # The task failed
            who=current_user
        )
        self.save(update_fields=('state',))

    def send_notification(self):
        task_handle(
           self, self.author,
           self.recipients.filter(is_active=True)
        )

    def is_relevant(self):
        return self.out_date < timezone.now().date() or self.state == 2

    def get_time_diff(self):
        now_date = datetime.now().date()
        if not self.out_date:
            return _('Out date not specified')
        if self.out_date > now_date:
            time_diff = "%s: %s" % (_('time left'), (self.out_date - now_date))
        else:
            time_diff = _("Expired timeout -%(time_left)s") % {
                'time_left': (now_date - self.out_date)
            }
        return time_diff

    class Meta:
        db_table = 'task'
        ordering = ('-id',)
        permissions = (
            ('can_viewall', _('Access to all tasks')),
            ('can_remind', _('Reminders of tasks'))
        )


class ExtraComment(models.Model):
    text = models.TextField(_('Text of comment'))
    task = models.ForeignKey(
        Task, verbose_name=_('Task'),
        on_delete=models.CASCADE
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name=_('Author'),
        on_delete=models.CASCADE
    )
    date_create = models.DateTimeField(_('Time of create'), auto_now_add=True)

    def __str__(self):
        return self.text

    class Meta:
        db_table = 'task_extra_comments'
        verbose_name = _('Extra comment')
        verbose_name_plural = _('Extra comments')
        ordering = ('-date_create',)
