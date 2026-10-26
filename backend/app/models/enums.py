from enum import StrEnum


class UserRole(StrEnum):
    CUSTOMER = "customer"
    STAFF = "staff"
    ADMIN = "admin"


class FulfillmentType(StrEnum):
    DELIVERY = "delivery"  # 10-minute style home delivery
    PICKUP = "pickup"  # scheduled pickup: store packs the order, customer collects in a time slot
    IN_STORE = "in_store"  # customer shops the aisles themselves and pays at the counter / in app


class OrderStatus(StrEnum):
    PLACED = "placed"
    CONFIRMED = "confirmed"
    PACKING = "packing"
    OUT_FOR_DELIVERY = "out_for_delivery"
    DELIVERED = "delivered"
    READY_FOR_PICKUP = "ready_for_pickup"
    PICKED_UP = "picked_up"
    AWAITING_PAYMENT = "awaiting_payment"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class PaymentMethod(StrEnum):
    COD = "cod"  # cash / UPI to the delivery partner
    PAY_AT_STORE = "pay_at_store"
    ONLINE = "online"  # mock online payment, marked paid immediately


class PaymentStatus(StrEnum):
    PENDING = "pending"
    PAID = "paid"
    REFUNDED = "refunded"


FINAL_STATUSES = {
    OrderStatus.DELIVERED,
    OrderStatus.PICKED_UP,
    OrderStatus.COMPLETED,
    OrderStatus.CANCELLED,
}
