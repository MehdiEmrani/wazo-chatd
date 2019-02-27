# Copyright 2019 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import random
import uuid

from hamcrest import (
    assert_that,
    calling,
    contains,
    equal_to,
    empty,
    has_items,
    has_properties,
    is_not,
    none,
)
from sqlalchemy.inspection import inspect

from wazo_chatd.database.models import User, Session, Line
from wazo_chatd.exceptions import UnknownUserException
from xivo_test_helpers.hamcrest.raises import raises

from .helpers import fixtures
from .helpers.base import (
    BaseIntegrationTest,
    UNKNOWN_UUID,
    MASTER_TENANT_UUID,
    SUBTENANT_UUID,
)
from .helpers.wait_strategy import NoWaitStrategy

USER_UUID = str(uuid.uuid4())


class TestUser(BaseIntegrationTest):

    asset = 'database'
    service = 'postgresql'
    wait_strategy = NoWaitStrategy()

    def test_create(self):
        user_uuid = uuid.uuid4()
        user = User(
            uuid=user_uuid,
            tenant_uuid=MASTER_TENANT_UUID,
            state='available',
            status='description of available state',
        )
        user = self._dao.user.create(user)

        self._session.expire_all()
        assert_that(inspect(user).persistent)
        assert_that(user, has_properties(
            uuid=str(user_uuid),
            tenant_uuid=MASTER_TENANT_UUID,
        ))

    @fixtures.db.user()
    @fixtures.db.user(tenant_uuid=SUBTENANT_UUID)
    def test_get(self, user_1, _):
        result = self._dao.user.get([MASTER_TENANT_UUID], user_1.uuid)
        assert_that(result, equal_to(user_1))

        assert_that(
            calling(self._dao.user.get).with_args(
                [SUBTENANT_UUID],
                user_1.uuid,
            ),
            raises(
                UnknownUserException,
                has_properties(
                    status_code=404,
                    id_='unknown-user',
                    resource='users',
                    details=is_not(none()),
                    message=is_not(none()),
                )
            )
        )

    def test_get_doesnt_exist(self):
        assert_that(
            calling(self._dao.user.get).with_args(
                [MASTER_TENANT_UUID],
                UNKNOWN_UUID,
            ),
            raises(
                UnknownUserException,
                has_properties(
                    status_code=404,
                    id_='unknown-user',
                    resource='users',
                    details=is_not(none()),
                    message=is_not(none()),
                )
            )
        )

    @fixtures.db.user()
    @fixtures.db.user(tenant_uuid=SUBTENANT_UUID)
    def test_list(self, user_1, user_2):
        result = self._dao.user.list_([MASTER_TENANT_UUID])
        assert_that(result, has_items(user_1))

        result = self._dao.user.list_([MASTER_TENANT_UUID, SUBTENANT_UUID])
        assert_that(result, has_items(user_1, user_2))

        result = self._dao.user.list_([SUBTENANT_UUID])
        assert_that(result, has_items(user_2))

    @fixtures.db.user()
    @fixtures.db.user(tenant_uuid=SUBTENANT_UUID)
    def test_list_bypass_tenant(self, user_1, user_2):
        result = self._dao.user.list_(tenant_uuids=None)
        assert_that(result, has_items(user_1, user_2))

    @fixtures.db.user()
    @fixtures.db.user(tenant_uuid=SUBTENANT_UUID)
    def test_count(self, user_1, user_2):
        result = self._dao.user.count([MASTER_TENANT_UUID])
        assert_that(result, equal_to(1))

        result = self._dao.user.count([MASTER_TENANT_UUID, SUBTENANT_UUID])
        assert_that(result, equal_to(2))

        result = self._dao.user.count([SUBTENANT_UUID])
        assert_that(result, equal_to(1))

    @fixtures.db.user()
    def test_update(self, user):
        user_uuid = user.uuid
        user_state = 'invisible'
        user_status = 'other status'

        user.state = user_state
        user.status = user_status
        self._dao.user.update(user)

        self._session.expire_all()
        assert_that(user, has_properties(
            uuid=user_uuid,
            state=user_state,
            status=user_status,
        ))

    @fixtures.db.user()
    def test_add_session(self, user):
        session_uuid = str(uuid.uuid4())
        session = Session(uuid=session_uuid)
        self._dao.user.add_session(user, session)

        self._session.expire_all()
        assert_that(user.sessions, contains(has_properties(uuid=session_uuid)))

        # twice
        self._dao.user.add_session(user, session)

        self._session.expire_all()
        assert_that(user.sessions, contains(has_properties(uuid=session_uuid)))

    @fixtures.db.user(uuid=USER_UUID)
    @fixtures.db.session(user_uuid=USER_UUID)
    def test_remove_session(self, user, session):
        self._dao.user.remove_session(user, session)

        self._session.expire_all()
        assert_that(user.sessions, empty())

        # twice
        self._dao.user.remove_session(user, session)

        self._session.expire_all()
        assert_that(user.sessions, empty())

    @fixtures.db.user()
    def test_add_line(self, user):
        line_id = random.randint(1, 1000000)
        line = Line(id=line_id)
        self._dao.user.add_line(user, line)

        self._session.expire_all()
        assert_that(user.lines, contains(has_properties(id=line_id)))

        # twice
        self._dao.user.add_line(user, line)

        self._session.expire_all()
        assert_that(user.lines, contains(has_properties(id=line_id)))

    @fixtures.db.user(uuid=USER_UUID)
    @fixtures.db.line(user_uuid=USER_UUID)
    def test_remove_line(self, user, line):
        self._dao.user.remove_line(user, line)

        self._session.expire_all()
        assert_that(user.lines, empty())

        # twice
        self._dao.user.remove_line(user, line)

        self._session.expire_all()
        assert_that(user.lines, empty())
