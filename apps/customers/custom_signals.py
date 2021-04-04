from django.dispatch import Signal

# Signal raises when customer service finished
# Params:
# - expired_services: Queryset of CustomerService model
customer_service_batch_pre_stop = Signal()
customer_service_batch_post_stop = Signal()

# Signal raises when customer service finished
# Params:
# - expired_service: CustomerService model instance
customer_service_pre_stop = Signal()
customer_service_post_stop = Signal()


# Signal raises when customer picked service
# params:
# - customer: Customer model instance
# - service: services.models.Service model instance
customer_service_pre_pick = Signal()
customer_service_post_pick = Signal()
