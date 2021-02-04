import os

from bitfield.models import BitField
from django.conf import settings
from django.contrib.auth.models import (
    BaseUserManager, AbstractBaseUser,
    PermissionsMixin, Permission
)
from django.contrib.sites.models import Site
from django.db import models
from django.utils.translation import gettext_lazy as _

from djing2.lib.validators import latinValidator, telephoneValidator
from djing2.models import BaseAbstractModel, BaseAbstractModelMixin
from groupapp.models import Group
from profiles.tasks import resize_profile_avatar


class MyUserManager(BaseUserManager):
    def create_user(self, telephone, username, password=None, is_save=True, **other_fields):
        """
        Creates and saves a User with the given email, date of
        birth and password.
        """
        if not telephone:
            raise ValueError(_('Users must have an telephone number'))

        user = self.model(
            telephone=telephone,
            username=username,
            **other_fields
        )
        user.is_admin = False

        if password:
            user.set_password(password)
        if is_save:
            user.save(using=self._db)
        return user

    def create_superuser(self, telephone, username, password=None, is_save=True, **other_fields):
        """
        Creates and saves a superuser with the given email, date of
        birth and password.
        """
        user = UserProfile.objects.create_user(telephone,
                                               password=password,
                                               username=username,
                                               is_save=False,
                                               **other_fields
                                               )

        user.is_admin = True
        user.is_superuser = True
        if is_save:
            user.save(using=self._db)
        return user


class BaseAccount(BaseAbstractModelMixin, AbstractBaseUser, PermissionsMixin):
    username = models.CharField(
        _('profile username'),
        max_length=127,
        unique=True,
        validators=(latinValidator,)
    )
    fio = models.CharField(_('fio'), max_length=256)
    birth_day = models.DateField(_('birth day'), null=True, blank=True, default=None)
    create_date = models.DateField(_('Create date'), auto_now_add=True)
    last_update_time = models.DateTimeField(_('Last update time'), default=None, null=True, blank=True)
    is_active = models.BooleanField(_('Is active'), default=True)
    is_admin = models.BooleanField(default=False)
    telephone = models.CharField(
        max_length=16,
        verbose_name=_('Telephone'),
        blank=True,
        null=True,
        default=None,
        validators=(telephoneValidator,)
    )
    sites = models.ManyToManyField(Site, blank=True)

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ('telephone',)

    def get_full_name(self):
        return self.fio if self.fio else self.username

    def get_short_name(self):
        return self.username or self.telephone

    def auth_log(self, user_agent: str, remote_ip: str):
        ProfileAuthLog.objects.create(
            profile=self,
            user_agent=user_agent,
            remote_ip=remote_ip
        )

    # Use UserManager to get the create_user method, etc.
    objects = MyUserManager()

    @property
    def is_staff(self):
        """ Is the user a member of staff?"""
        # Simplest possible answer: All admins are staff
        return self.is_admin

    def __str__(self):
        return self.get_full_name()

    class Meta:
        db_table = 'base_accounts'
        ordering = 'username',


class UserProfileLogActionType(models.IntegerChoices):
    UNDEFINED = 0, _('Undefined')
    CREATE_USER = 1, _('Create user')
    DELETE_USER = 2, _('Delete user')
    CREATE_DEVICE = 3, _('Create device')
    DELETE_DEVICE = 4, _('Delete device')
    CREATE_NAS = 5, _('Create NAS')
    DELETE_NAS = 6, _('Delete NAS')
    CREATE_SERVICE = 7, _('Create service')
    DELETE_SERVICE = 8, _('Delete service')


class UserProfileLog(BaseAbstractModel):
    account = models.ForeignKey('UserProfile', on_delete=models.CASCADE, verbose_name=_('Author'))
    # meta_info = JSONField(verbose_name=_('Meta information'))
    do_type = models.PositiveSmallIntegerField(_('Action type'), choices=UserProfileLogActionType.choices,
                                               default=UserProfileLogActionType.UNDEFINED)
    additional_text = models.CharField(_('Additional info'), blank=True, null=True, max_length=512)
    action_date = models.DateTimeField(_('Action date'), auto_now_add=True)

    def __str__(self):
        return self.get_do_type_display()

    class Meta:
        ordering = '-action_date',
        verbose_name = _('User profile log')
        verbose_name_plural = _('User profile logs')
        db_table = 'profiles_userprofilelog'


class UserProfileManager(MyUserManager):
    def get_queryset(self):
        qs = super().get_queryset()
        # TODO: check if AnonymousUser yet used
        return qs.exclude(username='AnonymousUser')

    def get_profiles_by_group(self, group_id):
        return self.filter(responsibility_groups__id__in=(group_id,), is_admin=True, is_active=True)

    def create_user(self, telephone, username, password=None, is_save=True, **other_fields):
        """
        Creates and saves a User with the given email, date of
        birth and password.
        """
        if not telephone:
            raise ValueError(_('Users must have an telephone number'))

        user = self.model(
            telephone=telephone,
            username=username,
            **other_fields
        )
        user.is_admin = True

        if password:
            user.set_password(password)
        if is_save:
            user.save(using=self._db)
        return user


class UserProfile(BaseAccount):
    avatar = models.ImageField(_('Avatar'), upload_to=os.path.join('user', 'avatar'), null=True, default=None,
                               blank=True)
    email = models.EmailField(default='', blank=True)
    responsibility_groups = models.ManyToManyField(Group, blank=True, verbose_name=_('Responsibility groups'))
    USER_PROFILE_FLAGS = (
        ('notify_task', _('Notification about tasks')),
        ('notify_msg', _('Notification about messages')),
        ('notify_mon', _('Notification from monitoring'))
    )
    flags = BitField(flags=USER_PROFILE_FLAGS, default=0, verbose_name=_('Settings flags'))

    objects = UserProfileManager()

    class Meta:
        verbose_name = _('Staff account profile')
        verbose_name_plural = _('Staff account profiles')
        ordering = 'fio',
        db_table = 'profiles_userprofile'

    def save(self, *args, **kwargs):
        r = super().save(*args, **kwargs)
        if self.avatar and os.path.isfile(self.avatar.path):
            resize_profile_avatar(self.avatar.path)
        return r

    def log(self, request_meta: dict, do_type: str, additional_text=None) -> None:
        """
        Make log about administrator actions.
        :param request_meta: META from django request.
        :param do_type: Choice from UserProfileLog.ACTION_TYPES
        :param additional_text: Additional information for action
        :return: None
        """
        inf = {
            'src_ip': request_meta.get('REMOTE_ADDR'),
            'username': request_meta.get('USER'),
            'hostname': request_meta.get('HOSTNAME'),
            'useragent': request_meta.get('HTTP_USER_AGENT')
        }
        UserProfileLog.objects.create(
            account=self,
            meta_info=inf,
            do_type=do_type,
            additional_text=additional_text
        )

    def get_avatar_url(self):
        try:
            return self.avatar.url
        except ValueError:
            return getattr(settings, 'DEFAULT_PICTURE', '/static/img/user_ava_min.gif')

    def calc_access_level_percent(self) -> float:
        assigned_perms = self.get_all_permissions()
        all_perms_count = Permission.objects.all().count()
        if all_perms_count > 0:
            res = (100 * len(assigned_perms)) / all_perms_count
            return res
        if self.is_superuser:
            return 100.0
        return 0.0


class ProfileAuthLog(models.Model):
    time = models.DateTimeField(_('Auth time'), auto_now_add=True)
    profile = models.ForeignKey(BaseAccount, on_delete=models.CASCADE, verbose_name=_('Profile'))
    remote_ip = models.GenericIPAddressField(_('Remote ip'), blank=True, null=True, default=None)
    user_agent = models.CharField(_('Details'), max_length=256)

    def __str__(self):
        return self.profile

    class Meta:
        db_table = 'profiles_auth_log'
        ordering = '-id',
