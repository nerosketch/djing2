from django.core import validators
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from sorm_export.models import (
    CommunicationStandardChoices,
    date_format, datetime_format,
    CustomerDocumentTypeChoices
)


class CustomerRootObjectFormat(serializers.Serializer):
    customer_id = serializers.CharField(
        label=_('Customer id'),
        max_length=64,
        required=True
    )
    legal_customer_id = serializers.CharField(
        label=_('Legal customer id'),
        max_length=64,
        required=False
    )
    contract_start_date = serializers.DateField(
        label=_('Date of conclusion of the contract'),
        required=True,
        format=date_format
    )  # format dd.mm.YYYY
    customer_login = serializers.CharField(
        label=_('Customer login'),
        max_length=256,
        required=True
    )
    customer_state = serializers.CharField(default='', required=False)  # reserved
    communication_standard = serializers.ChoiceField(
        label=_('Communication_standard'),
        choices=CommunicationStandardChoices.choices,
        default=0
    )


class CustomerContractObjectFormat(serializers.Serializer):
    contract_id = serializers.CharField(
        label=_('Contract ID'),
        max_length=64,
        required=True
    )
    customer_id = serializers.CharField(
        label=_('Customer id'),
        max_length=64,
        required=True
    )
    contract_status = serializers.CharField(default='', required=False)  # reserved
    contract_start_date = serializers.DateField(
        label=_('Date of conclusion of the contract'),
        required=True,
        format=date_format
    )  # format dd.mm.YYYY
    contract_end_date = serializers.DateField(
        label=_('Contract completion date'),
        format=date_format,
        allow_null=True,
        required=False
    )  # format DD.mm.YYYYTHH:MM:SS or ''
    contract_number = serializers.CharField(
        label=_('Contract number'),
        max_length=128,
        required=False
    )
    contract_title = serializers.CharField(
        label=_('Contract title'),
        max_length=256,
        default=''
    )


class AddressObjectFormat(serializers.Serializer):
    address_id = serializers.CharField(
        label=_('Address id'),
        help_text="это может быть любой идентификатор: GUID, первичный ключ таблицы, код FIAS",
        max_length=128,
        required=True
    )
    parent_id = serializers.CharField(
        label=_('Parent address id'),
        help_text="для корневого а/о (страна) - пустое поле",
        max_length=128,
        allow_blank=True,
        default=''
    )
    type_id = serializers.IntegerField(
        label=_('Address type id'),
        help_text="соответствует полю SOCRBASE.KOD_T_ST (уникальный код типа а/о) "
                  "из справочника типов адресных объектов ФИАС",
        # https://github.com/hflabs/socrbase/blob/master/socrbase.csv
        required=True,
        # sorm_export.fias_socrbase.py
    )
    region_type = serializers.CharField(
        label=_('Region type'),
        max_length=128,
        help_text="соответствует полю SOCRBASE.SOCRNAME (сокращённое название) "
                  "из справочника типов адресных объектов ФИАС",
        # sorm_export.fias_socrbase.py
        required=True
    )
    title = serializers.CharField(
        label=_('Title'),
        max_length=128,
        required=True,
        help_text="содержит только название, без типа адресного объекта"
    )
    home = serializers.CharField(default="", required=False)  # reserved
    building = serializers.CharField(default="", required=False)  # reserved
    korp = serializers.CharField(default="", required=False)  # reserved
    full_title = serializers.CharField(
        label=_('Full address title'),
        max_length=512,
        required=False
    )


class CustomerAccessPointAddressObjectFormat(serializers.Serializer):
    """
     https://wiki.vasexperts.ru/doku.php?id=sorm:sorm3:sorm3_subs_dump:sorm3_subs_hier:start
     #файл_выгрузки_адресов_точек_подключения_версия_1
    """

    # 1
    ap_id = serializers.CharField(
        label=_('Access point id'),
        max_length=128,
        required=True,
    )
    # 2
    customer_id = serializers.CharField(
        label=_('Customer id'),
        max_length=64,
        required=True,
    )
    # 3
    house = serializers.IntegerField(
        label=_('House'),
        required=True,
    )
    # 4
    full_address = serializers.CharField(
        label=_('Full address'),
        max_length=512,
        required=False,
        allow_blank=True,
        allow_null=True,
        default=''
    )
    # 5
    internal_address = serializers.CharField(
        label=_('Internal address'),
        required=False,
        allow_blank=True,
        default=''
    )  # reserved
    # 6
    # reserved, ao - address object
    id_ao = serializers.CharField(default='', required=False)
    # 7
    parent_id_ao = serializers.CharField(
        label=_('Parent ao id'),
        max_length=128,
        required=True
    )  # AddressObjectFormat.address_id
    # 8
    type_id = serializers.CharField(default='', required=False)  # reserved
    # 9
    type_ao = serializers.CharField(default='', required=False)  # reserved
    # 10
    title = serializers.CharField(default='', required=False)  # reserved
    # 11
    house_num = serializers.IntegerField(
        label=_('House'),
        required=False,
        allow_null=True,
        default=None
    )
    # 12
    building = serializers.IntegerField(
        label=_('Building'),
        required=False,
        allow_null=True,
        default=None
    )
    # 13
    building_corpus = serializers.CharField(
        label=_('Building corpus'),
        max_length=32,
        required=False,
        allow_null=True,
        allow_blank=True,
        default=''
    )
    # 14
    full_description = serializers.CharField(
        label=_('Full description'),
        required=False,
        allow_null=True,
        default=''
    )  # reserved
    # 15
    actual_start_time = serializers.DateTimeField(
        label=_('Actual start time'),
        help_text="для первой записи должна быть равна дате заключения договора с "
                  "абонентом, для последующих исторических записей - должна "
                  "превышать дату окончания предыдущей записи",
        required=True,
        format=datetime_format,
        allow_null=False
    )
    # 16
    actual_end_time = serializers.DateTimeField(
        label=_('Actual end time'),
        help_text="Должна быть меньше или равна дате расторжения "
                  "договора с абонентом и превышать дату начала интервала",
        required=False,
        format=datetime_format,
        allow_null=True
    )


class CustomerIndividualObjectFormat(serializers.Serializer):
    # 1
    contract_id = serializers.CharField(
        label='ID физ лица',
        max_length=64,
        required=True
    )  # CustomerRootObjectFormat.legal_customer_id
    # 2
    name = serializers.CharField(
        label=_('Individual customer name'),  # ФИО
        max_length=64,
        required=True
    )
    # 3
    last_name = serializers.CharField(
        label=_('Last name'),
        required=False,
        max_length=64,
        default=''
    )
    # 4
    surname = serializers.CharField(
        label=_('Surname'),
        max_length=64,
        required=False,
        allow_blank=True,
        allow_null=True,
        default=''
    )
    # 5
    birthday = serializers.DateField(
        label=_('Birthday'),
        required=False,
        format=date_format,
        allow_null=True,
        default=''
    )  # format DD.mm.YYYY
    # 6
    document_type = serializers.ChoiceField(
        label=_('Document type'),
        required=False,
        choices=CustomerDocumentTypeChoices.choices,
        default=CustomerDocumentTypeChoices.EMPTY,
        allow_blank=True,
        allow_null=True,
    )
    # 7
    document_serial = serializers.CharField(
        label=_('Document serial'),
        max_length=32,
        validators=[validators.integer_validator],
        required=False,
        default=''
    )
    # 8
    document_number = serializers.CharField(
        label=_('Document number'),
        max_length=64,
        validators=[validators.integer_validator],
        required=False,
        default=''
    )
    # 9
    document_distributor = serializers.CharField(
        label=_('Document distributor'),
        help_text="содержит название подразделения, "
                  "выдавшего документ, например, "
                  "«35 о/м Приморского р-на, г. Санкт-Петербург»",
        max_length=128,
        required=False,
        default=''
    )
    # 10
    passport_code = serializers.CharField(
        label="Код подразделения",
        max_length=16,
        required=False,
        allow_blank=True,
        allow_null=True,
        default=''
    )
    # 11
    passport_date = serializers.DateField(
        label="Дата выдачи документа",
        format=date_format,
        required=False,
        default=''
    )
    # 12
    reserved = serializers.CharField(default='', required=False)
    # 13
    house = serializers.CharField(
        label=_('House'),
        help_text="квартира адреса прописки",
        max_length=32,
        required=False,
        allow_blank=True,
        allow_null=True,
        default=''
    )
    # 14
    ao_id = serializers.CharField(default='', required=False)  # reserved
    # 15
    # FIXME: In docs field 'parent_id_ao' is required
    parent_id_ao = serializers.CharField(
        label=_('Parent ao id'),
        max_length=128,
        required=False,
        allow_blank=True,
        allow_null=True,
        default=''
    )  # AddressObjectFormat.address_id
    # 16
    ao_type_id = serializers.CharField(default='', required=False)  # reserved
    # 17
    ao_type = serializers.CharField(default='', required=False)  # reserved
    # 18
    ao_title = serializers.CharField(default='', required=False)  # reserved
    # 19
    house_num = serializers.IntegerField(
        label=_('House number'),
        required=False,
        allow_null=True,
        default=None
    )
    # 20
    building = serializers.IntegerField(
        label=_('Building'),
        required=False,
        allow_null=True,
        default=None
    )
    # 21
    building_corpus = serializers.CharField(
        label=_('Building corpus'),
        max_length=32,
        required=False,
        allow_null=True,
        allow_blank=True,
        default=''
    )
    # 22
    full_description = serializers.CharField(
        label=_('Full description'),
        required=False,
        allow_null=True,
        allow_blank=True,
        default=''
    )  # reserved
    # 23
    actual_start_time = serializers.DateTimeField(
        label=_('Actual start time'),
        help_text="для первой записи должна быть равна дате заключения договора с "
                  "абонентом, для последующих исторических записей - должна "
                  "превышать дату окончания предыдущей записи",
        required=True,
        format=datetime_format,
        allow_null=False
    )
    # 24
    actual_end_time = serializers.DateTimeField(
        label=_('Actual end time'),
        help_text="Должна быть меньше или равна дате расторжения "
                  "договора с абонентом и превышать дату начала интервала",
        required=False,
        format=datetime_format,
        allow_null=True,
        default=''
    )
    # 25
    customer_id = serializers.CharField(
        label=_('Customer id'),
        max_length=64,
        required=True
    )


class CustomerLegalObjectFormat(serializers.Serializer):
    # №1
    legal_id = serializers.CharField(
        label=_('Legal customer id'),
        max_length=64,
        required=True
    )  # CustomerRootObjectFormat.legal_customer_id
    # №2
    legal_title = serializers.CharField(
        label=_('Legal title'),
        help_text="название ЮЛ, содержит организационно-правовую форму в "
                  "сокращенном виде (ПАО, АО и т.д.) и полное наименование "
                  "организации без кавычек, определяющих слов и фраз, например, "
                  "«ООО Ромашка»",
        max_length=256,
        required=True
    )
    # №3
    inn = serializers.CharField(
        label='ИНН',
        max_length=32,
        default='',
        required=False
    )
    # №4
    post_index = serializers.CharField(
        label='почтовый индекс адреса абонента',
        max_length=6,
        validators=[validators.integer_validator],
        default='',
        required=False
    )
    # №5
    office_addr = serializers.CharField(
        label='офис юридического адреса, содержит только цифры офиса',
        max_length=32,
        required=False,
        allow_blank=True,
        default='',
    )
    # №6
    ao_id = serializers.CharField(default='', required=False)  # reserved
    # №7
    parent_id_ao = serializers.CharField(
        label=_('Parent ao id'),
        max_length=128,
        required=True
    )  # AddressObjectFormat.address_id
    # №8
    ao_type_id = serializers.CharField(default='', required=False)  # reserved
    # №9
    ao_type = serializers.CharField(default='', required=False)  # reserved
    # №10
    ao_title = serializers.CharField(default='', required=False)  # reserved
    # №11
    house = serializers.IntegerField(
        label='Номер дома',
        help_text="содержит только номер дома, без типа а/о",
        default=None,
        required=False,
        allow_null=True,
    )
    # №12
    building = serializers.IntegerField(
        label=_('Building'),
        help_text='содержит только номер или букву здания, без типа а/о',
        default=None,
        allow_null=True,
        required=False
    )
    # №13
    building_corpus = serializers.CharField(
        label=_('Building corpus'),
        help_text='содержит только номер корпуса',
        max_length=32,
        default='',
        allow_null=True,
        allow_blank=True,
        required=False
    )
    # №14
    full_description = serializers.CharField(
        label=_('Full description'),
        default='',
        required=False,
    )  # reserved
    # №15
    customer_bank = serializers.CharField(
        label=_('Customer bank'),
        max_length=256,
        default='',
        required=False
    )
    # №16
    customer_bank_num = serializers.CharField(
        label=_('Bank receipt number'),
        max_length=128,
        default='',
        allow_blank=True,
        allow_null=True,
        required=False
    )
    # №17
    contact_telephones = serializers.CharField(
        label=_('Contact telephones'),
        max_length=128,
        help_text='содержит телефоны контактного лица',
        default='',
        required=False
    )
    # №18
    post_post_index = serializers.CharField(
        label='почтовый индекс почтового адреса абонента',
        max_length=6,
        validators=[validators.integer_validator],
        default='',
        required=False
    )
    # №19
    office_post_addr = serializers.CharField(
        label='Почтовый адрес офиса',
        help_text='содержит только цифры офиса',
        max_length=32,
        #validators=[validators.integer_validator],
        default='',
        allow_blank=True,
        allow_null=True,
        required=False
    )
    # №20
    ao_id2 = serializers.CharField(default='', required=False)  # reserved
    # №21
    post_parent_id_ao = serializers.CharField(
        label='ID родительского а/о в regions для почтового адреса',
        help_text='соответствует полю 1 в «Файле выгрузки адресных объектов»',
        max_length=128,
        required=True
    )  # AddressObjectFormat.address_id
    # №22
    post_ao_type_id = serializers.CharField(default='', required=False)  # reserved
    # №23
    post_ao_type = serializers.CharField(default='', required=False)  # reserved
    # №24
    post_ao_title = serializers.CharField(default='', required=False)  # reserved
    # №25
    post_house = serializers.IntegerField(
        label='номер дома почтового адреса',
        help_text="содержит только номер дома, без типа а/о",
        default=None,
        allow_null=True,
        required=False,
    )
    # №26
    post_building = serializers.IntegerField(
        label='здание почтового адреса',
        help_text='содержит только номер или букву здания, без типа а/о',
        default=None,
        allow_null=True,
        required=False
    )
    # №27
    post_building_corpus = serializers.CharField(
        label='корпус почтового адреса',
        help_text='содержит только номер корпуса',
        max_length=32,
        default='',
        allow_null=True,
        allow_blank=True,
        required=False
    )
    # №28
    post_full_description = serializers.CharField(
        label=_('Full description'),
        default='',
        required=False,
    )  # reserved
    # №29
    post_delivery_index = serializers.CharField(
        label='почтовый индекс адреса доставки',
        max_length=6,
        validators=[validators.integer_validator],
        default='',
        required=False
    )
    # №30
    office_delivery_address = serializers.CharField(
        label='Адрес офиса доставки счёта',
        help_text='содержит только цифры офиса',
        #validators=[validators.integer_validator],
        max_length=32,
        default='',
        allow_blank=True,
        required=False
    )
    # №31
    office_delivery_address_id = serializers.CharField(default='', required=False)  # reserved
    # №32
    parent_office_delivery_address_id = serializers.CharField(
        label='ID родительского а/о в regions для адреса доставки счёта',
        help_text='соответствует полю 1 в «Файле выгрузки адресных объектов»',
        max_length=128,
        required=True
    )  # AddressObjectFormat.address_id
    # №33
    office_delivery_address_type_id = serializers.CharField(default='', required=False)  # reserved
    # №34
    office_delivery_address_ao_type = serializers.CharField(default='', required=False)  # reserved
    # №35
    office_delivery_address_ao_title = serializers.CharField(default='', required=False)  # reserved
    # №36
    office_delivery_address_house = serializers.IntegerField(
        label='Номер дома адреса доставки счёта, строка',
        help_text="содержит только номер дома, без типа а/о",
        default=None,
        allow_null=True,
        required=False,
    )
    # №37
    office_delivery_address_building = serializers.IntegerField(
        label=_('Building'),
        help_text='содержит только номер или букву здания, без типа а/о',
        default=None,
        allow_null=True,
        required=False
    )
    # №38
    office_delivery_address_building_corpus = serializers.CharField(
        label=_('Building corpus'),
        help_text='содержит только номер корпуса',
        max_length=32,
        default=None,
        allow_null=True,
        allow_blank=True,
        required=False
    )
    # №39
    office_delivery_address_full_description = serializers.CharField(
        label='полное наименование а/о доставки счёта',
        default='',
        required=False,
    )  # reserved
    # №40
    actual_start_time = serializers.DateTimeField(
        label=_('Actual start time'),
        help_text="для первой записи должна быть равна дате заключения договора с "
                  "абонентом, для последующих исторических записей - должна "
                  "превышать дату окончания предыдущей записи",
        required=True,
        format=datetime_format,
        allow_null=False
    )
    # №41
    actual_end_time = serializers.DateTimeField(
        label=_('Actual end time'),
        help_text="Должна быть меньше или равна дате расторжения "
                  "договора с абонентом и превышать дату начала интервала",
        required=False,
        format=datetime_format,
        allow_null=True
    )
    # №42
    customer_id = serializers.CharField(
        label=_('Customer ID'),
        max_length=64,
        required=True
    )


class CustomerContactObjectFormat(serializers.Serializer):
    customer_id = serializers.CharField(
        label=_('Customer id'),
        max_length=64,
        required=True
    )  # CustomerRootObjectFormat.legal_customer_id
    contact = serializers.CharField(
        label=_('Contact info'),
        help_text='содержит ФИО, адрес, контактный телефон и факс, '
                  'минимально допустимый формат «Иванов Иван,Спб,Тельмана, '
                  '1-1,т.3332211,ф.3332211»',
        max_length=128,
        required=True
    )
    customer_status = serializers.CharField(default='', required=False)  # reserved
    actual_start_time = serializers.DateTimeField(
        label=_('Actual start time'),
        help_text="для первой записи должна быть равна дате заключения договора с "
                  "абонентом, для последующих исторических записей - должна "
                  "превышать дату окончания предыдущей записи",
        required=True,
        format=datetime_format,
        allow_null=False
    )
    actual_end_time = serializers.DateTimeField(
        label=_('Actual end time'),
        help_text="Должна быть меньше или равна дате расторжения "
                  "договора с абонентом и превышать дату начала интервала",
        required=False,
        format=datetime_format,
        allow_null=True
    )
