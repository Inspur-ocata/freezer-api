"""
Copyright 2015 Hewlett-Packard

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

This product includes cryptographic software written by Eric Young
(eay@cryptsoft.com). This product includes software written by Tim
Hudson (tjh@cryptsoft.com).
========================================================================
"""

import time
import uuid
import falcon
from freezer_api.common import exceptions


class ActionsCollectionResource(object):
    """
    Handler for endpoint: /v1/actions
    """
    def __init__(self, storage_driver):
        self.db = storage_driver

    def on_get(self, req, resp):
        # GET /v1/actions(?limit,offset)     Lists actions
        user_id = req.get_header('X-User-ID')
        offset = req.get_param_as_int('offset') or 0
        limit = req.get_param_as_int('limit') or 10
        search = req.context.get('doc', {})
        obj_list = self.db.search_action(user_id=user_id, offset=offset,
                                         limit=limit, search=search)
        req.context['result'] = {'actions': obj_list}

    def on_post(self, req, resp):
        # POST /v1/actions    Creates action entry
        try:
            doc = req.context['doc']
        except KeyError:
            raise exceptions.BadDataFormat(
                message='Missing request body')
        user_id = req.get_header('X-User-ID')
        action_id = '{0}'.format(uuid.uuid4())
        time_created = int(time.time())
        time_started = -1
        time_ended = -1
        doc.update({
            'action_id': action_id,
            'time_created': time_created,
            'time_started': time_started,
            'time_ended': time_ended,
            'status': 'pending'
        })
        action_id = self.db.add_action(
            user_id=user_id, doc=doc)
        resp.status = falcon.HTTP_201
        req.context['result'] = {'action_id': action_id}


class ActionsResource(object):
    """
    Handler for endpoint: /v1/actions/{action_id}
    """
    starting_states = ['started']
    ending_states = ['aborted', 'success', 'fail']

    def __init__(self, storage_driver):
        self.db = storage_driver

    def on_get(self, req, resp, action_id):
        # GET /v1/actions/{action_id}     retrieves the specified action
        # search in body
        user_id = req.get_header('X-User-ID') or ''
        obj = self.db.get_action(user_id=user_id, action_id=action_id)
        if obj:
            req.context['result'] = obj
        else:
            resp.status = falcon.HTTP_404

    def on_delete(self, req, resp, action_id):
        # DELETE /v1/actions/{action_id}     Deletes the specified action
        user_id = req.get_header('X-User-ID')
        self.db.delete_action(
            user_id=user_id, action_id=action_id)
        req.context['result'] = {'action_id': action_id}
        resp.status = falcon.HTTP_204

    def on_patch(self, req, resp, action_id):
        # PATCH /v1/actions/{action_id}     updates the specified action
        user_id = req.get_header('X-User-ID') or ''
        patch = req.context.get('doc', {})

        # Some knowledge of internal workings here:
        # status update triggers timestamp update
        status = patch.get('status', '')
        if status in ActionsResource.starting_states:
            patch.update({"time_started": int(time.time())})
        elif status in ActionsResource.ending_states:
            patch.update({"time_ended": int(time.time())})

        new_version = self.db.update_action(user_id=user_id,
                                            action_id=action_id,
                                            patch=patch)
        req.context['result'] = {'action_id': action_id,
                                 'patch': patch,
                                 'version': new_version}
