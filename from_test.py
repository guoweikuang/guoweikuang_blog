class Mixin(object):
    pass


def register(cls):
    print cls.__name__
    decorated = type(
        cls.__name__,
        (Mixin, cls),
        {}
    )
    return cls


class View(object):
    def method(self):
        pass


@register
class ChildView(View):
    """docstring for ChildView"""

    def method(self):
        super(ChildView, self).method()
        # print super(ChildView, self).method
        # print ChildView


child = ChildView()
child.method()

view = View()
view.method()