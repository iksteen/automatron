from ConfigParser import SafeConfigParser, NoSectionError
from twisted.application import internet
from twisted.application.service import MultiService
from twisted.internet import defer
from twisted.plugin import getPlugins, IPlugin
from twisted.python import log
from automatron.client import ClientFactory
from automatron.config import IAutomatronConfigManagerFactory
from automatron.plugin import PluginManager


DEFAULT_PORT = 6667


class Controller(MultiService):
    def __init__(self, config_file):
        MultiService.__init__(self)

        self.config_file = SafeConfigParser()
        self.config_file.readfp(open(config_file))

        self.plugins = None
        self.config = None

    @defer.inlineCallbacks
    def startService(self):
        # Set up configuration manager
        self.config = self._build_config_manager()
        yield self.config.prepare()

        # Load plugins
        self.plugins = PluginManager(self)

        servers = yield self.config.enumerate_servers()

        if not servers:
            log.msg('Warning: No server configurations defined.')

        # Set up client connections
        for server in servers:
            server_config = yield self.config.get_section('server', server, None)
            factory = ClientFactory(self, server, server_config)

            server_hostname = server_config['hostname']
            server_port = server_config.get('port', DEFAULT_PORT)
            connector = internet.TCPClient(server_hostname, server_port, factory)
            connector.setServiceParent(self)

        MultiService.startService(self)

    def _build_config_manager(self):
        try:
            automatron_options = dict(self.config_file.items('automatron'))
        except NoSectionError:
            automatron_options = {}
        typename = automatron_options.get('configmanager', 'sql')

        factories = list(getPlugins(IAutomatronConfigManagerFactory))
        for factory in factories:
            if factory.name == typename:
                return factory(self)
        else:
            raise RuntimeError('Config manager class %s not found' % typename)
