from django.dispatch import Signal


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
