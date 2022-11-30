from django.dispatch import Signal


#
# Signal raises before customer trying to pay
# params:
# - sender: customers.Customer class
# - instance: customers.Customer model instance
# - amount: Decimal
#
before_payment_success = Signal()

#
# Signal raises after customer has successfully payment
# params:
# - sender: customers.Customer class
# - instance: customers.Customer model instance
# - amount: Decimal
#
after_payment_success = Signal()
