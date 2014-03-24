from twisted.internet import defer
from twisted.python import log
import zope.interface
import zope.interface.verify


STOP = object()


class IAutomatronEventHandler(zope.interface.Interface):
    """
    Abstract interface which is the base of all event handler interfaces.
    """


class EventManager(object):
    def __init__(self, controller):
        self.controller = controller
        self.event_handlers = []
        self.event_interfaces = {}

    def register_event_handler(self, handler):
        for event_interface in zope.interface.providedBy(handler):
            if event_interface.extends(IAutomatronEventHandler):
                event_interface_name = event_interface.getName()
                if event_interface_name in self.event_interfaces:
                    if self.event_interfaces[event_interface_name] is not event_interface:
                        log.msg('Warning: Duplicate event handler interface name: %s' % event_interface_name)
                else:
                    self.event_interfaces[event_interface_name] = event_interface

                try:
                    zope.interface.verify.verifyObject(event_interface, handler)
                except (zope.interface.verify.BrokenImplementation,
                        zope.interface.verify.BrokenMethodImplementation) as e:
                    log.err(e, 'Event handler %s is broken' % handler.__name__)
                    break
        else:
            self.event_handlers.append(handler)
            log.msg('Loaded event handler %s' % handler.name)

    @defer.inlineCallbacks
    def emit(self, interface_event_name, *args):
        interface_name, event_name = interface_event_name.split('.', 1)
        if not interface_name in self.event_interfaces:
            return

        event_interface = self.event_interfaces[interface_name]
        event = event_interface[event_name]

        if not event_interface.extends(IAutomatronEventHandler):
            log.msg('Emitted event %s\'s interface (%s) does not extend IAutomatronEventHandler' %
                    (event_name, interface_event_name))
            return

        if len(args) < len(event.required):
            log.msg('Emitted event %s\'s declaration requires at least %d arguments, only %d were '
                    'provided.' % (interface_event_name, len(event.required), len(args)))
            return

        if len(args) > len(event.positional):
            log.msg('Emitted event %s\'s declaration requires at most %d arguments, %d were '
                    'provided.' % (interface_event_name, len(event.positional), len(args)))
            return

        event_handlers = sorted(self.event_handlers, key=lambda i: i.priority)
        for plugin in event_handlers:
            try:
                event_handler_adapter = event_interface(plugin)
            except TypeError:
                continue

            f = getattr(event_handler_adapter, event.getName())
            if (yield defer.maybeDeferred(f, *args)) is STOP:
                defer.returnValue(STOP)
