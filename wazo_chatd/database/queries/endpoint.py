# Copyright 2019 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from sqlalchemy import and_, text

from ...exceptions import UnknownEndpointException
from ..helpers import get_dao_session
from ..models import Endpoint


class EndpointDAO:

    @property
    def session(self):
        return get_dao_session()

    def create(self, endpoint):
        self.session.add(endpoint)
        self.session.flush()
        return endpoint

    def find_by(self, **kwargs):
        return self._find_by(**kwargs)

    def get_by(self, **kwargs):
        endpoint = self._find_by(**kwargs)
        if not endpoint:
            raise UnknownEndpointException(kwargs.get('name'))
        return endpoint

    def _find_by(self, **kwargs):
        filter_ = text('true')

        if 'name' in kwargs:
            filter_ = and_(filter_, Endpoint.name == kwargs['name'])

        return self.session.query(Endpoint).filter(filter_).first()

    def list_(self):
        return self.session.query(Endpoint).all()

    def update(self, endpoint):
        self.session.add(endpoint)
        self.session.flush()

    def delete_all(self):
        self.session.query(Endpoint).delete()
        self.session.flush()
