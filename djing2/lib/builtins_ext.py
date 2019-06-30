class DictReturner:

    def to_dict(self):
        return {k: getattr(self, k) for k in dir(self) if not k.startswith('_')}
