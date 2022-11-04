from django.dispatch import Signal


# Signal raises when customer service finished
# Params:
# - instance: CustomerService model instance
# - customer: customers.Customer model instance
customer_service_pre_stop = Signal()
customer_service_post_stop = Signal()
