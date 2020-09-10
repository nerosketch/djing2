from datetime import timedelta, datetime
from django.utils.translation import gettext_lazy as _
from django.db import models
from customers.models import Customer
from profiles.models import UserProfile
from tasks.handle import handle as task_handle


class ChangeLog(models.Model):
    task = models.ForeignKey('Task', on_delete=models.CASCADE)
    ACT_TYPE_CHANGE_TASK = 1
    ACT_TYPE_CREATE_TASK = 2
    ACT_TYPE_DELETE_TASK = 3
    ACT_TYPE_COMPLETE_TASK = 4
    ACT_TYPE_FAILED_TASK = 5
    ACT_CHOICES = (
        (ACT_TYPE_CHANGE_TASK, _('Change task')),
        (ACT_TYPE_CREATE_TASK, _('Create task')),
        (ACT_TYPE_DELETE_TASK, _('Delete task')),
        (ACT_TYPE_COMPLETE_TASK, _('Completing tasks')),
        (ACT_TYPE_FAILED_TASK, _('The task failed'))
    )
    act_type = models.PositiveSmallIntegerField(choices=ACT_CHOICES)
    when = models.DateTimeField(auto_now_add=True)
    who = models.ForeignKey(
        UserProfile,
        on_delete=models.CASCADE, related_name='+'
    )

    def __str__(self):
        return self.get_act_type_display()

    class Meta:
        db_table = 'task_change_log'
        verbose_name = _('Change log')
        verbose_name_plural = _('Change logs')
        ordering = '-when',


def delta_add_days():
    return datetime.now() + timedelta(days=3)


class Task(models.Model):
    descr = models.CharField(
        _('Description'), max_length=128,
        null=True, blank=True
    )
    recipients = models.ManyToManyField(
        UserProfile, verbose_name=_('Recipients'),
        related_name='them_task'
    )
    author = models.ForeignKey(
        UserProfile, related_name='+',
        on_delete=models.SET_NULL, null=True,
        blank=True, verbose_name=_('Task author')
    )
    TASK_PRIORITY_LOW = 0
    TASK_PRIORITY_AVARAGE = 1
    TASK_PRIORITY_HIGHER = 2
    TASK_PRIORITIES = (
        (TASK_PRIORITY_LOW, _('Low')),
        (TASK_PRIORITY_AVARAGE, _('Average')),
        (TASK_PRIORITY_HIGHER, _('Higher'))
    )
    priority = models.PositiveSmallIntegerField(
        _('A priority'),
        choices=TASK_PRIORITIES, default=TASK_PRIORITY_LOW
    )
    out_date = models.DateField(
        _('Reality'), null=True,
        blank=True, default=delta_add_days
    )
    time_of_create = models.DateTimeField(
        _('Date of create'), auto_now_add=True
    )
    TASK_STATE_NEW = 0
    TASK_STATE_CONFUSED = 1
    TASK_STATE_COMPLETED = 2
    TASK_STATES = (
        (TASK_STATE_NEW, _('New')),
        (TASK_STATE_CONFUSED, _('Confused')),
        (TASK_STATE_COMPLETED, _('Completed'))
    )
    task_state = models.PositiveSmallIntegerField(
        _('Condition'), choices=TASK_STATES,
        default=TASK_STATE_NEW
    )
    TASK_TYPE_NOT_CHOSEN = 0
    TASK_TYPE_IP_CONFLICT = 1
    TASK_TYPE_YELLOW_TRIANGLE = 2
    TASK_TYPE_RED_CROSS = 3
    TASK_TYPE_WAEK_SPEED = 4
    TASK_TYPE_CABLE_BREAK = 5
    TASK_TYPE_CONNECTION = 6
    TASK_TYPE_PERIODIC_DISAPPEARANCE = 7
    TASK_TYPE_ROUTER_SETUP = 8
    TASK_TYPE_CONFIGURE_ONU = 9
    TASK_TYPE_CRIMP_CABLE = 10
    TASK_TYPE_INTERNET_CRASH = 11
    TASK_TYPE_OTHER = 12
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
    mode = models.PositiveSmallIntegerField(
        _('The nature of the damage'),
        choices=TASK_TYPES, default=TASK_TYPE_NOT_CHOSEN
    )
    customer = models.ForeignKey(
        Customer, on_delete=models.CASCADE,
        verbose_name=_('Customer')
    )

    def finish(self, current_user):
        self.task_state = self.TASK_STATE_COMPLETED  # Completed. Task done
        self.out_date = datetime.now()  # End time
        ChangeLog.objects.create(
            task=self,
            act_type=ChangeLog.ACT_TYPE_COMPLETE_TASK,  # Completing tasks
            who=current_user
        )
        self.save(update_fields=('task_state', 'out_date'))

    def do_fail(self, current_user):
        self.task_state = self.TASK_STATE_CONFUSED  # Confused(crashed)
        ChangeLog.objects.create(
            task=self,
            act_type=ChangeLog.ACT_TYPE_FAILED_TASK,  # The task failed
            who=current_user
        )
        self.save(update_fields=('task_state',))

    def send_notification(self):
        task_handle(
           self, self.author,
           self.recipients.filter(is_active=True)
        )

    def is_expired(self):
        if self.out_date:
            return self.out_date < datetime.now().date()
        return False

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
        ordering = '-id',
        permissions = [
            ('can_viewall', _('Access to all tasks')),
            ('can_remind', _('Reminders of tasks'))
        ]


class ExtraComment(models.Model):
    text = models.TextField(_('Text of comment'))
    task = models.ForeignKey(
        Task, verbose_name=_('Task'),
        on_delete=models.CASCADE
    )
    author = models.ForeignKey(
        UserProfile, verbose_name=_('Author'),
        on_delete=models.CASCADE
    )
    date_create = models.DateTimeField(_('Time of create'), auto_now_add=True)

    def __str__(self):
        return self.text

    class Meta:
        db_table = 'task_extra_comments'
        verbose_name = _('Extra comment')
        verbose_name_plural = _('Extra comments')
        ordering = '-date_create',


class TaskDocumentAttachment(models.Model):
    title = models.CharField(max_length=64)
    doc_file = models.FileField(upload_to='task_attachments/%Y/%m/', max_length=128)
    create_time = models.DateTimeField(auto_now_add=True)
    author = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    task = models.ForeignKey(Task, on_delete=models.CASCADE)

    def __str__(self):
        return self.title

    class Meta:
        db_table = 'task_doc_attachments'
