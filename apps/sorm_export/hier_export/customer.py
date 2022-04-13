from datetime import datetime
from typing import Iterable, Optional

from django.db.models import Subquery, OuterRef, Count
from django.utils.translation import gettext_lazy as _
from djing2.lib.logger import logger
from addresses.models import AddressModelTypes, AddressModel
from customer_contract.models import CustomerContractModel
from customers_legal.models import CustomerLegalModel
from customers.models import Customer
from sorm_export.models import (
    CommunicationStandardChoices,
    CustomerDocumentTypeChoices,
)
from sorm_export.serializers import individual_entity_serializers
from .base import (
    iterable_export_decorator,
    simple_export_decorator,
    format_fname,
    iterable_gen_export_decorator
)


def general_customer_filter_queryset():
    return Customer.objects.filter(is_active=True).annotate(
        contr_count=Count('customercontractmodel')
    ).filter(contr_count__gt=0)


def _addr2str(addr: Optional[AddressModel]) -> str:
    if not addr:
        return ''
    return str(addr.title)


@iterable_gen_export_decorator
def export_customer_root(customers: Iterable[Customer], event_time=None):
    """
    Файл данных по абонентам v1.
    В этом файле выгружается корневая запись всей иерархии
    данных об абоненте, ошибки загрузки в этом файле приводят
    к каскадным ошибкам загрузки связанных данных в других файлах.
    :return: data, filename
    """

    def _gen():
        lgl_sb = CustomerLegalModel.objects.filter(branches__id=OuterRef('pk')).values('pk')
        # FIXME: Абоненты без договора не выгружаются.
        #  Нужно выгружать только тех, у кого есть основной договор.
        #  Нужно сделать типы договоров, чтоб проверять только по 'основному'.
        #  Типы договоров, например: Основной, iptv, voip, доп оборудование, и.т.д.

        for customer in customers.annotate(
            legal_id=Subquery(lgl_sb)
        ):
            # TODO: optimize
            contract = customer.customercontractmodel_set.first()
            if contract is None:
                logger.error('Contract for customer: "%s" not found' % customer)
                continue
            yield {
                "customer_id": customer.pk,
                "legal_customer_id": customer.legal_id if customer.legal_id else customer.pk,
                "contract_start_date": contract.start_service_time.date(),
                "customer_login": customer.username,
                "communication_standard": CommunicationStandardChoices.ETHERNET.value,
            }

    return (
        individual_entity_serializers.CustomerRootObjectFormat,
        _gen,
        f"ISP/abonents/abonents_v1_{format_fname(event_time)}.txt",
    )


@iterable_export_decorator
def export_contract(contracts, event_time=None):
    """
    Файл данных по договорам.
    В этом файле выгружаются данные по договорам абонентов.
    :return:
    """

    def gen(contract):
        return {
            "contract_id": contract.pk,
            "customer_id": contract.customer_id,
            "contract_start_date": contract.start_service_time.date(),
            'contract_end_date': contract.end_service_time.date() if contract.end_service_time else None,
            "contract_number": contract.contract_number,
            "contract_title": "Договор на оказание услуг связи",
            # "contract_title": contract.title,
        }

    return (
        individual_entity_serializers.CustomerContractObjectFormat,
        gen,
        contracts,
        f"ISP/abonents/contracts_{format_fname(event_time)}.txt",
    )


def _addr_get_parent(addr: AddressModel, err_msg=None) -> Optional[AddressModel]:
    # TODO: Cache address hierarchy
    addr_parent_region = addr.get_address_item_by_type(
        addr_type=AddressModelTypes.STREET
    )
    if not addr_parent_region:
        if err_msg is not None:
            logger.error(err_msg)
        return
    return addr_parent_region


@iterable_export_decorator
def export_access_point_address(customers: Iterable[Customer], event_time=None):
    """
    Файл выгрузки адресов точек подключения, версия 1.
    В этом файле выгружается информация о точках подключения оборудования - реальном адресе,
    на котором находится оборудование абонента, с помощью которого он пользуется услугами оператора связи.
    TODO: Выгружать адреса абонентов чъё это оборудование.
    TODO: Записывать адреса к устройствам абонентов. Заполнять при создании устройства.
    Сейчас у нас оборудование абонента ставится у абонента дома, так что это тот же адрес
    что и у абонента.
    """

    def gen(customer: Customer):
        if not hasattr(customer, "address"):
            logger.error(_('Customer "%s" [%s] has no address') % (customer, customer.username))
            return
        addr = customer.address
        if not addr:
            logger.error(_('Customer "%s" [%s] has no address') % (customer, customer.username))
            return
        if not addr.parent_addr:
            logger.error(_('Customer "%s" has address without parent address object') % customer)
            return
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
        addr_parent_region = _addr_get_parent(
            addr,
            _('Customer "%s" with login "%s" address has no parent street element') % (
                customer,
                customer.username
            )
        )
        if not addr_parent_region:
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
            "parent_id_ao": addr_parent_region.pk if addr_parent_region else None,
            "house_num": addr_house or None,
            "builing": addr_building,
            "building_corpus": addr_corpus or None,
            "full_address": addr.full_title(),
            "actual_start_time": contract.start_service_time,
            'actual_end_time': contract.end_service_time or None
        }

    return (
        individual_entity_serializers.CustomerAccessPointAddressObjectFormat,
        gen,
        customers.select_related(
            "address", "address__parent_addr"
        ),
        f"ISP/abonents/ap_region_v1_{format_fname(event_time)}.txt",
    )


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


@iterable_export_decorator
def export_individual_customer(customers_queryset, event_time=None):
    """
    Файл выгрузки данных о физическом лице, версия 2
    В этом файле выгружается информация об абонентах, у которых контракт заключён с физическим лицом.
    Выгружаются только абоненты с паспортными данными.
    """

    def gen(customer: Customer):
        if not hasattr(customer, "passportinfo"):
            logger.error('Customer "%s" has no passport info' % customer)
            return
        passport = customer.passportinfo
        if not passport:
            logger.error(_('Customer "%s" [%s] has no passport info') % (customer, customer.username))
            return
        addr = passport.registration_address
        if not addr:
            logger.error(_('Customer "%s" [%s] has no address in passport') % (customer, customer.username))
            return

        addr_parent_region = _addr_get_parent(
            addr,
            _('Customer "%s" with login "%s" passport registration address has no parent street element') % (
                customer,
                customer.username
            )
        )
        if not addr_parent_region:
            return

        actual_start_date = customer.contract_date if customer.contract_date else datetime(
            customer.create_date.year,
            customer.create_date.month,
            customer.create_date.day
        )
        full_fname = customer.get_full_name()

        addr_house = addr.get_address_item_by_type(
            addr_type=AddressModelTypes.HOUSE
        )
        addr_building = addr.get_address_item_by_type(
            addr_type=AddressModelTypes.BUILDING
        )
        addr_corp = addr.get_address_item_by_type(
            addr_type=AddressModelTypes.BUILDING
        )
        r = {
            "contract_id": customer.pk,
            "name": full_fname,
            "surname": full_fname,
            "birthday": customer.birth_day,
            "document_type": CustomerDocumentTypeChoices.PASSPORT_RF,
            "document_serial": passport.series,
            "document_number": passport.number,
            "document_distributor": passport.distributor,
            "passport_code": passport.division_code or "",
            "passport_date": passport.date_of_acceptance,
            "house": addr.title,
            "parent_id_ao": addr_parent_region.pk,
            "house_num": addr_house.title if addr_house else None,
            "building": addr_building.title if addr_building else None,
            "building_corpus": addr_corp.title if addr_corp else None,
            "actual_start_time": actual_start_date,
            # 'actual_end_time':
            "customer_id": customer.pk,
        }
        surname, name, last_name = customer.split_fio()
        if surname is not None:
            r['surname'] = surname
        if name is not None:
            r['name'] = name
        if last_name is not None:
            r['last_name'] = last_name
        return r

    contracts_q = CustomerContractModel.objects.filter(
        customer_id=OuterRef('pk'),
        is_active=True
    ).values('start_service_time')

    _report_about_customers_no_have_passport(
        customers_queryset.filter(passportinfo=None)
    )

    return (
        individual_entity_serializers.CustomerIndividualObjectFormat,
        gen,
        customers_queryset.exclude(passportinfo=None).select_related(
            "group", "passportinfo"
        ).annotate(
            contract_date=Subquery(contracts_q)
        ),
        f"ISP/abonents/fiz_v2_{format_fname(event_time)}.txt",
    )


@iterable_gen_export_decorator
def export_legal_customer(legal_customers: Iterable[CustomerLegalModel], event_time=None):
    """
    Файл выгрузки данных о юридическом лице версия 5.
    В этом файле выгружается информация об абонентах у которых контракт заключён с юридическим лицом.
    """

    def _iter_customers(legal):
        # TODO: Optimize
        #  оптимизаровать запросы к бд
        #  Сейчас на каждый запрос адреса из иерархии адресов делается отдельный запрос в бд.
        for customer in legal.branches.annotate(
            contr_count=Count('customercontractmodel')
        ).filter(contr_count__gt=0, is_active=True):
            addr: AddressModel = legal.address
            if not addr:
                continue

            if not legal.post_address:
                post_addr = addr
            else:
                post_addr = legal.post_address

            if not legal.delivery_address:
                delivery_addr = legal.address
            else:
                delivery_addr = legal.delivery_address

            addr_parent_region = _addr_get_parent(
                addr,
                _('Legal customer "%s" with login "%s" address has no parent street element') % (
                    legal,
                    legal.username
                )
            )
            if not addr_parent_region:
                return
            post_addr_parent_region = _addr_get_parent(
                post_addr,
                _('Legal customer "%s" with login "%s" post address has no parent street element') % (
                    legal,
                    legal.username
                )
            )
            delivery_addr_parent_region = _addr_get_parent(
                delivery_addr,
                _('Legal customer "%s" with login "%s" delivery address has no parent street element') % (
                    legal,
                    legal.username
                )
            )
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
                'customer_id': customer.pk,
            }
            if hasattr(legal, 'legalcustomerbankmodel'):
                bank_info = getattr(legal, 'legalcustomerbankmodel')
                res.update({
                    'customer_bank': bank_info.title,
                    'customer_bank_num': bank_info.number,
                })
            yield res

    def _gen():
        legals = legal_customers.select_related('address', 'delivery_address', 'post_address')
        for legal in legals:
            yield from _iter_customers(legal)

    return (
        individual_entity_serializers.CustomerLegalObjectFormat,
        _gen,
        f'ISP/abonents/jur_v5_{format_fname(event_time)}.txt'
    )


@simple_export_decorator
def export_contact(customer_tels, event_time=None):
    """
    Файл данных по контактной информации.
    В этом файле выгружается контактная информация
    для каждого абонента - ФИО, телефон и факс контактного лица.
    """
    ser = individual_entity_serializers.CustomerContactObjectFormat(data=customer_tels, many=True)
    return ser, f"ISP/abonents/contact_phones_v1_{format_fname(event_time)}.txt"

