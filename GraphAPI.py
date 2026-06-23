import base64
from datetime import datetime, date, timedelta
from dateutil import parser
import json
import sys
import logging
import requests
import msal
import time
import os

PARAMETERS_PATH = 'Parameters.json'
BACKUP_PARAMETERS_PATH = 'ReducedParameters.json'

try:
    DRIVE_PARAMS = json.load(open(PARAMETERS_PATH))
except FileNotFoundError:
    DRIVE_PARAMS = json.load(open(BACKUP_PARAMETERS_PATH))

for env_key in ["authority", "client_id", "secret", "endpoint"]:
    val = os.getenv(env_key)
    if val is None:
        continue
    DRIVE_PARAMS[env_key] = val

DRIVE_APP = msal.ConfidentialClientApplication(
            DRIVE_PARAMS["client_id"], authority=DRIVE_PARAMS["authority"],
            client_credential=DRIVE_PARAMS["secret"],
            # token_cache=...  # Default cache is in memory only.
            # You can learn how to use SerializableTokenCache from
            # https://msal-python.rtfd.io/en/latest/#msal.SerializableTokenCache
        )


def PartitionBatch(batch_list, max_length=20):
    ret = [batch_list[max_length*i:max_length*(i+1)] for i in range(len(batch_list)//max_length)]
    if len(batch_list) % max_length != 0:
        ret.append(batch_list[len(batch_list)-len(batch_list) % max_length:])
    return ret


class DriveSaveState:
    def __init__(self):
        pass


class MSDrive:
    def __init__(self, drive='', mode='drive', user='', site='', batch=True, meta_remote=False, app=None):

        self.foreman_drive = 'b!6wkisgg8iEu3Lm7Szz2BSnLa6yKS3jBOmSqrdiFYdHZtmzcESesoToy0wCtlR71V'
        self.rogers_drive = 'b!gDjZv2olxk67VLnWtUOPhK5zcmZo5-xHtKJFEcgOBkTJmS8wbP28Q7Igu0QUL2EP'
        self.foreman_item = "01TS3CPAHDYD3BMNBTKFHY2NWVX2KWIBIF"
        self.grady_site = '548605bd-4d98-4edd-b368-e20a38558faa'
        self.grady_drive = 'b!vQWGVJhN3U6zaOIKOFWPqqqzGkNbjD5OqsM-bVt-i6Wus8FSFgmoSrifpWqf5CiA'
        self.asbuilts_email = '82fcfd4a-40f5-4ff8-9ee1-22463a9b36e0'
        self.grady_email = '67ff38da-105d-4b62-908b-bfacee5335ac'
        self.test_item = '01I3LL2LRT5TWQSNWUFNHZHLVG4WXJRXNQ'
        self.params_item = '01ZWWTLPNDFBYBWNSQBFA2G4CX7DL7JB4B'
        self.FTTHAssociations_item = '01ZWWTLPL3UHJ7MMMBEJDJ3VKKHKAFCWHG'
        self.meta2_id = '01ZWWTLPMYXZ2OGWOHLZDJMMKTM74O363E'
        self.material_matrix_id = '01ZWWTLPLB7ZZP6K5EOZAZ3NRJGU7E4OHH'
        self.resource_files_id = '01ZWWTLPOYCEEUUCLJKVH2ET6IENFZ3SID'
        self.queue_id = '01ZWWTLPLITPUODTYB3VGLRUJ3DEIFQBWW'

        self.default_dir = f'drives/{self.rogers_drive}'

        if drive.lower() == 'foreman':
            self._drive = self.foreman_drive
        elif drive != '':
            self.drive = drive
        else:
            self.drive = self.rogers_drive
        self.prefix = ''
        self.response = None
        self.response_str = None
        self.delta_link = None
        self.meta = None
        self.values = []
        self.filtered_values = []
        self.user = user
        self.site = site
        self.filetype = 'application/json'
        self._batch = []
        self.batch_results = {}
        self.date_filter = 'today'
        self.verbose = False
        self.batch_instructions = batch
        self.use_next = True
        self._mode = mode
        self.params = DRIVE_PARAMS
        self.settings = self.Settings(self)
        self.batch_times = []
        self.batch_sleep_override = None
        self.meta_type = '2.0'
        self.meta_remote = meta_remote

        if app is None:
            # self.app = self.init_ms_app()
            self.app = DRIVE_APP
        else:
            self.app = app

    class Settings:
        def __init__(self, class_to_copy):
            self.mode = class_to_copy.mode
            self.site = class_to_copy.site
            self.meta = class_to_copy.meta
            self.user = class_to_copy.user
            self.drive = class_to_copy.drive
            self.verbose = class_to_copy.verbose
            self.batch_instructions = class_to_copy.batch_instructions
            self.use_next = class_to_copy.use_next
            self.attr_to_exclude = ['attr_to_exclude', 'values', 'response',
                                    'response_str', 'filtered_values', 'batch_results',
                                    'settings', 'copy', 'meta']
            self.copy = class_to_copy
            self.versions = []

        def attr_is_valid(self, name, attr):
            if name in ['_mode']:
                return True
            if not name.startswith("_") and not callable(attr) and not type(attr) is staticmethod:
                if name not in self.attr_to_exclude:
                    return True

        def refresh(self):
            save_state = DriveSaveState()
            for name, attr in self.copy.__dict__.items():
                if self.attr_is_valid(name, attr):
                    if type(attr) is list or type(attr) is dict:
                        save_state.__setattr__(name, attr.copy())
                    elif type(attr) is bool:
                        save_state.__setattr__(name, bool(attr))
                    else:
                        save_state.__setattr__(name, attr)
            self.versions.append(save_state)

        def revert(self):
            save_state = self.versions[-1]
            for name, attr in save_state.__dict__.items():
                if self.attr_is_valid(name, attr):
                    if type(attr) is list or type(attr) is dict:
                        self.copy.__setattr__(name, attr.copy())
                    elif type(attr) is bool:
                        self.copy.__setattr__(name, bool(attr))
                    else:
                        self.copy.__setattr__(name, attr)
            self.copy.setPrefix()
            self.versions.pop()
            del save_state

    def init_ms_app(self):
        self.app = msal.ConfidentialClientApplication(
            self.params["client_id"], authority=self.params["authority"],
            client_credential=self.params["secret"],
            # token_cache=...  # Default cache is in memory only.
            # You can learn how to use SerializableTokenCache from
            # https://msal-python.rtfd.io/en/latest/#msal.SerializableTokenCache
        )
        return self.app

    def request(self, mode='get', query='', data=None, verbose=True, override=False):
        # Example: Get(':/Customers/Rogers/Material/Material Matrix:/children', '')
        default_dir = f'drives/{self.default_dir}'
        mode = mode.lower()

        # Body needs to be a string
        if type(data) is dict:
            data = json.dumps(data)

        if verbose:
            print(f"{mode[0].upper()}{mode[1:]} {query}")

        try:
            config = json.load(open(sys.argv[1]))
        except:
            config = self.params

        if not override:
            full_query = "https://graph.microsoft.com/v1.0/" + query
        else:
            full_query = query

        # Create a preferably long-lived app instance which maintains a token cache.

        # The pattern to acquire a token looks like this.
        result = None

        # Firstly, looks up a token from cache.
        result = self.app.acquire_token_silent(config["scope"], account=None)

        if not result:
            logging.info("No suitable token exists in cache. Let's get a new one from AAD.")
            result = self.app.acquire_token_for_client(scopes=config["scope"])

        simple_reqs = {'get': requests.get, 'delete': requests.delete}
        complex_reqs = {'post': requests.post, 'put': requests.put, 'patch': requests.patch}

        ReturnResults = None
        if "access_token" in result:
            # Calling graph using the access token
            if mode in simple_reqs:
                graph_data_response = simple_reqs[mode](
                    full_query,
                    headers={'Authorization': 'Bearer ' + result['access_token'], 'Content-Type': 'application/Json', 'Prefer': 'bypass-shared-lock'})
            else:
                graph_data_response = complex_reqs[mode](  # Use token to call downstream service
                    full_query,
                    data,
                    headers={'Authorization': 'Bearer ' + result['access_token'], 'Content-Type': 'application/Json', 'Prefer': 'bypass-shared-lock'}, )
            if graph_data_response.status_code != 202:
                try:
                    graph_data = graph_data_response.json()
                except requests.exceptions.JSONDecodeError:
                    return graph_data_response.content
            else:
                graph_data = {'Response': 202}
            # print("Graph API call result: ")
            ReturnResults = json.dumps(graph_data, indent=2)
            # print(ReturnResults)
        else:
            print(result.get("error"))
            print(result.get("error_description"))
            print(result.get("correlation_id"))  # You may need this when reporting a bug

        return ReturnResults

    def multiReq(self, input_list, verbose=True, filetype='application/json', use_default_dir=True, safety_sleep=4):
        start_time = datetime.now()
        input_str = '{"requests": ['
        need_comma = False
        for request_id, request in enumerate(input_list):
            instruction_id = str(request_id + 1)
            if need_comma:
                input_str += ', '
            need_comma = True

            body_str = ''
            if len(request) > 2:
                # get the body
                if request[2] is not None:
                    body = f'"body": {request[2]}'
                    header = '"headers": {"Content-Type": "' + filetype + '"}'
                    body_str = f', {body}, {header}'  # f', {body}, {header}'
            if len(request) > 3:
                instruction_id = request[3]

            if use_default_dir:
                url = self.default_dir + request[0]
            else:
                url = request[0]
            input_str += '{' + f'"url": "{url}", "method": "{request[1].upper()}", "id": {instruction_id}{body_str}' + '}'
        input_str += ']}'
        if verbose:
            print(input_str)
        ret = json.loads(self.request('post', f'https://graph.microsoft.com/v1.0/$batch', data=input_str, verbose=verbose, override=True))
        time_delta = timedelta(seconds=safety_sleep) - (datetime.now()-start_time)

        if time_delta > timedelta(seconds=0):
            time.sleep(time_delta.seconds + time_delta.microseconds/1000000)
        return ret

    @staticmethod
    def simpleStr(inp):
        inp = inp.lower()
        ret = inp + ''
        to_remove = ['/', '-', ',', '.', ' ', '&', '"', "'", 's', '\n', '\t', '\r']
        for remove in to_remove:
            ret = ret.replace(remove, '')
        return ret.lower()

    def setPrefix(self):
        prefix = ''
        if self._mode.replace('s', '') == 'drive'.replace('s', ''):
            prefix = f'drives/{self.drive}/'

        if self._mode.replace('s', '') == 'sites'.replace('s', ''):
            prefix = f'sites/{self.site}/'

        if self._mode.replace('s', '') == 'user'.replace('s', ''):
            prefix = f'users/{self.user}/'

        if self._mode == 'custom':
            prefix = ''

        self.prefix = prefix

    @property
    def mode(self):
        return self._mode

    @mode.setter
    def mode(self, new_value):
        self._mode = new_value.lower()
        self.setPrefix()

    def addBatch(self, instructions):
        ret = []

        def batchify(ins):
            instruction_id = str(len(self._batch))
            url = self.prefix + ins[0]
            method = ins[1]
            if len(ins) >= 3:
                body = ins[2]
            else:
                body = None
            req = [url, method, body, instruction_id]
            self._batch.append(req)
            ret.append(instruction_id)

        if type(instructions[0]) is list:
            for instruction in instructions:
                batchify(instruction)
        else:
            # instructions is actually one instruction:
            batchify(instructions)

        if len(ret) == 1:
            ret = ret[0]

        return ret

    def batch(self, to_values=True):
        # prefix is used by addBatch
        self.batch_results = {}
        part_ins = PartitionBatch(self._batch)
        responses = []
        for batch_num, batch in enumerate(part_ins):
            t1 = datetime.now()
            if self.batch_sleep_override is not None:
                responses.append(self.multiReq(batch, verbose=self.verbose, filetype=self.filetype, use_default_dir=False, safety_sleep=self.batch_sleep_override))
            else:
                responses.append(self.multiReq(batch, verbose=self.verbose, filetype=self.filetype, use_default_dir=False))
            time_difference = round((datetime.now() - t1).seconds + (datetime.now() - t1).microseconds / (10 ** 6), 6)
            print(f"{batch_num+1}/{len(part_ins)}, Time diff: {time_difference} / {self.batch_sleep_override}")

        for batch in responses:
            for response in batch['responses']:
                if 'id' in response.keys():
                    if 'body' in response.keys():
                        if response['body'] is not None:
                            self.batch_results[response['id']] = response['body']
                        elif 'status' in response.keys():
                            self.batch_results[response['id']] = response['status']

        if to_values:
            self.batchToValues()
        self._batch = []
        return self.batch_results

    def branchingInstruction(self, start_locs, cont_cond, check_cond, success_func, max_depth=None):

        # start_locs is of form ["item path", inherited_info]
        # cont_cond is the condition required to check folders contents
        # check_cond is the condition to apply the success function on the file found
        # this function will always call the given functions with arguments: file value, inherited data

        if len(self._batch) == 0:
            self.settings.refresh()
            self.batch_instructions = True
            # start by initialising recursive variables
            request_log = {}
            # little kick start
            for loc in start_locs:
                if '/' in loc[0] or '\\' in loc[0]:
                    batch_id = self.get(f"{loc[0]}:/children".replace('::', ':'))
                else:
                    batch_id = self.get(f"{loc[0]}/children")
                request_log[batch_id] = loc[1]
            # print(self._batch)
            self.batch()
            new_request_log = {}
            checking_folders = True

            depth = 0
            while checking_folders:
                print("Checking", len(request_log))

                checking_folders = False
                for batch, values in self.batch_results.items():
                    next_link = self.next_link(values)
                    if next_link is not None:
                        checking_folders = True
                        batch_id = self.get(next_link)
                        new_request_log[batch_id] = request_log[batch].copy()
                    if 'error' in values:
                        continue
                    for value in values['value']:
                        # Continues search if folder fits criteria
                        if 'folder' in value and cont_cond(value, request_log[batch]):
                            checking_folders = True
                            batch_id = self.get(f"{value['id']}/children")
                            new_request_log[batch_id] = request_log[batch].copy()

                        # Takes job info from folder name
                        if check_cond(value, request_log[batch]):
                            success_func(value, request_log[batch])

                depth += 1
                if max_depth is not None and depth >= max_depth:
                    break
                # Searches all folders found earlier
                self.batch()
                request_log = new_request_log.copy()
                new_request_log = {}

            self.settings.revert()
            return True
        else:
            print("Attempted to perform a branching instruction while the batch wasn't empty.")
            return False

    def branch_search(self, nb_nums, target_names='bom', folders_to_check=None, soft_match=False, all_match=False):
        if type(target_names) is not list:
            target_names = [target_names]
        # nb_nums is a list of nubuild numbers
        ret = {}

        def check(info, carried_info):
            for i in target_names:
                if info['name'].lower() == i.lower():
                    if all_match:
                        continue
                    return True
                if soft_match and info['name'].lower().find(i.lower()) != -1:
                    if all_match:
                        continue
                    return True
                if all_match:
                    return False
            if all_match:
                return True
            return False

        def cont(info, carried_info):
            if 'folder' not in info:
                return False
            if folders_to_check:
                for i in folders_to_check:
                    if i.lower() in info['name'].lower():
                        return True
            else:
                for i in target_names:
                    if folders_to_check:
                        continue
                    if i.lower() == info['name'].lower():
                        return True
            return False

        def success(info, carried_info):
            carried_info[0] = True
            if carried_info[1] not in carried_info[2]:
                carried_info[2][carried_info[1]] = [info['id']]
            else:
                carried_info[2][carried_info[1]].append(info['id'])

        branch_instruct = []
        for nb in nb_nums:
            job_info = self.checkMeta(nb)
            job_id = job_info['id']
            branch_instruct.append([job_id, [False, nb, ret]])
        self.branchingInstruction(branch_instruct, cont, check, success)
        return ret

    def batchToValues(self):
        for ret_id, data in self.batch_results.items():
            try:
                data['value']
            except KeyError:
                pass
                # print(f'GraphAPI: No value in {data}')
            except TypeError:
                print(f"GraphAPI: Return data is of type {type(data)} : {data}")
        values = []
        if len(self.batch_results) > 0:
            for response in self.batch_results.items():
                if response[1] and type(response[1]) is dict and response[1] and 'value' in response[1]:
                    values += response[1]['value']
            self.values = values
        return self.values

    def setExcelCell(self, book_id, sheet_name, value, row=1, col=1):
        body = {
            "valueTypes": [["String"]],
            "values": [[value]]
        }
        request = f"{book_id}/workbook/worksheets('{sheet_name}')/cell(row={row},column={col})"
        return self.patch(request, body)

    def filterResponse(self):
        def matchesFilter(value):
            if self.date_filter:
                if 'createdDateTime' not in value.keys():
                    return False
                if not self.date_filter == 'today':
                    return True
                created_time = datetime.strptime(value['createdDateTime'], '%Y-%m-%dT%H:%M:%SZ')
                today_midnight = datetime.combine(date.today(), datetime.min.time())
                if created_time > today_midnight:
                    return True
                return False
            return True

        self.filtered_values = []
        if self.values:
            self.filtered_values = [x for x in self.values if matchesFilter(x)]
        return self.filtered_values

    def respond(self, response):
        if response:
            if type(response) is dict:
                ret = response
            elif type(response) is str:
                ret = json.loads(response)
            else:
                ret = response
                self.values = None
            if type(ret) == dict:
                if 'value' in ret.keys():
                    self.values = ret['value']
                elif "@odata.context" in ret.keys():
                    self.values = None
        else:
            if self.verbose:
                print('Error! Nothing was returned.')
            ret = 'Error! Nothing was returned.'
        self.response = ret
        if type(ret) == dict:
            self.response_str = json.dumps(ret, indent=2)
        else:
            self.response_str = ''
        self.filterResponse()

        if type(ret) is dict and 'error' in ret:
            print(f"GraphAPI Error: {ret}")

        return ret

    def search(self, target_text, path='01ZWWTLPLLP4EXWIJQVVF2NRZZZY7KYNUM'):
        return self.get(f"{path}/search(q='{{{target_text}}}')")

    def list_children(self, item_id, verbose=True):
        if self.batch_instructions:
            print(f"Batch Instructions enabled: Cannot get children")
            return
        self.get(f"{item_id}/children?$select=name,id")
        ret = []
        for val in self.values:
            i_id = val['id']
            i_name = val['name']
            ret.append(val)
            if verbose:
                print(f"{i_id} : {i_name}")
        return ret

    def copy(self, path_from, id_to, drive_id=None, name=None, overwrite=False):
        to_drive_id = drive_id
        if drive_id is None:
            to_drive_id = self.drive

        target_dict = {"parentReference": {"driveId": to_drive_id, "id": id_to}}
        if name:
            target_dict['name'] = name
        else:
            target_dict['name'] = 'Example Name'
        target_json = json.dumps(target_dict)
        if self.verbose:
            print(f'target json: {target_json}')

        path = path_from
        if path.find('/') == -1:
            path = f'/items/{path}/Copy'
        else:
            path = path + ':/Copy'

        if overwrite:
            path += "?@microsoft.graph.conflictBehavior=replace"

        if not self.batch_instructions:
            ret = self.post(path, target_json)
            # ret = Post(path, target_json, '')
            return self.respond(ret)
        else:
            full_path = f"drives/{self.drive}" + path
            ret = self.addBatch([path, 'post', target_dict])
            return ret

    def getAttachments(self, message_id, immediate=False):
        if not self.batch_instructions:
            self.mode = 'user'
            ret = self.get(f'messages/{message_id}/attachments')
        else:
            self.mode = 'user'
            ret = self.addBatch([f'messages/{message_id}/attachments', 'get'])
        return ret

    def saveByteString(self, byte_string, path):
        with open(path, 'wb') as file:
            base_string = byte_string
            img_data = base_string.encode()
            content = base64.b64decode(img_data)
            file.write(content)

    def getMail(self, senders=(), subject=None, depth=50):
        depth = -(depth//-10)-1

        search_dict = {}
        if senders:
            sender_str = ', '.join(senders)
            search_dict['participants'] = sender_str
        if subject is not None:
            search_dict['subject'] = subject

        search_str = ' AND '.join([f"{key}:{val}" for key, val in search_dict.items()])

        # Adding an empty search parameter gives the error unexpected character at position 0
        if search_str:
            req = f"messages?$search=\"{search_str}\""
        else:
            req = f"messages"

        if not self.batch_instructions:
            ret = self.get(req, nextLinkLimit=depth)
        else:
            self.addBatch([req, 'get'])
            ret = 'Added mail request to batch queue.'
        return ret

    def sendMail(self, sender='0cded3a1-2c4c-4eff-8393-399b58925455', recipients='gseaward@nubuildinc.ca',
                 subject='default', body='default email', saveToSentItems=False, attachments=None, time_to_send=None):
        self.settings.refresh()
        self.mode = 'user'
        if type(recipients) is str:
            recipients = [recipients]
        body = {
            "message": {
                "subject": subject,
                "body": {
                    "contentType": "HTML",
                    "content": body
                },
                "toRecipients": [
                    {
                        "emailAddress": {
                            "address": mail
                        }
                    }
                    for mail in recipients
                ]
            },
            "saveToSentItems": saveToSentItems
        }

        if time_to_send is not None:
            if type(time_to_send) is str:
                # add four hours to get to Greenwich time.
                date_str = parser.parse(time_to_send) + timedelta(hours=4)
            else:
                date_str = time_to_send
            date_str = date_str.strftime("%Y-%m-%dT%X")
            body['message']['singleValueExtendedProperties'] = [{"id": "SystemTime 0x3FEF", "value": date_str}]
        # attachments is of the form:
        # [ {'name': filename, 'path': local_path} ]

        if attachments is not None:
            if type(attachments) is str or type(attachments) is dict:
                attachments = [attachments]
            print(attachments)
            body['message']['attachments'] = [
                {"@odata.type": "#microsoft.graph.fileAttachment", "name": attachment['name'],
                 "contentType": "text/plain", "contentBytes": self.getBytes(attachment['path'])} for attachment in attachments]

        ret = self.post(f"{sender}/sendMail", json.dumps(body))
        self.settings.revert()
        return ret

    def makeFolder(self, parent_ref, name):
        if self.verbose:
            print(f"Creating folder with name '{name}'")
        folder = '{"name": "'+name+'", "folder": {}}'
        url = parent_ref
        if not self.checkForItem(url):
            url += ':'
        ret = self.post(f'{url}/children', folder)
        return ret

    def moveFile(self, item_id, p_ref):
        ret = self.patch(f"{item_id}", {'parentReference': {'id': f"{p_ref}"}})
        return ret

    def upload(self, given=None, pref=None, name=None, path=None):
        # expected input should be
        # [parentReference, item name, body]
        # or a list of the above
        ret = []

        if given is None:
            given = [pref, name, path]

        if not given:
            return []

        def upload(inp_list, ret_list):
            pRef = inp_list[0]
            item = inp_list[1]
            body = inp_list[2]
            # print(f"testing graphapi {pRef} : {item} : {body}")

            if type(body) is str and len(body) < 150:
                body = self.getBytes(body)
            print(f"pRef: {pRef}, item: {item}, body: {body[-20:]}")
            if type(body) is str:
                # turn body into bytestream
                body = body.encode()
                body = base64.b64decode(body)

            formatted_item = f"/{item}:"
            if pRef[-1] == ':':
                pRef = pRef[:-1]
            elif pRef.find(':') == -1:
                formatted_item = ':' + formatted_item

            response = self.put(f"{pRef}{formatted_item}/content", body)
            return response

        if type(given[0]) is list:
            # list of files was given
            for sub_input in given:
                ret.append(upload(sub_input, ret))
        else:
            # we're only uploading a single file
            ret = upload(given, ret)

        return ret

    def rename(self, item_id, name):
        body = {"name": name}
        self.patch(item_id, body)

    def uploadToJob(self, requests):
        # data needs to be list of [[rpat, folder_name, file_name, body], .. ]
        if self.verbose:
            print(f"Uploading: {requests}")
        self.batch_instructions = False
        self.drive = self.rogers_drive
        self.checkMeta()
        ret = []
        if not self._batch:
            self.settings.refresh()
            self.batch_instructions = True
            self.drive = self.rogers_drive
            self.mode = 'drive'
            folders_to_check = []
            for req in requests:
                rpat = req[0]
                folder_name = req[1]
                file_name = req[2]
                body = req[3]
                job_info = self.checkMeta(rpat)
                if job_info is not None:

                    response_id = self.get(f"{job_info['id']}/children?$select=id,name")
                    # I added rpat and None to the end, None is if a folder is made for that job
                    folders_to_check.append([response_id, req, job_info['id'], job_info, None])
                else:
                    print(f"Couldn't find {rpat}")

            self.batch()

            self.settings.revert()
            for idx, value in self.batch_results.items():
                for request in folders_to_check:
                    found_id = None
                    if idx != request[0]:
                        continue

                    if request[4]:
                        found_id = request[4]
                    else:
                        for folder in value['value']:
                            if self.simpleStr(folder['name']) == self.simpleStr(request[1][1]):
                                # Change this if batch putting ever changes
                                found_id = folder['id']

                    if not found_id:
                        if self.verbose:
                            print(f"No {request[1][1]} found, creating folder...")
                        self.settings.refresh()
                        self.batch_instructions = False
                        self.drive = self.rogers_drive
                        self.mode = 'drive'

                        self.makeFolder(request[2], request[1][1])
                        newfolder = self.response

                        if 'id' in newfolder.keys():
                            found_id = newfolder['id']
                            # go through and let all items know
                            for f in folders_to_check:
                                if f[3] == request[3]:
                                    f[4] = found_id

                        self.settings.revert()

                    parent_ref = found_id
                    item_name = request[1][2].replace(':', ';')
                    body = request[1][3]
                    ret.append(self.upload([parent_ref, item_name, body]))
            print(f"Done uploading")
            return ret
        else:
            err_msg = "There are requests in the batch! Didn't submit"
            print(err_msg)
            return err_msg

    def getMeta(self, file_path='SaveData/meta2.0.json'):
        if self.meta_type == '1.0':
            self.settings.refresh()
            self.batch_instructions = False
            self.drive = self.rogers_drive
            self.mode = 'drive'

            self.get(self.params["resource_location"] + "/Meta.json:/content")
            self.meta = self.response

            self.settings.revert()
            return self.meta
        elif self.meta_type == '2.0':
            if self.meta_remote:
                self.settings.refresh()
                self.batch_instructions = False
                self.drive = self.rogers_drive
                self.mode = 'drive'

                self.get(f"{self.meta2_id}/content")
                self.meta = self.response

                self.settings.revert()
            else:
                with open(file_path) as file:
                    meta = json.load(file)
                self.meta = meta
                return meta

    def uploadMeta(self, body_loc='SaveData/meta2.0.json'):
        given = ["01ZWWTLPOYCEEUUCLJKVH2ET6IENFZ3SID", 'meta2.0.json', body_loc]
        self.upload(given)

    def checkMeta(self, job_num_raw='', strict=False):

        if not job_num_raw:
            return

        job_num_raw = job_num_raw.upper()

        def check():
            job_num = job_num_raw
            period_loc = job_num_raw.find('.')
            if period_loc != -1:
                job_num = job_num[:period_loc]

            if self.meta_type == '1.0':
                for job in self.meta['job data']:
                    if job_num.upper() == job['NuBuild#']:
                        return job
                    if job_num.upper() in job['RPAT']:
                        return job
            elif self.meta_type == '2.0':
                for nb, job in self.meta.items():
                    # check nubuild number first
                    if nb.lower() == job_num.lower():
                        job_info = job.copy()
                        job_info.update({"NuBuild#": nb})
                        return job_info
                    # check rpats
                    if 'ADM' not in job:
                        continue
                    customer_ids = []
                    for i in ['RPAT', 'ADM', 'customer id']:
                        if i in job:
                            customer_ids += job[i]
                    for listed_rpat in customer_ids:
                        listed_period_loc = listed_rpat.find('.')
                        if listed_period_loc != -1:
                            listed_rpat = listed_rpat[:listed_period_loc]
                        if strict:
                            if listed_rpat == job_num:
                                job_info = job.copy()
                                job_info.update({"NuBuild#": nb})
                                return job_info
                        elif listed_rpat.find(job_num) != -1:
                            job_info = job.copy()
                            job_info.update({"NuBuild#": nb})
                            return job_info

            return None

        if self.meta is None:
            self.getMeta()

        def get_specific_job(nb):
            nb_num = nb.lower()
            job_info = self.meta[nb_num].copy()
            job_info.update({"NuBuild#": nb_num})
            return job_info

        # check if input is ftth name
        name = job_num_raw.replace(' ', '').lower()
        if name == 'clearview':
            return get_specific_job('21-147')
        if name == 'innisfil':
            return get_specific_job('21-146')

        return check()

    @staticmethod
    def checkForItem(input_string):
        pot_item = input_string[:34]
        if pot_item.find('/') != -1 or pot_item.find('\\') != -1:
            return False
        if any(char.isdigit() for char in pot_item):
            digitless_string = ''
            for char in pot_item:
                if not char.isdigit():
                    digitless_string += char
            if len(digitless_string) > 0:
                if len(input_string) > 34:
                    if input_string[34] != '/' and input_string[34] != '\\' and input_string[34] != ':':
                        return False
                return True

    @staticmethod
    def getBytes(path='ExamplePDFs\\Temp\\NuDriveForms\\Vac Work Order 0.pdf'):
        with open(path, 'rb') as raw_bytes:
            encoded_string = str(base64.b64encode(raw_bytes.read()))
            encoded_string = encoded_string[2:-1]
        return encoded_string

    def next_link(self, response):

        if '@odata.nextLink' not in response.keys():
            return
        sub_link = response['@odata.nextLink']
        sub_link = sub_link.replace('https://graph.microsoft.com/v1.0/', '')
        if sub_link.find('drive') != -1:
            sub_link = sub_link[sub_link.find('drive'):]
            sub_link = sub_link[sub_link.find('/')+1:]
            sub_link = sub_link[sub_link.find('/')+1:]
        return sub_link

    def get(self, req='', nextLinkLimit=1000):
        url = req
        input_is_item = self.checkForItem(req)
        if input_is_item:
            url = f"items/{req}"

        self.setPrefix()
        if not self.batch_instructions:
            if self.verbose:
                print(f'Get {self.prefix}{url}')
            ret = None
            response = self.request('get', self.prefix + url, verbose=False)  # Get('', self.prefix + url, verbose=False)
            if response:
                if type(response) == bytes:
                    return self.respond(response)
                if req[-7:].lower() == 'content':
                    return self.respond(response)
                ret = json.loads(response)
                if self.use_next and '@odata.nextLink' in ret.keys():
                    sub_link = ret['@odata.nextLink']
                    for i in range(nextLinkLimit):
                        sub_link = sub_link.replace('https://graph.microsoft.com/v1.0/', '')
                        if self.verbose:
                            print(f'Get data overflow ({i})')
                        sub_ret = self.request('get', sub_link, verbose=False)
                        if sub_ret:
                            sub_ret_json = json.loads(sub_ret)
                            if 'value' in sub_ret_json.keys():
                                ret['value'] += sub_ret_json['value']
                            if '@odata.nextLink' in sub_ret_json.keys():
                                sub_link = sub_ret_json['@odata.nextLink']
                            else:
                                if '@odata.deltaLink' in sub_ret_json.keys():
                                    self.delta_link = sub_ret_json['@odata.deltaLink']
                                break

            return self.respond(ret)
        else:
            ret = self.addBatch([url, 'get'])
            return ret

    def delete(self, req=''):
        url = req
        input_is_item = self.checkForItem(req)
        if input_is_item:
            url = f"items/{req}"
        self.setPrefix()
        if not self.batch_instructions:
            if self.verbose:
                print(f'Delete {self.prefix}{url}')
            print(self.prefix+url)
            response = self.request('delete', self.prefix + url, verbose=False)
            return self.respond(response)
        else:
            ret = self.addBatch([url, 'delete'])
            return ret

    def post(self, req='', body=''):
        url = req
        input_is_item = self.checkForItem(req)
        if input_is_item:
            url = f"items/{req}"
        self.setPrefix()
        if not self.batch_instructions:
            if self.verbose:
                print(f'Post {self.prefix}{url}')
            response = self.request('post', self.prefix + url, data=body, verbose=False)
            return self.respond(response)
        else:
            ret = self.addBatch([url, 'post', body])
            return ret

    def patch(self, req='', body=''):
        url = req
        input_is_item = self.checkForItem(req)
        if input_is_item:
            url = f"items/{req}"

        self.setPrefix()
        if not self.batch_instructions:
            if self.verbose:
                print(f'Patch {self.prefix}{url}')
            response = self.request('patch', self.prefix + url, data=body, verbose=False)
            return self.respond(response)
        else:
            ret = self.addBatch([url, 'patch', body])
            return ret

    def put(self, req='', body=''):
        url = req
        input_is_item = self.checkForItem(req)
        if input_is_item:
            url = f"items/{req}"

        self.setPrefix()
        if not self.batch_instructions:
            if self.verbose:
                print(f'Put {self.prefix}{url}')
            response = self.request('put', self.prefix + url, data=body, verbose=False)
            return self.respond(response)
        else:
            ret = self.addBatch([url, 'put', body])
            return ret
