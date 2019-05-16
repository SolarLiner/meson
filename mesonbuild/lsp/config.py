import logging

logger = logging.getLogger(__name__)


class Config:
    def __init__(self, root_uri, init_opts, proc_id, capabilities):
        logger.debug(
            'Config(%s)', ','.join(
                repr(x) for x in [root_uri, init_opts, proc_id, capabilities]))
        self.root_uri = root_uri
        self.init_options = init_opts
        self.process_id = proc_id
        self.capabilities = capabilities
