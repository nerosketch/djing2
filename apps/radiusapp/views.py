from datetime import datetime
from typing import Optional, Mapping, Any

from asyncpg import Record
from asyncpg.pool import PoolConnectionProxy
from django.utils.translation import gettext as _
from djing2.lib.fastapi.default_response_class import CompatibleJSONResponse
from fastapi import APIRouter, HTTPException, Body, Depends
from netaddr import EUI
from starlette import status
from starlette.responses import Response

from customers.models import Customer
from services.models import CustomerService
from djing2.lib import LogicError, safe_int
from djing2.lib.logger import logger
from networks.models import CustomerIpLeaseModel, NetworkIpPoolKind
from networks.tasks import async_finish_session_task
from radiusapp import custom_signals
from radiusapp.schemas import CustomerServiceRequestSchema
from radiusapp.vendor_base import (
    AcctStatusType,
    CustomerServiceLeaseResult,
    SpeedInfoStruct
)
from radiusapp.vendors import VendorManager
from radiusapp.db_asession import db_connection_dependency
from radiusapp import tasks

# TODO: Also protect requests by hash
router = APIRouter(
    prefix='/radius/customer',
    tags=['RADIUS']
)


def _bad_ret(text: str, custom_status=status.HTTP_400_BAD_REQUEST, log_err=True) -> CompatibleJSONResponse:
    if log_err:
        logger.error(msg=str(text))
    return CompatibleJSONResponse({
        "Reply-Message": text
    }, status_code=custom_status)


def _acct_unknown(_, tx=''):
    logger.error('Unknown acct: %s' % tx)
    return _bad_ret("Bad Acct-Status-Type: %s" % tx, custom_status=status.HTTP_200_OK)


async def _assign_global_guest_lease(
    customer_mac, vlan_id: Optional[int], svid: Optional[int],
    session_id: Optional[str], radius_username: Optional[str],
    conn: PoolConnectionProxy,
):
    """Create global guest lease without customer"""

    sql = (
        "UPDATE networks_ip_leases n SET "
            "mac_address=$1::macaddr, "
            "state=true, "
            "input_octets=0, "
            "output_octets=0, "
            "input_packets=0, "
            "output_packets=0, "
            "cvid=$2::smallint, "
            "svid=$3::smallint, "
            "lease_time=now(), "
            "last_update=now(), "
            "session_id=$4::uuid, "
            "radius_username=$5 "
        "WHERE id IN ( "
            "SELECT l.id "
            "FROM networks_ip_leases l "
            "LEFT JOIN networks_ip_pool p ON l.pool_id = p.id "
            "WHERE p.kind = $6::smallint "
              "AND NOT l.state "
            "LIMIT 1 "
        ") "
        "RETURNING n.ip_address, n.mac_address, n.is_dynamic"
    )

    ip_result = await conn.fetchrow(
        sql, str(customer_mac), vlan_id,
        svid, session_id, radius_username,
        NetworkIpPoolKind.NETWORK_KIND_GUEST.value
    )
    if ip_result is None:
        raise BadRetException(
            detail='Failed to assign guest address',
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    return CustomerServiceLeaseResult(
        ip_address=ip_result['ip_address'],
        mac_address=ip_result['mac_address'],
        is_dynamic=ip_result['is_dynamic']
    )


async def _find_and_assign_lease(
    customer_mac: EUI, pool_kind: NetworkIpPoolKind,
    customer_id: int, vlan_id: int, service_vlan_id: int,
    radius_unique_id: str, radius_username: str,
    conn: PoolConnectionProxy
):
    sql = """WITH lease(id, ip_address) AS (
    SELECT nil.id, nil.ip_address
    FROM networks_ip_leases nil
             LEFT JOIN networks_ip_pool nip ON (nil.pool_id = nip.id)
             LEFT JOIN networks_vlan nv ON (nip.vlan_if_id = nv.id)
    WHERE nv.vid = $1::smallint
      AND nip.is_dynamic
      AND nip.kind = $2::smallint
      AND nil.ip_address >= nip.ip_start
      AND nil.ip_address <= nip.ip_end
      AND nil.is_dynamic
      AND (
            (nil.customer_id = $3::integer AND nil.mac_address = $4::macaddr)
                OR
            (nil.customer_id IS NULL AND nil.mac_address IS NULL)
        )
      AND NOT nil.state
    LIMIT 1
)
UPDATE networks_ip_leases unil
SET mac_address     = $4::macaddr,
    customer_id     = $3::integer,
    input_octets    = 0,
    output_octets   = 0,
    input_packets   = 0,
    output_packets  = 0,
    cvid            = $1::smallint,
    svid            = $5::smallint,
    lease_time      = now(),
    last_update     = now(),
    session_id      = $6::uuid,
    radius_username = $7
WHERE unil.id IN (SELECT id FROM lease)
RETURNING (SELECT ip_address FROM lease);
"""
    ip = await conn.fetchval(sql, vlan_id, pool_kind.value, customer_id, str(customer_mac),
                             service_vlan_id, radius_unique_id, radius_username)
    return ip


@router.post('/auth/{vendor_name}/')
async def auth(vendor_name: str, request_data: Mapping[str, Any] = Body(...),
               conn: PoolConnectionProxy = Depends(db_connection_dependency)):
    vendor_manager = VendorManager(vendor_name=vendor_name)

    opt82 = vendor_manager.get_opt82(data=request_data)
    if opt82 is None:
        return _bad_ret("Fetch opt82 info system fail")
    agent_remote_id, agent_circuit_id = opt82

    customer_mac = vendor_manager.get_customer_mac(request_data)
    if not customer_mac:
        return _bad_ret("Customer mac is required")

    vlan_id = vendor_manager.get_vlan_id(request_data)
    service_vlan_id = vendor_manager.get_service_vlan_id(request_data)
    radius_unique_id = vendor_manager.get_radius_unique_id(request_data)
    radius_username = vendor_manager.get_radius_username(request_data)

    if all([agent_remote_id, agent_circuit_id]):
        dev_mac, dev_port = vendor_manager.build_dev_mac_by_opt82(
            agent_remote_id=agent_remote_id,
            agent_circuit_id=agent_circuit_id
        )
        if not dev_mac:
            return _bad_ret("Failed to parse option82")

        db_info = await _get_customer_and_service_and_lease_by_device_credentials(
            conn=conn,
            device_mac=dev_mac,
            customer_mac=customer_mac,
            device_port=dev_port
        )

        if db_info is None:
            db_info = await _assign_global_guest_lease(
                customer_mac=customer_mac,
                vlan_id=vlan_id,
                svid=service_vlan_id,
                session_id=radius_unique_id,
                radius_username=radius_username,
                conn=conn
            )
        if not db_info.ip_address:
            # assign new lease
            #  with transaction.atomic():
            # find one free lease, and update it for customer
            db_info.ip_address = await _find_and_assign_lease(
                customer_mac=customer_mac,
                pool_kind=NetworkIpPoolKind.NETWORK_KIND_INTERNET,
                customer_id=db_info.id,
                vlan_id=vlan_id,
                service_vlan_id=service_vlan_id,
                radius_unique_id=radius_unique_id,
                radius_username=radius_username,
                conn=conn
            )
            db_info.mac_address = customer_mac
    else:
        # auth by mac. Find static lease.
        db_info = await _get_customer_and_service_and_lease_by_mac(
            customer_mac=customer_mac,
            conn=conn
        )
        if db_info is None:
            #  Create global guest lease without customer
            db_info = await _assign_global_guest_lease(
                customer_mac=customer_mac,
                vlan_id=vlan_id,
                svid=service_vlan_id,
                session_id=radius_unique_id,
                radius_username=radius_username,
                conn=conn
            )

    # If ip does not exists, then assign guest lease
    if not db_info.ip_address:
        # assign new guest lease
        db_info.ip_address = await _find_and_assign_lease(
            customer_mac=customer_mac,
            pool_kind=NetworkIpPoolKind.NETWORK_KIND_GUEST,
            customer_id=db_info.id,
            vlan_id=vlan_id,
            service_vlan_id=service_vlan_id,
            radius_unique_id=radius_unique_id,
            radius_username=radius_username,
            conn=conn
        )
        db_info.mac_address = customer_mac

    if not db_info.ip_address:
        logger.error('Failed to assign ip address for mac: %s, opt82: %s' % (customer_mac, str(opt82)))
        return _bad_ret('Failed to assign ip address')

    # Return auth response
    try:
        r = vendor_manager.get_auth_session_response(
            db_result=db_info
        )
        if not r:
            logger.error('Empty auth session response')
            return Response(
                'Empty auth session response',
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        response, code = r
        return CompatibleJSONResponse(response, status_code=code)
    except LogicError as err:
        return _bad_ret(f'{str(err)}')
    except BadRetException as err:
        return _bad_ret(f'{str(err)}', log_err=err.show_err)


@router.post('/get_service/')
def get_service(data: CustomerServiceRequestSchema):
    customer_ip = data.customer_ip
    # password = data.get('password')

    customer_service = CustomerService.get_user_credentials_by_ip(ip_addr=customer_ip)
    if customer_service is None:
        return Response({
            "Reply-Message": "Customer service not found"
        }, status_code=status.HTTP_404_NOT_FOUND)

    sess_time = customer_service.calc_remaining_time()
    return Response({
        "ip": customer_ip,
        "session_time": int(sess_time.total_seconds()),
        "speed_in": customer_service.service.speed_in,
        "speed_out": customer_service.service.speed_out,
    })


@router.post('/acct/{vendor_name}/')
async def acct(
    vendor_name: str,
    request_data: Mapping[str, Any] = Body(...),
    conn: PoolConnectionProxy = Depends(db_connection_dependency)
):
    if not vendor_name:
        return _bad_ret('Empty vendor name')

    vendor_manager = VendorManager(vendor_name=vendor_name)
    bras_service_name = vendor_manager.get_rad_val(request_data, "ERX-Service-Session", str)
    if not bras_service_name:
        logger.info('ERX-Service-Session not found')
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    request_type = vendor_manager.get_acct_status_type(request_data)
    if not request_type:
        logger.error('request_type is None')
        return _acct_unknown(None, 'request_type is None')

    try:
        request_type_fn = _acct_status_type_map.get(request_type)
        if request_type_fn is None:
            err = 'request_type_fn is None, (request_type=%s)' % request_type
            logger.error(err)
            return _acct_unknown(None, err)
        return await request_type_fn(
            vendor_manager=vendor_manager,
            request_data=request_data,
            bras_service_name=bras_service_name,
            conn=conn
        )
    except BadRetException as err:
        return _bad_ret(str(err), log_err=err.show_err)


class BadRetException(HTTPException):
    show_err: bool

    def __init__(self, status_code=status.HTTP_400_BAD_REQUEST, detail=None,
                 show_err=True, *args, **kwargs):
        self.show_err = show_err
        super().__init__(
            status_code=status_code,
            detail=detail or _('exception from radius.'),
            *args, **kwargs
        )

    def __str__(self):
        return f'{self.__class__.__name__}: {self.detail}'


class CustomerNotFoundException(BadRetException): pass
class Opt82NotExistsException(BadRetException): pass
class Opt82NotAllExistsException(BadRetException): pass


def _build_srv_result_from_db_result(row: Record) -> CustomerServiceLeaseResult:
    si, so, sb = row['speed_in'], row['speed_out'], row['speed_burst']

    if all([si, so]):
        speed = SpeedInfoStruct(
            speed_in=si,
            speed_out=so,
            burst_in=sb,
            burst_out=sb
        )
    else:
        speed = None
    return CustomerServiceLeaseResult(
        id=row.get('uid'),
        username=row.get('uname'),
        is_active=row.get('acc_is_active', False),
        balance=row.get('acc_balance'),
        is_dynamic_ip=row.get('acc_is_dynamic_ip'),
        auto_renewal_service=row.get('acc_auto_renewal_service'),
        current_service_id=row.get('customer_service_id'),
        dev_port_id=row.get('dev_port_id'),
        device_id=row.get('device_id'),
        gateway_id=row.get('gateway_id'),
        speed=speed,
        ip_address=row.get('ip_address'),
        mac_address=row.get('mac_address'),
        is_dynamic=row.get('ip_is_dynamic')
    )


async def _get_customer_and_service_and_lease_by_device_credentials(
    conn: PoolConnectionProxy,
    device_mac: EUI, customer_mac: EUI, device_port: int = 0,
) -> Optional[CustomerServiceLeaseResult]:
    sql = (
        "SELECT ba.id as uid, "
          "ba.username as uname, "
          "ba.is_active as acc_is_active, "
          "c.balance as acc_balance, "
          "c.is_dynamic_ip as acc_is_dynamic_ip, "
          "c.auto_renewal_service as acc_auto_renewal_service, "
          "cs.id as customer_service_id, "
          "c.dev_port_id, "
          "c.device_id, "
          "c.gateway_id, "
          "srv.speed_in, "
          "srv.speed_out, "
          "srv.speed_burst, "
          "nip.ip_address, "
          "nip.mac_address, "
          "nip.is_dynamic as ip_is_dynamic "
        "FROM customers c "
          "LEFT JOIN device dv ON (dv.id = c.device_id) "
          "LEFT JOIN device_port dp ON (c.dev_port_id = dp.id) "
          "LEFT JOIN device_dev_type_is_use_dev_port ddtiudptiu ON (ddtiudptiu.dev_type = dv.dev_type) "
          "LEFT JOIN base_accounts ba ON c.baseaccount_ptr_id = ba.id "
          "LEFT JOIN customer_service cs ON cs.customer_id = c.baseaccount_ptr_id "
          "LEFT JOIN services srv ON srv.id = cs.service_id "
          "LEFT JOIN networks_ip_leases nip ON ( "
            "nip.customer_id = c.baseaccount_ptr_id AND ( "
              "nip.mac_address = $1::MACADDR OR nip.mac_address IS NULL "
            ") "
          ") "
        "WHERE dv.mac_addr = $2::MACADDR "
        "AND ((NOT ddtiudptiu.is_use_dev_port) OR dp.num = $3::SMALLINT) "
        "LIMIT 1;"
    )
    row = await conn.fetchrow(sql, str(customer_mac), str(device_mac), device_port)
    if not row:
        return None
    return _build_srv_result_from_db_result(row=row)


async def _get_customer_and_service_and_lease_by_mac(
    customer_mac: EUI,
    conn: PoolConnectionProxy
) -> Optional[CustomerServiceLeaseResult]:
    sql = (
        "SELECT ba.id as uid, "
          "ba.username as uname, "
          "ba.is_active as acc_is_active, "
          "c.balance as acc_balance, "
          "c.is_dynamic_ip as acc_is_dynamic_ip, "
          "c.auto_renewal_service as acc_auto_renewal_service, "
          "cs.id as customer_service_id, "
          "c.dev_port_id, "
          "c.device_id, "
          "c.gateway_id, "
          "srv.speed_in, "
          "srv.speed_out, "
          "srv.speed_burst, "
          "nip.ip_address, "
          "nip.mac_address, "
          "false as ip_is_dynamic "
        "FROM customers c "
          "LEFT JOIN base_accounts ba ON ba.id = c.baseaccount_ptr_id "
          "LEFT JOIN customer_service cs ON cs.customer_id = c.baseaccount_ptr_id "
          "LEFT JOIN services srv ON srv.id = cs.service_id "
          "LEFT JOIN networks_ip_leases nip ON nip.customer_id = c.baseaccount_ptr_id "
        "WHERE "
          "nip.mac_address = $1::MACADDR "
        "LIMIT 1"
    )
    row = await conn.fetchrow(sql, str(customer_mac))
    if not row:
        return None
    return _build_srv_result_from_db_result(row=row)


async def _acct_start(
    vendor_manager: VendorManager, request_data: Mapping[str, Any],
    bras_service_name: str,
    conn: PoolConnectionProxy
) -> Response:
    """Accounting start handler."""
    if not vendor_manager or not vendor_manager.vendor_class:
        return _bad_ret(
            'No vendor manager exists',
            custom_status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    if not request_data:
        return _bad_ret("Empty request")

    ip = vendor_manager.vendor_class.get_rad_val(request_data, "Framed-IP-Address", str)
    if not ip:
        return _bad_ret(
            "Request has no ip information (Framed-IP-Address)",
            custom_status=status.HTTP_200_OK
        )

    radius_username = vendor_manager.get_radius_username(request_data)
    if not radius_username:
        return _bad_ret(
            "Request has no username",
            custom_status=status.HTTP_200_OK
        )

    customer_mac = vendor_manager.get_customer_mac(request_data)
    if not customer_mac:
        return _bad_ret("Customer mac is required")

    radius_unique_id = vendor_manager.get_radius_unique_id(request_data)
    if not radius_unique_id:
        return _bad_ret('Bad unique id from radius request')

    now = datetime.now()

    try:
        customer = await _find_customer(
            data=request_data,
            vendor_manager=vendor_manager,
            conn=conn
        )
        sql = (
            "UPDATE networks_ip_leases n SET "
                "mac_address = $1::macaddr, "
                "input_octets=0, "
                "output_octets=0, "
                "input_packets=0, "
                "output_packets=0, "
                "state=True, "
                "session_id=$2::uuid, "
                "radius_username=$3, "
                "last_update=now() "
            "WHERE ip_address=$4::inet"
        )
        await conn.execute(sql, str(customer_mac), radius_unique_id, radius_username, ip)
    except (Opt82NotExistsException, Opt82NotAllExistsException):
        # auth by mac. Find static lease.
        sql = (
            "UPDATE networks_ip_leases l SET "
                "state=true "
            "FROM customers c "
            "LEFT JOIN base_accounts ba on c.baseaccount_ptr_id = ba.id "
                "WHERE l.customer_id = c.baseaccount_ptr_id AND "
                    "l.mac_address=$1::macaddr AND "
                    "not l.is_dynamic AND "
                    "l.customer_id IS NOT NULL "
            "RETURNING c.baseaccount_ptr_id, c.balance, c.is_dynamic_ip, "
            "c.auto_renewal_service, c.dev_port_id, c.device_id, c.gateway_id, "
            "c.group_id, c.address_id, ba.username, ba.is_active, ba.is_admin, "
            "ba.is_superuser"
        )
        row = await conn.fetchrow(sql, str(customer_mac))
        if not row:
            return _bad_ret(
                'Free lease with mac="%s" not found' % customer_mac,
                custom_status=status.HTTP_404_NOT_FOUND
            )
        customer = Customer(
            pk=row.get('baseaccount_ptr_id'),
            username=row.get('username'),
            is_active=row.get('is_active'),
            is_admin=row.get('is_admin'),
            is_superuser=row.get('is_superuser'),
            balance=row.get('balance'),
            is_dynamic_ip=row.get('is_dynamic_ip', False),
            auto_renewal_service=row.get('auto_renewal_service'),
            dev_port_id=row.get('dev_port_id'),
            device_id=row.get('device_id'),
            gateway_id=row.get('gateway_id'),
            group_id=row.get('group_id'),
            address_id=row.get('address_id')
        )

    custom_signals.radius_acct_start_signal.send(
        sender=CustomerIpLeaseModel,
        instance=None,
        data=request_data,
        ip_addr=ip,
        customer_mac=customer_mac,
        radius_username=radius_username,
        customer_ip_lease=None,
        customer=customer,
        radius_unique_id=radius_unique_id,
        event_time=now,
    )

    return Response(status_code=status.HTTP_204_NO_CONTENT)


async def _acct_stop(
    vendor_manager: VendorManager,
    request_data: Mapping[str, Any],
    bras_service_name: str,
    conn: PoolConnectionProxy
) -> Response:
    ip = vendor_manager.get_rad_val(request_data, "Framed-IP-Address", str)
    radius_unique_id = vendor_manager.get_radius_unique_id(request_data)
    customer_mac = vendor_manager.get_customer_mac(request_data)

    counters = vendor_manager.get_counters(data=request_data)

    sql = (
        "UPDATE networks_ip_leases l SET "
            "state=false, "
            "input_octets=$1::bigint, "
            "output_octets=$2::bigint, "
            "input_packets=$3::bigint, "
            "output_packets=$4::bigint, "
            "last_update=now() "
        "FROM customers c "
            "LEFT JOIN base_accounts ba ON c.baseaccount_ptr_id = ba.id "
        "WHERE l.ip_address=$5::inet "
            "RETURNING c.baseaccount_ptr_id, c.balance, c.is_dynamic_ip, "
                "c.auto_renewal_service, c.dev_port_id, c.device_id, c.gateway_id, "
            "c.group_id, c.address_id, ba.username, ba.is_active, ba.is_admin, "
            "ba.is_superuser;"
    )

    row = await conn.fetchrow(sql, counters.input_octets,
                              counters.output_octets, counters.input_packets,
                              counters.output_packets, ip)

    customer = Customer(
        pk=row.get('baseaccount_ptr_id'),
        username=row.get('username'),
        is_active=row.get('is_active'),
        is_admin=row.get('is_admin'),
        is_superuser=row.get('is_superuser'),
        balance=row.get('balance'),
        is_dynamic_ip=row.get('is_dynamic_ip', False),
        auto_renewal_service=row.get('auto_renewal_service'),
        dev_port_id=row.get('dev_port_id'),
        device_id=row.get('device_id'),
        gateway_id=row.get('gateway_id'),
        group_id=row.get('group_id'),
        address_id=row.get('address_id')
    )

    custom_signals.radius_acct_stop_signal.send(
        sender=CustomerIpLeaseModel,
        instance=CustomerIpLeaseModel(),
        data=request_data,
        counters=counters,
        ip_addr=ip,
        radius_unique_id=radius_unique_id,
        customer_mac=customer_mac,
        customer=customer
    )

    return Response(status_code=status.HTTP_204_NO_CONTENT)


# async version of networks.models.CustomerIpLeaseModel.find_customer_by_device_credentials
async def _find_customer_by_device_credentials_async(
    conn: PoolConnectionProxy,
    device_mac: EUI,
    device_port: int
):
    sql = (
        "SELECT ba.id as uid, ba.last_login, ba.is_superuser, ba.username, "
        "ba.fio, ba.birth_day, ba.is_active, ba.is_admin, "
        "ba.telephone, ba.create_date, ba.last_update_time, "
        "cs.balance, cs.is_dynamic_ip, cs.auto_renewal_service, "
        "cs.dev_port_id, cs.device_id, "
        "cs.gateway_id, cs.group_id, cs.address_id "
        "FROM customers cs "
        "LEFT JOIN device dv ON (dv.id = cs.device_id) "
        "LEFT JOIN device_port dp ON (cs.dev_port_id = dp.id) "
        "LEFT JOIN device_dev_type_is_use_dev_port ddtiudptiu ON (ddtiudptiu.dev_type = dv.dev_type) "
        "LEFT JOIN base_accounts ba ON cs.baseaccount_ptr_id = ba.id "
        "WHERE dv.mac_addr = $1::MACADDR "
        "AND ((NOT ddtiudptiu.is_use_dev_port) OR dp.num = $2::SMALLINT) "
        "LIMIT 1;"
    )
    row = await conn.fetchrow(sql, str(device_mac), device_port)
    if not row:
        return
    return Customer(
        pk=row.get('uid'),
        last_login=row.get('last_login'),
        is_superuser=row.get('is_superuser'),
        username=row.get('username'),
        fio=row.get('fio'),
        birth_day=row.get('birth_day'),
        is_active=row.get('is_active'),
        is_admin=row.get('is_admin'),
        telephone=row.get('telephone'),
        create_date=row.get('create_date'),
        last_update_time=row.get('last_update_time'),
        balance=row.get('balance'),
        is_dynamic_ip=row.get('is_dynamic_ip'),
        auto_renewal_service=row.get('auto_renewal_service'),
        dev_port_id=row.get('dev_port_id'),
        device_id=row.get('device_id'),
        gateway_id=row.get('gateway_id'),
        group_id=row.get('group_id'),
        address_id=row.get('address_id'),
    )


async def _find_customer(
    data: Mapping[str, Any],
    vendor_manager: VendorManager,
    conn: PoolConnectionProxy
) -> Customer:
    opt82 = vendor_manager.get_opt82(data=data)
    if not opt82 or opt82 == (None, None):
        raise Opt82NotExistsException(
            detail="Failed fetch opt82 info",
            show_err=False
        )
    agent_remote_id, agent_circuit_id = opt82
    if all([agent_remote_id, agent_circuit_id]):
        dev_mac, dev_port = vendor_manager.build_dev_mac_by_opt82(
            agent_remote_id=agent_remote_id,
            agent_circuit_id=agent_circuit_id
        )
        if not dev_mac:
            raise BadRetException(
                detail='opt82 has no device mac: (%(ari)s, %(aci)s)' % {
                    'ari': str(agent_remote_id),
                    'aci': str(agent_circuit_id)
                }
            )

        customer = await _find_customer_by_device_credentials_async(
            device_mac=dev_mac,
            device_port=dev_port,
            conn=conn
        )
        if not customer:
            raise CustomerNotFoundException(
                detail='Customer not found by device: dev_mac=%(dev_mac)s, dev_port=%(dev_port)s' % {
                    'dev_mac': str(dev_mac),
                    'dev_port': str(dev_port),
                },
                status_code=status.HTTP_404_NOT_FOUND
            )
        return customer
    raise Opt82NotAllExistsException(
        detail='not all opt82 %s' % str(opt82),
        status_code=status.HTTP_200_OK
    )


async def _acct_update(
    vendor_manager: VendorManager,
    request_data: Mapping[str, Any],
    bras_service_name: str,
    conn: PoolConnectionProxy
) -> Response:
    radius_unique_id = vendor_manager.get_radius_unique_id(request_data)
    if not radius_unique_id:
        return _bad_ret(
            "Request has no unique id",
            custom_status=status.HTTP_200_OK
        )

    customer_mac = vendor_manager.get_customer_mac(request_data)
    if not customer_mac:
        return _bad_ret("Customer mac is required")
    radius_username = vendor_manager.get_radius_username(request_data)
    if not radius_username:
        return _bad_ret(
            "Request has no username",
            custom_status=status.HTTP_200_OK
        )
    ip = vendor_manager.get_rad_val(request_data, "Framed-IP-Address", str)
    counters = vendor_manager.get_counters(request_data)

    try:
        customer = await _find_customer(
            data=request_data,
            vendor_manager=vendor_manager,
            conn=conn
        )
    except CustomerNotFoundException as err:
        logger.error('Session with not customer in db: uname="%s", details: %s' % (
            radius_username, err.detail
        ))
        async_finish_session_task.delay(
            radius_uname=radius_username
        )
        raise err
    except Opt82NotExistsException as err:
        # TODO: update fixed mac
        raise err

    async with conn.transaction():
        exists = await conn.fetchval(
            "select id from networks_ip_leases where ip_address=$1::inet AND customer_id=$2 limit 1 for update",
            str(ip), customer.pk,
        )
        if exists is not None:
            # just update counters
            await conn.execute(
                "update networks_ip_leases l "
                "set last_update=now(), "
                    "input_octets=$3::bigint, "
                    "output_octets=$4::bigint, "
                    "input_packets=$5::bigint, "
                    "output_packets=$6::bigint, "
                    "state=true, "
                    "session_id=$7::uuid, "
                    "radius_username=$8, "
                    "mac_address=$9::macaddr "
                "where l.ip_address=$1::inet and l.customer_id=$2::integer;",
                str(ip), customer.pk, counters.input_octets,
                counters.output_octets, counters.input_packets,
                counters.output_packets, str(radius_unique_id),
                radius_username, str(customer_mac)
            )
        else:
            # create lease on customer profile if it not exists
            vlan_id = vendor_manager.get_vlan_id(request_data)
            service_vlan_id = vendor_manager.get_service_vlan_id(request_data)
            await conn.execute(
                "update networks_ip_leases l "
                "set customer_id=$2::integer, "
                    "mac_address=$9::macaddr, "
                    "input_octets=$3::bigint, "
                    "output_octets=$4::bigint, "
                    "input_packets=$5::bigint, "
                    "output_packets=$6::bigint, "
                    "state=true, "
                    "last_update=now(), "
                    "lease_time=now(), "
                    "session_id=$7::uuid, "
                    "radius_username=$8, "
                    "cvid=$10::smallint, "
                    "svid=$11::smallint "
                "where ip_address=$1::inet",
                str(ip), customer.pk, counters.input_octets,
                counters.output_octets, counters.input_packets,
                counters.output_packets, str(radius_unique_id),
                radius_username, str(customer_mac),
                safe_int(vlan_id), safe_int(service_vlan_id)
            )

    # Check for service synchronization
    tasks.check_and_control_session_task.delay(
        bras_service_name=bras_service_name,
        customer_id=customer.pk,
        radius_username=radius_username
    )
    custom_signals.radius_auth_update_signal.send(
        sender=CustomerIpLeaseModel,
        instance=None,
        data=request_data,
        counters=counters,
        radius_unique_id=radius_unique_id,
        ip_addr=ip,
        customer=customer,
        customer_mac=customer_mac
    )

    return Response(status_code=status.HTTP_204_NO_CONTENT)


_acct_status_type_map = {
    AcctStatusType.START: _acct_start,
    AcctStatusType.STOP: _acct_stop,
    AcctStatusType.UPDATE: _acct_update,
}
