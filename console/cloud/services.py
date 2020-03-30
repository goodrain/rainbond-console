# -*- coding: utf-8 -*-


def order_payload(order):
    return {
        "eid": order.eid,
        "create_time": order.create_time,
        "expired_time": order.expired_time,
        "final_price": order.final_price,
        "memory": order.memory,
        "months": order.months,
        "order_id": order.order_id,
        "origin_price": order.origin_price,
        "status": order.status,
        "unit_price": order.unit_price,
        "user_id": order.user_id,
    }
