from datetime import datetime


def on_new_lease_assigned(lease_id: int, ip_address: str, pool_id: int, lease_time: datetime,
                                                 mac_address: str,
                                                 customer_id: int, is_dynamic: bool, is_assigned: bool):
    """
    Calls this then new lease is assigned from db
    """
    pass
