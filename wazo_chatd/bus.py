# Copyright 2019-2020 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import logging

from xivo.status import Status
from xivo_bus.middlewares import Middleware
from xivo_bus.consumer import BusConsumer
from xivo_bus.publisher import BusPublisherFailFast

logger = logging.getLogger(__name__)


class BusChatd(BusConsumer, BusPublisherFailFast):
    def provide_status(self, status):
        status['bus']['status'] = Status.ok if self.is_running else Status.fail


class ChatdInjector(Middleware):
    def marshal(self, event, headers, payload):
        try:
            tenant_uuid = payload['data']['tenant_uuid']
            headers.update(tenant_uuid=tenant_uuid)
        except KeyError:
            pass

        return headers, payload

    def unmarshal(self, event, headers, payload):
        return headers, payload
