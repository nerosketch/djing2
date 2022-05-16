# Generated by Django 3.1.14 on 2022-03-16 13:14

from django.db import migrations, models
from django.utils.translation import gettext as _


#  TASK_TYPE_NOT_CHOSEN = 0
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
    #  (TASK_TYPE_NOT_CHOSEN, _("not chosen")),
    (TASK_TYPE_IP_CONFLICT, _("ip conflict")),
    (TASK_TYPE_YELLOW_TRIANGLE, _("yellow triangle")),
    (TASK_TYPE_RED_CROSS, _("red cross")),
    (TASK_TYPE_WAEK_SPEED, _("weak speed")),
    (TASK_TYPE_CABLE_BREAK, _("cable break")),
    (TASK_TYPE_CONNECTION, _("connection")),
    (TASK_TYPE_PERIODIC_DISAPPEARANCE, _("periodic disappearance")),
    (TASK_TYPE_ROUTER_SETUP, _("router setup")),
    (TASK_TYPE_CONFIGURE_ONU, _("configure onu")),
    (TASK_TYPE_CRIMP_CABLE, _("crimp cable")),
    (TASK_TYPE_INTERNET_CRASH, _("Internet crash")),
    (TASK_TYPE_OTHER, _("other")),
)

def create_task_modes(apps, schema_editor):
    TaskModeModel = apps.get_model("tasks", "TaskModeModel")
    doc_models = [TaskModeModel(pk=item_num, title=item_title) for item_num, item_title in TASK_TYPES]
    TaskModeModel.objects.bulk_create(doc_models)


def copy_fkmodes_from_fixed_modes(apps, schema_editor):
    Task = apps.get_model("tasks", "Task")
    Task.objects.exclude(mode=0).update(task_mode=models.F('mode'))


class Migration(migrations.Migration):

    dependencies = [
        ('profiles', '0005_auto_20210204_2043'),
        ('tasks', '0006_auto_20210721_2238'),
    ]

    operations = [
        migrations.CreateModel(
            name='TaskModeModel',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=64, verbose_name='Title')),
            ],
            options={
                'db_table': 'task_modes',
            },
        ),
        migrations.AlterModelOptions(
            name='extracomment',
            options={'verbose_name': 'Extra comment', 'verbose_name_plural': 'Extra comments'},
        ),
        migrations.AlterModelOptions(
            name='task',
            options={'permissions': [('can_remind', 'Reminders of tasks'), ('can_view_task_mode_report', 'Can view task mode report')]},
        ),
        migrations.AlterModelOptions(
            name='taskstatechangelogmodel',
            options={'verbose_name': 'Change log', 'verbose_name_plural': 'Change logs'},
        ),
        migrations.CreateModel(
            name='TaskFinishDocumentModel',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.CharField(max_length=64, verbose_name='Document code')),
                ('act_num', models.CharField(blank=True, default=None, max_length=64, null=True, verbose_name='Act num')),
                ('create_time', models.DateTimeField(verbose_name='Time of create')),
                ('finish_time', models.DateTimeField(verbose_name='Finish time')),
                ('cost', models.FloatField(verbose_name='Cost')),
                ('author', models.ForeignKey(on_delete=models.CASCADE, to='profiles.userprofile', verbose_name='Author')),
                ('recipients', models.ManyToManyField(related_name='finish_docs', to='profiles.UserProfile', verbose_name='Recipients')),
                ('task', models.OneToOneField(on_delete=models.CASCADE, to='tasks.task', verbose_name='Task')),
                ('task_mode', models.ForeignKey(blank=True, default=None, null=True, on_delete=models.SET_DEFAULT, to='tasks.taskmodemodel', verbose_name='Mode')),
            ],
            options={
                'db_table': 'task_finish_docs',
            },
        ),
        migrations.AddField(
            model_name='task',
            name='task_mode',
            field=models.ForeignKey(blank=True, default=None, null=True, on_delete=models.SET_DEFAULT, to='tasks.taskmodemodel', verbose_name='Mode'),
        ),
        migrations.RunPython(create_task_modes),
        migrations.RunPython(copy_fkmodes_from_fixed_modes),
    ]