from django.dispatch import Signal

# Signal raises when customer service finished
# Params:
# - Instance: Queryset of CustomerService model
customer_service_batch_pre_stop = Signal()
customer_service_batch_post_stop = Signal()

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
customer_service_post_pick = Signal()
