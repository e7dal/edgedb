#
# This source file is part of the EdgeDB open source project.
#
# Copyright 2016-present MagicStack Inc. and the EdgeDB authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#


from edb.testbase import server as tb


class TestDatabase(tb.ConnectedTestCase):
    async def test_database_create01(self):
        await self.con._legacy_execute('CREATE DATABASE mytestdb;')

        try:
            conn = await self.cluster.connect(
                user='edgedb', database='mytestdb')

            await conn.close()

        finally:
            await self.con._legacy_execute('DROP DATABASE mytestdb;')
