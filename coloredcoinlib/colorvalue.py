from comparable import ComparableMixin


class IncompatibleTypesError(Exception):
    pass


class InvalidValueError(Exception):
    pass


class ColorValue(object):
    def __init__(self, **kwargs):
        self.colordef = kwargs.pop('colordef')

    def get_kwargs(self):
        kwargs = {}
        kwargs['colordef'] = self.get_colordef()
        return kwargs

    def clone(self):
        kwargs = self.get_kwargs()
        return self.__class__(**kwargs)

    def check_compatibility(self, other):
        if self.get_color_id() != other.get_color_id():
            raise IncompatibleTypesError        

    def get_colordef(self):
        return self.colordef

    def get_color_id(self):
        return self.colordef.get_color_id()


class AdditiveColorValue(ColorValue, ComparableMixin):
    def __init__(self, **kwargs):
        super(AdditiveColorValue, self).__init__(**kwargs)
        self.value = int(kwargs.pop('value'))
        if not isinstance(self.value, int):
            raise InvalidValueError('not an int but a %s'
                                    % self.value.__class__)

    def get_kwargs(self):
        kwargs = super(AdditiveColorValue, self).get_kwargs()
        kwargs['value'] = self.get_value()
        return kwargs

    def get_value(self):
        return self.value

    def get_satoshi(self):
        return self.get_colordef().__class__.color_to_satoshi(self)

    def __add__(self, other):
        if isinstance(other, int) and other == 0:
            return self
        self.check_compatibility(other)
        kwargs = self.get_kwargs()
        kwargs['value'] = self.get_value() + other.get_value()
        return self.__class__(**kwargs)

    def __radd__(self, other):
        return self + other

    def __sub__(self, other):
        if isinstance(other, int) and other == 0:
            return self
        self.check_compatibility(other)
        kwargs = self.get_kwargs()
        kwargs['value'] = self.get_value() - other.get_value()
        return self.__class__(**kwargs)

    def __iadd__(self, other):
        self.check_compatibility(other)
        self.value += other.value
        return self

    def __eq__(self, other):
        if self.get_colordef() != other.get_colordef():
            return False
        else:
            return self.get_value() == other.get_value()

    def __lt__(self, other):
        self.check_compatibility(other)
        return self.get_value() < other.get_value()

    def __gt__(self, other):
        if isinstance(other, int) and other == 0:
            return self.get_value() > 0
        return other < self

    @classmethod
    def sum(cls, items):
        return reduce(lambda x,y:x + y, items)


class SimpleColorValue(AdditiveColorValue):
    def __init__(self, **kwargs):
        super(SimpleColorValue, self).__init__(**kwargs)
        if kwargs.get('label'):
            self.label = kwargs.pop('label')
        else:
            self.label = ''

    def get_kwargs(self):
        kwargs = super(SimpleColorValue, self).get_kwargs()
        kwargs['label'] = self.get_label()
        return kwargs

    def get_label(self):
        return self.label

    def __repr__(self):
        return "%s: %s" % (self.get_label() or self.get_colordef(), self.value)
