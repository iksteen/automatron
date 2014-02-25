import shlex
from twisted.internet import defer
from twisted.python import log
from zope.interface import implements, classProvides
from automatron.command import IAutomatronCommandHandler
from automatron.plugin import IAutomatronPluginFactory, STOP
from automatron.client import IAutomatronMessageHandler


class CommandMessagePlugin(object):
    classProvides(IAutomatronPluginFactory)
    implements(IAutomatronMessageHandler)

    name = 'command'
    priority = 100

    def __init__(self, controller):
        self.controller = controller

    def on_message(self, client, user, channel, message):
        if channel == client.nickname and message:
            return self._on_message(client, user, message)

    @defer.inlineCallbacks
    def _on_message(self, client, user, message):
        try:
            args = shlex.split(message)
        except ValueError as e:
            client.msg(client.parse_user(user)[0], 'Invalid syntax: %s' % str(e))
            log.err(e, 'Unable to parse command')
            defer.returnValue(STOP)

        if not args:
            return
        command = args.pop(0)

        defer.returnValue((yield self.controller.plugins.emit(
            IAutomatronCommandHandler['on_command'],
            client,
            user,
            command,
            args
        )))