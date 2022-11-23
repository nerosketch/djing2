from django.dispatch import Signal


# Signal raises when customer service finished
# Params:
# - instance: CustomerService model instance
# - customer: customers.Customer model instance
customer_service_pre_stop = Signal()
customer_service_post_stop = Signal()


# Signal raises when customer picked service
# params:
# - sender: customers.Customer class
# - instance: customers.Customer model instance
# - service: services.models.Service model instance
customer_service_pre_pick = Signal()

# Signal raises when customer picked service
# params:
# - sender: services.CustomerService class
# - instance: services.CustomerService model instance
# - service: services.models.Service model instance
customer_service_post_pick = Signal()
