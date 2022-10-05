from datetime import datetime
from typing import Optional, Mapping, Any

from customers.models import CustomerService, Customer
from django.db import connection
from django.db.models import F
from django.utils.translation import gettext_lazy as _
from djing2.lib import LogicError, safe_int
from djing2.lib.logger import logger
from djing2.lib.ws_connector import WsEventTypeEnum, send_data2ws
from fastapi import APIRouter, HTTPException, Body
from netaddr import EUI
from networks.models import CustomerIpLeaseModel, NetworkIpPoolKind
from networks.tasks import (
    async_change_session_inet2guest,
    async_change_session_guest2inet
)
from radiusapp import custom_signals
from radiusapp.schemas import CustomerServiceRequestSchema
from radiusapp.vendor_base import (
    AcctStatusType,
    CustomerServiceLeaseResult,
    SpeedInfoStruct, RadiusCounters
)
from radiusapp.vendors import VendorManager
from starlette import status
from starlette.responses import Response, JSONResponse

# TODO: Also protect requests by hash
router = APIRouter(
    prefix='/radius/customer',
    tags=['RADIUS']
)


def _acct_unknown(_, tx=''):
    logger.error('Unknown acct: %s' % tx)
    return _bad_ret("Bad Acct-Status-Type: %s" % tx, custom_status=status.HTTP_200_OK)


def _assign_global_guest_lease(customer_mac, vlan_id: Optional[int], svid: Optional[int],
                               now: datetime, session_id: Optional[str], radius_username: Optional[str]):
    """Create global guest lease without customer"""

    leases_qs = CustomerIpLeaseModel.objects.filter(
        pool__kind=NetworkIpPoolKind.NETWORK_KIND_GUEST.value,
        state=False,
    )[:1]
    updated_lease_count = CustomerIpLeaseModel.objects.filter(pk__in=leases_qs).update(
        mac_address=customer_mac,
        state=True,
        input_octets=0,
        output_octets=0,
        input_packets=0,
        output_packets=0,
        cvid=vlan_id,
        svid=svid,
        lease_time=now,
        last_update=now,
        session_id=session_id,
        radius_username=radius_username,
    )
    if updated_lease_count > 0:
        ipaddr = leases_qs.first()
        if ipaddr is not None:
            db_info = CustomerServiceLeaseResult(
                ip_address=ipaddr.ip_address
            )
            return db_info
    raise BadRetException(
        detail='Failed to assign guest address',
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
    )


def _update_leases(lease: CustomerIpLeaseModel, customer_mac: EUI,
                   customer_id: int, vlan_id: int, service_vlan_id: int,
                   radius_unique_id: str, radius_username: str,
                   curr_time: Optional[datetime] = None):
    if curr_time is None:
        curr_time = datetime.now()
    updated_lease_count = CustomerIpLeaseModel.objects.filter(pk__in=lease).update(
        mac_address=customer_mac,
        customer=customer_id,
        input_octets=0,
        output_octets=0,
        input_packets=0,
        output_packets=0,
        cvid=vlan_id,
        svid=service_vlan_id,
        state=False,  # Set True in acct start
        lease_time=curr_time,
        last_update=curr_time,
        session_id=radius_unique_id,
        radius_username=radius_username,
    )
    return updated_lease_count


@router.post('/auth/{vendor_name}/')
def auth(vendor_name: str, request_data: Mapping[str, str] = Body(...)):
    # Just find customer by credentials from request
    vendor_manager = VendorManager(vendor_name=vendor_name)

    opt82 = vendor_manager.get_opt82(data=request_data)
    if not opt82:
        return _bad_ret("Failed fetch opt82 info")
    agent_remote_id, agent_circuit_id = opt82

    customer_mac = vendor_manager.get_customer_mac(request_data)
    if not customer_mac:
        return _bad_ret("Customer mac is required")

    vlan_id = vendor_manager.get_vlan_id(request_data)
    service_vlan_id = vendor_manager.get_vlan_id(request_data)
    radius_unique_id = vendor_manager.get_radius_unique_id(request_data)
    radius_username = vendor_manager.get_radius_username(request_data)
    now = datetime.now()

    if all([agent_remote_id, agent_circuit_id]):
        dev_mac, dev_port = vendor_manager.build_dev_mac_by_opt82(
            agent_remote_id=agent_remote_id,
            agent_circuit_id=agent_circuit_id
        )
        if not dev_mac:
            return _bad_ret("Failed to parse option82")

        db_info = _get_customer_and_service_and_lease_by_device_credentials(
            device_mac=dev_mac,
            customer_mac=customer_mac,
            device_port=dev_port
        )

        if db_info is None:
            db_info = _assign_global_guest_lease(
                customer_mac=customer_mac,
                vlan_id=vlan_id,
                svid=service_vlan_id,
                now=now,
                session_id=radius_unique_id,
                radius_username=radius_username
            )
        if not db_info.ip_address:
            # assign new lease
            #  with transaction.atomic():
            # find one free lease, and update it for customer
            lease = CustomerIpLeaseModel.objects.filter(
                pool__vlan_if__vid=vlan_id,
                pool__is_dynamic=True,
                pool__kind=NetworkIpPoolKind.NETWORK_KIND_INTERNET,
                ip_address__gte=F('pool__ip_start'),
                ip_address__lte=F('pool__ip_end'),
                is_dynamic=F('pool__is_dynamic'),
                customer=None,
                cvid=0, svid=0,
                state=False
            )[:1]
            updated_lease_count = _update_leases(
                lease,
                customer_mac=customer_mac,
                customer_id=db_info.id,
                vlan_id=vlan_id,
                service_vlan_id=service_vlan_id,
                curr_time=now,
                radius_unique_id=radius_unique_id,
                radius_username=radius_username
            )
            if updated_lease_count > 0:
                lease = lease.only('ip_address').values('ip_address').first()
                if lease is not None and lease.get('ip_address') is not None:
                    db_info.ip_address = lease.get('ip_address')
    else:
        # auth by mac. Find static lease.
        db_info = _get_customer_and_service_and_lease_by_mac(
            customer_mac=customer_mac
        )
        if db_info is None:
            #  Create global guest lease without customer
            db_info = _assign_global_guest_lease(
                customer_mac=customer_mac,
                vlan_id=vlan_id,
                svid=service_vlan_id,
                now=now,
                session_id=radius_unique_id,
                radius_username=radius_username
            )

    # If ip does not exists, then assign guest lease
    if not db_info.ip_address:
        # assign new guest lease
        lease = CustomerIpLeaseModel.objects.filter(
            pool__vlan_if__vid=vlan_id,
            pool__is_dynamic=True,
            pool__kind=NetworkIpPoolKind.NETWORK_KIND_GUEST,
            ip_address__gte=F('pool__ip_start'),
            ip_address__lte=F('pool__ip_end'),
            is_dynamic=True,
            customer=None,
            cvid=0, svid=0,
            state=False
        )[:1]
        updated_lease_count = _update_leases(
            lease,
            customer_mac=customer_mac,
            customer_id=db_info.id,
            vlan_id=vlan_id,
            service_vlan_id=service_vlan_id,
            curr_time=now,
            radius_unique_id=radius_unique_id,
            radius_username=radius_username
        )
        if updated_lease_count > 0:
            lease = lease.only('ip_address').values('ip_address').first()
            if lease is not None and lease.get('ip_address') is not None:
                db_info.ip_address = lease.get('ip_address')

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
        _update_lease_send_ws_signal(
            customer_id=db_info.id
        )
        return JSONResponse(response, status_code=code)
    except (LogicError, BadRetException) as err:
        return _bad_ret(str(err))


@router.post('/get_service/')
def get_service(data: CustomerServiceRequestSchema):
    customer_ip = data.customer_ip
    # password = data.get('password')

    customer_service = CustomerService.get_user_credentials_by_ip(ip_addr=customer_ip)
    if customer_service is None:
        return Response({
            "Reply-Message": "Customer service not found"
        }, status_code=status.HTTP_404_NOT_FOUND)

    sess_time = customer_service.calc_session_time()
    return Response({
        "ip": customer_ip,
        "session_time": int(sess_time.total_seconds()),
        "speed_in": customer_service.service.speed_in,
        "speed_out": customer_service.service.speed_out,
    })


@router.post('/acct/{vendor_name}/')
def acct(vendor_name: str, request_data: Mapping[str, Any] = Body(...)):
    if not vendor_name:
        return _bad_ret('Empty vendor name')

    vendor_manager = VendorManager(vendor_name=vendor_name)

    request_type = vendor_manager.get_acct_status_type(request_data)
    if request_type is None:
        logger.error('request_type is None')
        return _acct_unknown(None, 'request_type is None')

    try:
        # request_type_fn = acct_status_type_map.get(request_type.value, self._acct_unknown)
        request_type_fn = _acct_status_type_map.get(request_type)
        if request_type_fn is None:
            err = 'request_type_fn is None, (request_type=%s)' % request_type
            logger.error(err)
            return _acct_unknown(None, err)
        return request_type_fn(vendor_manager=vendor_manager, request_data=request_data)
    except BadRetException as err:
        return _bad_ret(str(err))


def _bad_ret(text, custom_status=status.HTTP_400_BAD_REQUEST):
    logger.error(text)
    return Response({"Reply-Message": text}, status_code=custom_status)


def _update_lease_send_ws_signal(customer_id: int):
    send_data2ws({
        "eventType": WsEventTypeEnum.UPDATE_CUSTOMER_LEASES.value,
        "data": {
            "customer_id": customer_id
        }
    })


class BadRetException(HTTPException):
    def __init__(self, status_code=status.HTTP_400_BAD_REQUEST, detail=None,
                 *args, **kwargs):
        super().__init__(
            status_code=status_code,
            detail=detail or _('exception from radius.'),
            *args, **kwargs
        )


def _build_srv_result_from_db_result(row: tuple) -> CustomerServiceLeaseResult:
    (uid, uname, acc_is_act, balance, is_dyn_ip, ars, csid, dev_port_id, dev_id, gw_id,
     si, so, sb, ip_addr, mac_addr, ip_is_dynamic) = row
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
        id=uid,
        username=uname,
        is_active=acc_is_act,
        balance=balance,
        is_dynamic_ip=is_dyn_ip,
        auto_renewal_service=ars,
        current_service_id=csid,
        dev_port_id=dev_port_id,
        device_id=dev_id,
        gateway_id=gw_id,
        speed=speed,
        ip_address=ip_addr,
        mac_address=mac_addr,
        is_dynamic=ip_is_dynamic
    )


def _get_customer_and_service_and_lease_by_device_credentials(
    device_mac: EUI, customer_mac: EUI, device_port: int = 0
) -> Optional[CustomerServiceLeaseResult]:
    sql = (
        "SELECT ba.id, "
        "ba.username, "
        "ba.is_active, "
        "cs.balance, "
        "cs.is_dynamic_ip, "
        "cs.auto_renewal_service, "
        "cs.current_service_id, "
        "cs.dev_port_id, "
        "cs.device_id, "
        "cs.gateway_id, "
        "srv.speed_in, "
        "srv.speed_out, "
        "srv.speed_burst, "
        "nip.ip_address, "
        "nip.mac_address, "
        "nip.is_dynamic "
        "FROM customers cs "
        "LEFT JOIN device dv ON (dv.id = cs.device_id) "
        "LEFT JOIN device_port dp ON (cs.dev_port_id = dp.id) "
        "LEFT JOIN device_dev_type_is_use_dev_port ddtiudptiu ON (ddtiudptiu.dev_type = dv.dev_type) "
        "LEFT JOIN base_accounts ba ON cs.baseaccount_ptr_id = ba.id "
        "LEFT JOIN customer_service custsrv ON custsrv.id = cs.current_service_id "
        "LEFT JOIN services srv ON srv.id = custsrv.service_id "
        "LEFT JOIN networks_ip_leases nip ON ( "
        "nip.customer_id = cs.baseaccount_ptr_id AND ( "
        "nip.mac_address = %s::MACADDR OR nip.mac_address IS NULL "
        ") "
        ") "
        "WHERE dv.mac_addr = %s::MACADDR "
        "AND ((NOT ddtiudptiu.is_use_dev_port) OR dp.num = %s::SMALLINT) "
        "LIMIT 1;"
    )
    with connection.cursor() as cur:
        cur.execute(sql=sql, params=[str(customer_mac), str(device_mac), device_port])
        row = cur.fetchone()
    if not row:
        return None
    return _build_srv_result_from_db_result(row=row)


def _get_customer_and_service_and_lease_by_mac(
    customer_mac: EUI
) -> Optional[CustomerServiceLeaseResult]:
    sql = (
        "SELECT ba.id, "
        "ba.username, "
        "ba.is_active, "
        "cs.balance, "
        "cs.is_dynamic_ip, "
        "cs.auto_renewal_service, "
        "cs.current_service_id, "
        "cs.dev_port_id, "
        "cs.device_id, "
        "cs.gateway_id, "
        "srv.speed_in, "
        "srv.speed_out, "
        "srv.speed_burst, "
        "nip.ip_address, "
        "nip.mac_address, "
        "false "
        "FROM customers cs "
        "LEFT JOIN base_accounts ba ON cs.baseaccount_ptr_id = ba.id "
        "LEFT JOIN customer_service custsrv ON custsrv.id = cs.current_service_id "
        "LEFT JOIN services srv ON srv.id = custsrv.service_id "
        "LEFT JOIN networks_ip_leases nip ON nip.customer_id = cs.baseaccount_ptr_id "
        "WHERE "
        "nip.mac_address = %s::MACADDR "
        "LIMIT 1;"
    )
    with connection.cursor() as cur:
        cur.execute(sql=sql, params=[str(customer_mac)])
        row = cur.fetchone()
    if not row:
        return None
    return _build_srv_result_from_db_result(row=row)


def _update_counters(leases, data: Mapping[str, str], counters: RadiusCounters, vendor_manager: VendorManager,
                     customer_mac: Optional[EUI] = None,
                     last_event_time=None, **update_kwargs):
    if last_event_time is None:
        last_event_time = datetime.now()
    leases.update(
        last_update=last_event_time,
        input_octets=counters.input_octets,
        output_octets=counters.output_octets,
        input_packets=counters.input_packets,
        output_packets=counters.output_packets,
        **update_kwargs,
    )
    radius_unique_id = vendor_manager.get_radius_unique_id(data)
    ip = vendor_manager.get_rad_val(data, "Framed-IP-Address", str)
    custom_signals.radius_auth_update_signal.send(
        sender=CustomerIpLeaseModel,
        instance=None,
        instance_queryset=leases,
        data=data,
        counters=counters,
        radius_unique_id=radius_unique_id,
        ip_addr=ip,
        customer_mac=customer_mac
    )


def _acct_start(vendor_manager: VendorManager, request_data: Mapping[str, Any]):
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

    opt82 = vendor_manager.get_opt82(data=request_data)
    if opt82 is None:
        return _bad_ret('Bad opt82')

    customer_mac = vendor_manager.get_customer_mac(request_data)
    if not customer_mac:
        return _bad_ret("Customer mac is required")

    radius_unique_id = vendor_manager.get_radius_unique_id(request_data)
    if not radius_unique_id:
        return _bad_ret('Bad unique id from radius request')

    now = datetime.now()

    agent_remote_id, agent_circuit_id = opt82
    if all([agent_remote_id, agent_circuit_id]):
        dev_mac, dev_port = vendor_manager.build_dev_mac_by_opt82(
            agent_remote_id=agent_remote_id,
            agent_circuit_id=agent_circuit_id
        )
        if not dev_mac:
            return _bad_ret('bad opt82 device mac address')
        customer = CustomerIpLeaseModel.find_customer_by_device_credentials(
            device_mac=dev_mac,
            device_port=dev_port
        )
        if not customer:
            return _bad_ret(
                'Customer with provided device credentials not found: %s %s' % (dev_mac, dev_port),
                custom_status=status.HTTP_404_NOT_FOUND
            )

        vlan_id = vendor_manager.get_vlan_id(request_data)
        service_vlan_id = vendor_manager.get_service_vlan_id(request_data)
        counters = vendor_manager.get_counters(data=request_data)
        CustomerIpLeaseModel.objects.filter(
            ip_address=ip,
            customer=customer,
            is_dynamic=False,
            mac_address=None
        ).update(
            mac_address=customer_mac,
            input_octets=counters.input_octets,
            output_octets=counters.output_octets,
            input_packets=counters.input_packets,
            output_packets=counters.output_packets,
            state=True,
            lease_time=now,
            last_update=now,
            session_id=radius_unique_id,
            radius_username=radius_username,
            svid=safe_int(service_vlan_id),
            cvid=safe_int(vlan_id)
        )
    else:
        # auth by mac. Find static lease.
        lease = CustomerIpLeaseModel.objects.filter(
            mac_address=customer_mac,
            is_dynamic=False
        ).exclude(
            customer=None
        ).select_related('customer').first()
        if lease is None:
            return _bad_ret(
                'Lease with mac="%s" not found' % customer_mac,
                custom_status=status.HTTP_404_NOT_FOUND
            )
        customer = lease.customer
        if not customer:
            return _bad_ret(
                'Customer with provided mac address: %s Not found' % customer_mac,
                custom_status=status.HTTP_404_NOT_FOUND
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


def _acct_stop(vendor_manager: VendorManager, request_data: Mapping[str, Any]):
    ip = vendor_manager.get_rad_val(request_data, "Framed-IP-Address", str)
    radius_unique_id = vendor_manager.get_radius_unique_id(request_data)
    customer_mac = vendor_manager.get_customer_mac(request_data)
    leases = CustomerIpLeaseModel.objects.filter(
        session_id=radius_unique_id
    )

    counters = vendor_manager.get_counters(data=request_data)

    custom_signals.radius_acct_stop_signal.send(
        sender=CustomerIpLeaseModel,
        instance=CustomerIpLeaseModel(),
        instance_queryset=leases,
        data=request_data,
        counters=counters,
        ip_addr=ip,
        radius_unique_id=radius_unique_id,
        customer_mac=customer_mac,
    )
    leases.update(
        state=False,
        last_update=datetime.now()
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _find_customer(data: Mapping[str, str], vendor_manager: VendorManager) -> Customer:
    # TODO: Optimize
    opt82 = vendor_manager.get_opt82(data=data)
    if not opt82:
        raise BadRetException(detail="Failed fetch opt82 info")
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

        customer = CustomerIpLeaseModel.find_customer_by_device_credentials(
            device_mac=dev_mac,
            device_port=dev_port
        )
        if not customer:
            raise BadRetException(
                detail='Customer not found by device: dev_mac=%(dev_mac)s, dev_port=%(dev_port)s' % {
                    'dev_mac': str(dev_mac),
                    'dev_port': str(dev_port),
                },
                status_code=status.HTTP_404_NOT_FOUND
            )
        return customer
    raise BadRetException(
        detail='not all opt82 %s' % str(opt82),
        status_code=status.HTTP_200_OK
    )


def _acct_update(vendor_manager: VendorManager, request_data: Mapping[str, Any]):
    radius_unique_id = vendor_manager.get_radius_unique_id(request_data)
    customer_mac = vendor_manager.get_customer_mac(request_data)
    if not customer_mac:
        return _bad_ret("Customer mac is required")
    radius_username = vendor_manager.get_radius_username(request_data)
    if not radius_username:
        return _bad_ret(
            "Request has no username",
            custom_status=status.HTTP_200_OK
        )
    now = datetime.now()
    counters = vendor_manager.get_counters(request_data)
    leases = CustomerIpLeaseModel.objects.filter(
        session_id=radius_unique_id
    )
    customer = None
    if leases.exists():
        # just update counters
        _update_counters(
            leases=leases,
            data=request_data,
            counters=counters,
            customer_mac=customer_mac,
            vendor_manager=vendor_manager
        )
    else:
        # create lease on customer profile if it not exists
        ip = vendor_manager.get_rad_val(request_data, "Framed-IP-Address", str)
        vlan_id = vendor_manager.get_vlan_id(request_data)
        service_vlan_id = vendor_manager.get_service_vlan_id(request_data)
        customer = _find_customer(data=request_data, vendor_manager=vendor_manager)
        CustomerIpLeaseModel.objects.filter(
            ip_address=str(ip),
        ).update(
            customer=customer,
            mac_address=str(customer_mac),
            input_octets=counters.input_octets,
            output_octets=counters.output_octets,
            input_packets=counters.input_packets,
            output_packets=counters.output_packets,
            state=True,
            lease_time=now,
            last_update=now,
            session_id=str(radius_unique_id),
            radius_username=radius_username,
            svid=safe_int(service_vlan_id),
            cvid=safe_int(vlan_id)
        )

    # Check for service synchronizaion
    bras_service_name = vendor_manager.get_rad_val(request_data, "ERX-Service-Session", str)
    if isinstance(bras_service_name, str):
        if 'SERVICE-INET' in bras_service_name:
            # bras contain inet session
            if customer is None:
                customer = _find_customer(data=request_data, vendor_manager=vendor_manager)
            if not customer.is_access():
                logger.info("COA: inet->guest uname=%s" % radius_username)
                async_change_session_inet2guest.delay(
                    radius_uname=radius_username
                )
        elif 'SERVICE-GUEST' in bras_service_name:
            # bras contain guest session
            if customer is None:
                customer = _find_customer(data=request_data, vendor_manager=vendor_manager)
            if customer.is_access():
                logger.info("COA: guest->inet uname=%s" % radius_username)
                customer_service = customer.active_service()
                service = customer_service.service
                speed = SpeedInfoStruct(
                    speed_in=float(service.speed_in),
                    speed_out=float(service.speed_out),
                    burst_in=float(service.speed_burst),
                    burst_out=float(service.speed_burst),
                )
                speed = vendor_manager.get_speed(speed=speed)
                async_change_session_guest2inet.delay(
                    radius_uname=radius_username,
                    speed_in=speed.speed_in,
                    speed_out=speed.speed_out,
                    speed_in_burst=speed.burst_in,
                    speed_out_burst=speed.burst_out
                )

    return Response(status_code=status.HTTP_204_NO_CONTENT)


_acct_status_type_map = {
    AcctStatusType.START: _acct_start,
    AcctStatusType.STOP: _acct_stop,
    AcctStatusType.UPDATE: _acct_update,
}
