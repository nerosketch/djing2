from typing import Optional

from django.db.models import Subquery, OuterRef, Count, Q, QuerySet
from django.utils.translation import gettext_lazy as _, gettext
from djing2.lib.logger import logger
from addresses.models import AddressModelTypes, AddressModel
from customer_contract.models import CustomerContractModel
from customers_legal.models import CustomerLegalModel
from customers.models import Customer
from profiles.models import FioDataclass
from sorm_export.models import (
    CommunicationStandardChoices,
    CustomerDocumentTypeChoices,
    ExportStampTypeEnum
)
from sorm_export.serializers import individual_entity_serializers
from sorm_export.checks.customer import (
    customer_checks,
    CheckFailedException,
    customer_legal_checks,
    _addr_get_parent
)
from .base import (
    format_fname,
    ExportTree, ContinueIteration,
    SimpleExportTree
)


def general_customer_all_filter_queryset():
    return Customer.objects.filter(is_active=True).annotate(
        contr_count=Count('customercontractmodel'),
        legals=Count('customerlegalmodel')
    ).filter(Q(contr_count__gt=0) | Q(legals__gt=0))


def general_customer_filter_queryset():
    """Физ учётки только те, у которых есть хотя бы один договор, и нет
       привязки к ЮР учётке"""

    return Customer.objects.filter(is_active=True).annotate(
        contr_count=Count('customercontractmodel'),
        legals=Count('customerlegalmodel')
    ).filter(contr_count__gt=0, legals=0)


def general_legal_filter_queryset():
    """Юр учётки только те, которые привязаны к ЮР учётке, и без договора."""

    return Customer.objects.filter(is_active=True).annotate(
        contr_count=Count('customercontractmodel'),
        legals=Count('customerlegalmodel'),
    ).filter(legals__gt=0, contr_count=0)


def _addr2str(addr: Optional[AddressModel]) -> str:
    if not addr:
        return ''
    return str(addr.title)


class CustomerRootExportTree(ExportTree[Customer]):
    """
    Файл данных по абонентам v1.
    В этом файле выгружается корневая запись всей иерархии
    данных об абоненте, ошибки загрузки в этом файле приводят
    к каскадным ошибкам загрузки связанных данных в других файлах.
    :return: data, filename
    """

    def get_remote_ftp_file_name(self):
        return f"ISP/abonents/abonents_v1_{format_fname(self._event_time)}.txt"

    @classmethod
    def get_export_format_serializer(cls):
        return individual_entity_serializers.CustomerRootObjectFormat

    @classmethod
    def get_export_type(cls):
        return ExportStampTypeEnum.CUSTOMER_ROOT

    def get_items(self, queryset):
        lgl_sb = CustomerLegalModel.objects.filter(branches__id=OuterRef('pk')).values('pk')
        # FIXME: Абоненты без договора не выгружаются.
        #  Нужно выгружать только тех, у кого есть основной договор.
        #  Нужно сделать типы договоров, чтоб проверять только по 'основному'.
        #  Типы договоров, например: Основной, iptv, voip, доп оборудование, и.т.д.

        for customer in queryset.annotate(
            legal_id=Subquery(lgl_sb)
        ):
            try:
                yield self.get_item(customer)
            except ContinueIteration:
                continue

    def get_item(self, customer):
        # TODO: optimize
        if customer.legal_id:
            # legal
            customer_id = customer.legal_id
            legal = customer.customerlegalmodel_set.first()
            if legal:
                contract_date = legal.actual_start_time.date()
            else:
                logger.error('Contract date for customer legal branch "%s" not found' % customer)
                raise ContinueIteration
        else:
            # individual
            customer_id = customer.pk
            contract = customer.customercontractmodel_set.first()
            if contract is None:
                logger.error('Contract for customer: "%s" not found' % customer)
                raise ContinueIteration
            contract_date = contract.start_service_time.date()
        return {
            "customer_id": customer.pk,
            "legal_customer_id": customer_id,
            "contract_start_date": contract_date,
            "customer_login": customer.username,
            "communication_standard": CommunicationStandardChoices.ETHERNET.value,
        }


class AccessPointExportTree(ExportTree[Customer]):
    """
    Файл выгрузки адресов точек подключения, версия 1.
    В этом файле выгружается информация о точках подключения оборудования - реальном адресе,
    на котором находится оборудование абонента, с помощью которого он пользуется услугами оператора связи.
    TODO: Выгружать адреса абонентов чъё это оборудование.
    TODO: Записывать адреса к устройствам абонентов. Заполнять при создании устройства.
    TODO: Выгружать так же и оборудование юриков. сейчас только физики.
    Сейчас у нас оборудование абонента ставится у абонента дома, так что это тот же адрес
    что и у абонента.
    """

    def get_remote_ftp_file_name(self):
        return f"ISP/abonents/ap_region_v1_{format_fname(self._event_time)}.txt"

    @classmethod
    def get_export_format_serializer(cls):
        return individual_entity_serializers.CustomerAccessPointAddressObjectFormat

    @classmethod
    def get_export_type(cls):
        return ExportStampTypeEnum.CUSTOMER_AP_ADDRESS

    def filter_queryset(self, queryset):
        return queryset.select_related(
            "address", "address__parent_addr"
        )

    def get_item(self, customer):
        if not hasattr(customer, "address"):
            logger.error(_('Customer "%s" [%s] has no address') % (
                customer, customer.username
            ))
            return
        addr = customer.address

        addr_house = _addr2str(addr.get_address_item_by_type(
            addr_type=AddressModelTypes.HOUSE
        ))
        addr_office = _addr2str(addr.get_address_item_by_type(
            addr_type=AddressModelTypes.OFFICE_NUM
        ))
        if not addr_house and not addr_office:
            logger.error(_('Customer "%s" [%s] has no house nor office in address "%s"') % (
                customer, customer.username, addr
            ))
            return

        addr_parent_street = addr.get_address_item_by_type(
            addr_type=AddressModelTypes.STREET
        )
        if not addr_parent_street:
            logger.error(
                _('Customer "%s" with login "%s" address has no parent street element') % (
                    customer,
                    customer.username
                ))
            return

        addr_building = _addr2str(addr.get_address_item_by_type(
            addr_type=AddressModelTypes.BUILDING
        ))
        addr_corpus = _addr2str(addr.get_address_item_by_type(
            addr_type=AddressModelTypes.CORPUS
        ))

        # first available contract
        # TODO: optimize
        contract = customer.customercontractmodel_set.first()

        return {
            "ap_id": addr.pk,
            "customer_id": customer.pk,
            "house": addr_house or addr_office,
            "parent_id_ao": addr_parent_street.pk,
            "house_num": addr_house or None,
            "builing": addr_building,
            "building_corpus": addr_corpus or None,
            "full_address": addr.full_title(),
            "actual_start_time": contract.start_service_time,
            'actual_end_time': contract.end_service_time or None
        }


def _report_about_customers_no_have_passport(customers_without_passports_qs):
    for customer in customers_without_passports_qs.prefetch_related('sites'):
        # FIXME: That is Very very shit code block, i'm sorry :(
        sites = customer.sites.all()
        logger.error(
            "%s; %s" % (
                _('Customer "%s" [%s] has no passport info') % (customer, customer.username),
                ' '.join(s.name for s in sites)
            )
        )


class IndividualCustomersExportTree(ExportTree[Customer]):
    """
    Файл выгрузки данных о физическом лице, версия 2
    В этом файле выгружается информация об абонентах, у которых контракт заключён с физическим лицом.
    Выгружаются только абоненты с паспортными данными.
    """

    def get_remote_ftp_file_name(self):
        return f"ISP/abonents/fiz_v2_{format_fname(self._event_time)}.txt"

    @classmethod
    def get_export_format_serializer(cls):
        return individual_entity_serializers.CustomerIndividualObjectFormat

    @classmethod
    def get_export_type(cls):
        return ExportStampTypeEnum.CUSTOMER_INDIVIDUAL

    @staticmethod
    def _add_fio(fio: FioDataclass) -> dict:
        r = {}
        if fio.surname:
            r['surname'] = fio.surname
        if fio.name:
            r['name'] = fio.name
        if fio.last_name:
            r['last_name'] = fio.last_name
        return r

    def filter_queryset(self, queryset):
        contract_start_service_time_q = CustomerContractModel.objects.filter(
            customer_id=OuterRef('pk'),
            is_active=True
        ).values('start_service_time')
        qs = queryset.select_related(
            "group", "passportinfo"
        ).annotate(
            contract_date=Subquery(contract_start_service_time_q),
            legals=Count('customerlegalmodel'),
        )
        _report_about_customers_no_have_passport(
            qs.filter(passportinfo=None).filter(legals=0)
        )
        return qs

    def _make_legal_filial_item(self, customer):
        my_legal = customer.customerlegalmodel_set.first()

        try:
            addr_parent_street_region = _addr_get_parent(
                customer.address,
                _('Customer "%s" with login "%s" address has no parent street element') % (
                    customer,
                    customer.username
                )
            )
        except CheckFailedException as err:
            logger.error(str(err))
            return

        actual_start_date = my_legal.actual_start_time

        r = {
            "contract_id": my_legal.pk,
            "birthday": customer.birth_day or None,
            "parent_id_ao": addr_parent_street_region.pk,
            "actual_start_time": actual_start_date,
            # TODO: "actual_end_time":
            "customer_id": customer.pk,
        }

        passport = getattr(customer, 'passportinfo', None)
        if passport:
            r.update({
                "document_type": CustomerDocumentTypeChoices.PASSPORT_RF,
                "document_serial": passport.series,
                "document_number": passport.number,
                "document_distributor": passport.distributor,
                "passport_code": passport.division_code or "",
                "passport_date": passport.date_of_acceptance,
            })
            addr = passport.registration_address
            if addr:
                addr_house = addr.get_address_item_by_type(
                    addr_type=AddressModelTypes.HOUSE
                )
                addr_building = addr.get_address_item_by_type(
                    addr_type=AddressModelTypes.BUILDING
                )
                addr_corp = addr.get_address_item_by_type(
                    addr_type=AddressModelTypes.CORPUS
                )
                r.update({
                    "house": addr.title,
                    "house_num": addr_house.title if addr_house else None,
                    "building": addr_building.title if addr_building else None,
                    "building_corpus": addr_corp.title if addr_corp else None,
                })

        fio = my_legal.split_fio()
        r.update(self._add_fio(fio))
        return r

    def _make_individual_item(self, customer):
        try:
            check_ok_res = customer_checks(customer=customer)
        except CheckFailedException as err:
            logger.error(str(err))
            return

        passport = check_ok_res.passport
        addr = passport.registration_address
        if not check_ok_res.parent_street:
            return

        if not customer.contract_date:
            logger.error(_('Customer contract has no date %s [%s]') % (customer, customer.username))
            return
        actual_start_date = customer.contract_date

        addr_house = addr.get_address_item_by_type(
            addr_type=AddressModelTypes.HOUSE
        )
        addr_building = addr.get_address_item_by_type(
            addr_type=AddressModelTypes.BUILDING
        )
        addr_corp = addr.get_address_item_by_type(
            addr_type=AddressModelTypes.CORPUS
        )
        r = {
            "contract_id": customer.pk,
            "birthday": customer.birth_day,
            "document_type": CustomerDocumentTypeChoices.PASSPORT_RF,
            "document_serial": passport.series,
            "document_number": passport.number,
            "document_distributor": passport.distributor,
            "passport_code": passport.division_code or "",
            "passport_date": passport.date_of_acceptance,
            "house": addr.title,
            "parent_id_ao": check_ok_res.parent_street.pk,
            "house_num": addr_house.title if addr_house else None,
            "building": addr_building.title if addr_building else None,
            "building_corpus": addr_corp.title if addr_corp else None,
            "actual_start_time": actual_start_date,
            # TODO: "actual_end_time":
            "customer_id": customer.pk,
        }
        fio = customer.split_fio()
        r.update(self._add_fio(fio))
        return r

    def get_item(self, customer):
        if customer.is_legal_filial:
            return self._make_legal_filial_item(customer)
        return self._make_individual_item(customer)


class LegalCustomerExportTree(ExportTree[CustomerLegalModel]):
    """
    Файл выгрузки данных о юридическом лице версия 5.
    В этом файле выгружается информация об абонентах у которых контракт заключён с юридическим лицом.
    """

    def get_remote_ftp_file_name(self):
        return f'ISP/abonents/jur_v5_{format_fname(self._event_time)}.txt'

    @classmethod
    def get_export_format_serializer(cls):
        return individual_entity_serializers.CustomerLegalObjectFormat

    @classmethod
    def get_export_type(cls):
        return ExportStampTypeEnum.CUSTOMER_LEGAL

    def filter_queryset(self, queryset):
        legals = queryset.select_related('address', 'delivery_address', 'post_address')
        return legals

    def get_items(self, queryset):
        for legal in queryset:
            yield from self._iter_customers(legal)

    def _iter_customers(self, legal):
        try:

            legal_checks = customer_legal_checks(legal=legal)
        except CheckFailedException as err:
            logger.error(str(err))
            return

        addr = legal_checks.addr
        addr_parent_region = legal_checks.parent_street
        post_addr = legal_checks.post_addr
        post_addr_parent_region = legal_checks.post_addr_parent_street
        delivery_addr = legal_checks.delivery_addr
        delivery_addr_parent_region = legal_checks.delivery_parent_street

        res = {
            'legal_id': legal.pk,
            'legal_title': legal.title,
            'inn': legal.tax_number,
            'post_index': legal.post_index,
            'office_addr': _addr2str(addr.get_address_item_by_type(
                addr_type=AddressModelTypes.OFFICE_NUM
            )),
            'parent_id_ao': addr_parent_region.pk,
            'house': _addr2str(addr.get_address_item_by_type(
                addr_type=AddressModelTypes.HOUSE
            )) or None,
            'building': _addr2str(addr.get_address_item_by_type(
                addr_type=AddressModelTypes.BUILDING
            )) or None,
            'building_corpus': _addr2str(addr.get_address_item_by_type(
                addr_type=AddressModelTypes.CORPUS
            )),
            'full_description': addr.full_title(),
            # TODO: fill contact_telephones
            # 'contact_telephones': '',
            'post_post_index': legal.post_post_index or legal.post_index,
            'office_post_addr': _addr2str(post_addr.get_address_item_by_type(
                addr_type=AddressModelTypes.OFFICE_NUM
            )),
            'post_parent_id_ao': post_addr_parent_region.pk if post_addr_parent_region else addr_parent_region.pk,
            'post_house': _addr2str(post_addr.get_address_item_by_type(
                addr_type=AddressModelTypes.HOUSE
            )) or None,
            'post_building': _addr2str(post_addr.get_address_item_by_type(
                addr_type=AddressModelTypes.BUILDING
            )) or None,
            'post_building_corpus': _addr2str(post_addr.get_address_item_by_type(
                addr_type=AddressModelTypes.BUILDING
            )),
            'post_full_description': post_addr.full_title(),
            'post_delivery_index': legal.delivery_address_post_index or legal.post_index,
            'office_delivery_address': _addr2str(delivery_addr.get_address_item_by_type(
                addr_type=AddressModelTypes.OFFICE_NUM
            )),
            'parent_office_delivery_address_id': delivery_addr_parent_region.pk if delivery_addr_parent_region else addr_parent_region.pk,
            'office_delivery_address_house': _addr2str(delivery_addr.get_address_item_by_type(
                addr_type=AddressModelTypes.HOUSE
            )) or None,
            'office_delivery_address_building': _addr2str(delivery_addr.get_address_item_by_type(
                addr_type=AddressModelTypes.BUILDING
            )) or None,
            'office_delivery_address_building_corpus': _addr2str(delivery_addr.get_address_item_by_type(
                addr_type=AddressModelTypes.CORPUS
            )),
            'office_delivery_address_full_description': delivery_addr.full_title(),
            'actual_start_time': legal.actual_start_time,
            'actual_end_time': legal.actual_end_time,
        }
        if hasattr(legal, 'legalcustomerbankmodel'):
            bank_info = getattr(legal, 'legalcustomerbankmodel')
            res.update({
                'customer_bank': bank_info.title,
                'customer_bank_num': bank_info.number,
            })

        for customer in legal.branches.filter(is_active=True):
            yield {**res, **{
                'customer_id': customer.pk,
            }}


class ContactSimpleExportTree(SimpleExportTree):
    """
    Файл данных по контактной информации.
    В этом файле выгружается контактная информация
    для каждого абонента - ФИО, телефон и факс контактного лица.
    """

    def get_remote_ftp_file_name(self):
        return f"ISP/abonents/contact_phones_v1_{format_fname(self._event_time)}.txt"

    @classmethod
    def get_export_type(cls):
        return ExportStampTypeEnum.CUSTOMER_CONTACT

    def export(self, data, many: bool, *args, **kwargs):
        ser = individual_entity_serializers.CustomerContactObjectFormat(data=data, many=many)
        ser.is_valid(raise_exception=True)
        return ser.data


class CustomerContractExportTree(ExportTree[CustomerContractModel]):
    """
    Файл данных по договорам.
    В этом файле выгружаются данные по договорам абонентов.
    :return:
    """
    _contract_title = gettext('Contract default title')

    def get_remote_ftp_file_name(self):
        return f"ISP/abonents/contracts_{format_fname(self._event_time)}.txt"

    @classmethod
    def get_export_format_serializer(cls):
        return individual_entity_serializers.CustomerContractObjectFormat

    @classmethod
    def get_export_type(cls):
        return ExportStampTypeEnum.CUSTOMER_CONTRACT

    def get_items(self, queryset, legal_qs: QuerySet[CustomerLegalModel], *args, **kwargs):
        # Выгрузить договора физиков
        for item in self.filter_queryset(queryset=queryset):
            try:
                yield self.get_item(item)
            except ContinueIteration:
                continue

        # Выгрузить договоры филиалов юриков
        for legal in legal_qs.iterator():
            yield from self.get_legal_item(legal=legal)

    def get_legal_item(self, legal: CustomerLegalModel):
        for branch in legal.branches.all():
            yield {
                "contract_id": f"u{branch.pk}",
                "customer_id": branch.pk,
                "contract_start_date": legal.actual_start_time.date(),
                'contract_end_date': legal.actual_end_time.date() if legal.actual_end_time else None,
                "contract_number": legal.username,
                "contract_title": self._contract_title,
            }

    def get_item(self, contract: CustomerContractModel):
        return {
            "contract_id": contract.pk,
            "customer_id": contract.customer_id,
            "contract_start_date": contract.start_service_time.date(),
            'contract_end_date': contract.end_service_time.date() if contract.end_service_time else None,
            "contract_number": contract.contract_number,
            "contract_title": self._contract_title,
        }
