from django.dispatch import Signal


# Signal raises when customer picked service
# params:
# - sender: customers.Customer class
# - instance: customers.Customer model instance
# - service: services.models.Service model instance
customer_service_pre_pick = Signal()
customer_service_post_pick = Signal()

# Signal raises when customer turns on
# params
# - sender: customers.Customer class
# - instance: customers.Customer model instance
customer_turns_on = Signal()

# Signal raises when customer turns off
# params
# - sender: customers.Customer class
# - instance: customers.Customer model instance
customer_turns_off = Signal()
