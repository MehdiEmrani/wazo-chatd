# Copyright 2019 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import datetime
import uuid

from hamcrest import (
    assert_that,
    calling,
    contains,
    contains_inanyorder,
    empty,
    equal_to,
    has_properties,
    is_not,
    none,
)
from sqlalchemy.inspection import inspect

from wazo_chatd.database.models import Room, RoomMessage, RoomUser
from wazo_chatd.exceptions import UnknownRoomException
from xivo_test_helpers.hamcrest.raises import raises
from xivo_test_helpers.hamcrest.uuid_ import uuid_

from .helpers import fixtures
from .helpers.base import (
    BaseIntegrationTest,
    UNKNOWN_UUID,
    TOKEN_TENANT_UUID as TENANT_1,
    TOKEN_SUBTENANT_UUID as TENANT_2,
)
from .helpers.wait_strategy import NoWaitStrategy

USER_UUID_1 = str(uuid.uuid4())
USER_UUID_2 = str(uuid.uuid4())
USER_UUID_3 = str(uuid.uuid4())

UUID = str(uuid.uuid4())


class TestRoom(BaseIntegrationTest):

    asset = 'database'
    service = 'postgresql'
    wait_strategy = NoWaitStrategy()

    @fixtures.db.room(tenant_uuid=TENANT_1)
    @fixtures.db.room(tenant_uuid=TENANT_2)
    def test_get(self, room_1, room_2):
        result = self._dao.room.get([room_1.tenant_uuid], room_1.uuid)
        assert_that(result, equal_to(room_1))

        assert_that(
            calling(self._dao.room.get).with_args([room_1.tenant_uuid], room_2.uuid),
            raises(UnknownRoomException, has_properties(status_code=404))
        )

    def test_get_doesnt_exist(self):
        assert_that(
            calling(self._dao.room.get).with_args([TENANT_1], UNKNOWN_UUID),
            raises(
                UnknownRoomException,
                has_properties(
                    status_code=404,
                    id_='unknown-room',
                    resource='rooms',
                    details=is_not(none()),
                    message=is_not(none()),
                )
            )
        )

    @fixtures.db.room(tenant_uuid=TENANT_1)
    @fixtures.db.room(tenant_uuid=TENANT_2)
    def test_list(self, room_1, room_2):
        result = self._dao.room.list_([room_1.tenant_uuid])
        assert_that(result, contains_inanyorder(room_1))

        result = self._dao.room.list_([room_1.tenant_uuid, room_2.tenant_uuid])
        assert_that(result, contains_inanyorder(room_1, room_2))

    @fixtures.db.room(users=[{'uuid': USER_UUID_1}, {'uuid': USER_UUID_2}])
    @fixtures.db.room(users=[{'uuid': USER_UUID_1}, {'uuid': USER_UUID_3}])
    @fixtures.db.room(users=[{'uuid': USER_UUID_2}, {'uuid': USER_UUID_3}])
    def test_list_by_user_uuid(self, room_1, room_2, _):
        result = self._dao.room.list_([room_1.tenant_uuid], user_uuid=USER_UUID_1)
        assert_that(result, contains_inanyorder(room_1, room_2))

    @fixtures.db.room(tenant_uuid=TENANT_1)
    @fixtures.db.room(tenant_uuid=TENANT_2)
    def test_count(self, room_1, room_2):
        result = self._dao.room.count([room_1.tenant_uuid])
        assert_that(result, equal_to(1))

        result = self._dao.room.count([room_1.tenant_uuid, room_2.tenant_uuid])
        assert_that(result, equal_to(2))

    @fixtures.db.room(users=[{'uuid': USER_UUID_1}, {'uuid': USER_UUID_2}])
    @fixtures.db.room(users=[{'uuid': USER_UUID_1}, {'uuid': USER_UUID_3}])
    @fixtures.db.room(users=[{'uuid': USER_UUID_2}, {'uuid': USER_UUID_3}])
    def test_count_by_user_uuid(self, room_1, room_2, _):
        result = self._dao.room.count([room_1.tenant_uuid], user_uuid=USER_UUID_1)
        assert_that(result, equal_to(2))

    def test_create(self):
        room = Room(tenant_uuid=TENANT_1)
        room = self._dao.room.create(room)

        self._session.expire_all()
        assert_that(room, has_properties(uuid=uuid_()))

    def test_create_with_users(self):
        room_user = RoomUser(uuid=USER_UUID_1, tenant_uuid=UUID, wazo_uuid=UUID)
        room = Room(tenant_uuid=TENANT_1, users=[room_user])
        room = self._dao.room.create(room)

        self._session.expire_all()
        assert_that(room, has_properties(uuid=uuid_()))

    @fixtures.db.room(users=[{'uuid': USER_UUID_1}])
    def test_delete_cascade(self, room):
        self._session.query(Room).filter(Room.uuid == room.uuid).delete()

        self._session.expire_all()
        assert_that(inspect(room).deleted)

        result = self._session.query(RoomUser).filter(RoomUser.uuid == USER_UUID_1).first()
        assert_that(result, none())

    @fixtures.db.room()
    def test_add_message(self, room):
        message = RoomMessage(user_uuid=UUID, tenant_uuid=UUID, wazo_uuid=UUID)

        self._dao.room.add_message(room, message)

        self._session.expire_all()
        assert_that(inspect(message).persistent)
        assert_that(room.messages, contains(message))

    @fixtures.db.room(messages=[{'content': 'older'}, {'content': 'newer'}])
    def test_list_messages(self, room):
        message_2, message_1 = room.messages

        messages = self._dao.room.list_messages(room)

        assert_that(messages, contains(message_2, message_1))

    @fixtures.db.room(messages=[{'content': 'older'}, {'content': 'newer'}])
    def test_list_messages_direction(self, room):
        message_2, message_1 = room.messages

        messages = self._dao.room.list_messages(room, direction='desc')
        assert_that(messages, contains(message_2, message_1))

        messages = self._dao.room.list_messages(room, direction='asc')
        assert_that(messages, contains(message_1, message_2))

    @fixtures.db.room(messages=[{'content': 'older'}, {'content': 'newer'}])
    def test_list_messages_limit(self, room):
        message_2, message_1 = room.messages

        messages = self._dao.room.list_messages(room, limit=1)

        assert_that(messages, contains(message_2))

    @fixtures.db.room(messages=[{'content': 'older'}, {'content': 'newer'}])
    def test_count_messages(self, room):
        count = self._dao.room.count_messages(room)

        assert_that(count, equal_to(2))


class TestRoomRelationships(BaseIntegrationTest):

    asset = 'database'
    service = 'postgresql'
    wait_strategy = NoWaitStrategy()

    @fixtures.db.room()
    def test_users_create(self, room):
        room_user = RoomUser(uuid=USER_UUID_1, tenant_uuid=UUID, wazo_uuid=UUID)
        room.users = [room_user]
        self._session.flush()

        self._session.expire_all()
        assert_that(inspect(room_user).persistent)
        assert_that(room.users, contains(room_user))

    @fixtures.db.room(users=[{'uuid': USER_UUID_1}])
    def test_users_delete(self, room):
        room_user = room.users[0]
        room.users = []
        self._session.flush()

        self._session.expire_all()
        assert_that(inspect(room_user).deleted)
        assert_that(room.users, empty())

    @fixtures.db.room()
    def test_users_get(self, room):
        room_user = RoomUser(room_uuid=room.uuid, uuid=USER_UUID_1, tenant_uuid=UUID, wazo_uuid=UUID)
        self._session.add(room_user)
        self._session.flush()

        self._session.expire_all()
        assert_that(room.users, contains(room_user))

    @fixtures.db.room()
    def test_messages_create(self, room):
        message = RoomMessage(user_uuid=UUID, tenant_uuid=UUID, wazo_uuid=UUID)
        room.messages = [message]
        self._session.flush()

        self._session.expire_all()
        assert_that(inspect(message).persistent)
        assert_that(room.messages, contains(message))

    @fixtures.db.room()
    def test_messages_delete(self, room):
        message = RoomMessage(user_uuid=UUID, tenant_uuid=UUID, wazo_uuid=UUID)
        room.messages = [message]
        self._session.flush()

        room.messages = []
        self._session.flush()

        self._session.expire_all()
        assert_that(inspect(message).deleted)
        assert_that(room.messages, empty())

    @fixtures.db.room()
    def test_messages_get(self, room):
        now = datetime.datetime.utcnow()
        yesterday = now - datetime.timedelta(days=1)
        message_1 = self.add_room_message(room_uuid=room.uuid, created_at=yesterday)
        message_2 = self.add_room_message(room_uuid=room.uuid, created_at=now)

        self._session.expire_all()
        assert_that(room.messages, contains(message_2, message_1))

    def add_room_message(self, **kwargs):
        kwargs.setdefault('user_uuid', str(uuid.uuid4()))
        kwargs.setdefault('tenant_uuid', str(uuid.uuid4()))
        kwargs.setdefault('wazo_uuid', str(uuid.uuid4()))
        message = RoomMessage(**kwargs)
        self._session.add(message)
        self._session.flush()
        return message