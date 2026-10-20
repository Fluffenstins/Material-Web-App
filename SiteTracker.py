import json
import requests
from datetime import datetime, timedelta, timezone
import threading
from functools import partial


class SiteTrackerDrive:
    def __init__(self):
        self.params = None
        self.instance_url = None
        self.access_token = None
        self.api_version = None
        self.consumer_key = None
        self.consumer_secret = None

        self.load_params()

    def now(self, return_string=True):
        date_obj = datetime.now(timezone.utc)
        if return_string:
            return self.time_to_str(date_obj)
        return date_obj

    @staticmethod
    def time_to_str(datetime_obj, include_time=True):
        if include_time:
            return datetime_obj.isoformat()[:19]  # gets rid of time zone changes and decimal seconds
        else:
            return datetime_obj.strftime('%Y-%m-%d')

    def load_params(self):
        with open("Parameters.json") as file:
            self.params = json.load(file)
        self.access_token = self.params['sitetracker_access_token']
        self.instance_url = self.params['sitetracker_instance_url']
        self.api_version = self.params['sitetracker_api_version']
        self.consumer_key = self.params['sitetracker_consumer_key']
        self.consumer_secret = self.params['sitetracker_consumer_secret']

    def update_saved_token(self):
        with open("Parameters.json") as file:
            params = json.load(file)
        params['sitetracker_access_token'] = self.access_token
        with open("Parameters.json", 'w') as file:
            json.dump(params, file, indent=2)

    def request_access_token(self):
        print("Access token is expired, requested a new one.")
        header = {"Content-Type": "application/x-www-form-urlencoded"}
        response = requests.post(
            url=f"{self.instance_url}/services/oauth2/token",
            headers=header,
            data={
                "grant_type": "client_credentials",
                "client_id": self.consumer_key,
                "client_secret": self.consumer_secret
            }
        )

        data = response.json()
        if 'access_token' in data:
            self.access_token = data['access_token']
        else:
            raise KeyError(f"No access token was provided when refreshing. {data}")

        self.update_saved_token()
        print("New access token retrieved.")
        return response.json()

    @property
    def header(self):
        header = {
            'Authorization': f"Bearer {self.access_token}",
            'Content-Type': 'application/json'
        }
        return header

    def full_request(self, query, base_url=False):
        if base_url:
            full_request = f"{self.instance_url}/{query}"
        else:
            full_request = f"{self.instance_url}/services/data/v{self.api_version}/{query}"
        return full_request

    def request(self, query, request_type, data=None, base_url=False):
        full_request = self.full_request(query, base_url=base_url)
        response = None

        if request_type == 'get':
            response = requests.get(full_request, headers=self.header)
        if request_type == 'patch':
            response = requests.patch(full_request, headers=self.header, json=data)
        if request_type == 'post':
            response = requests.post(full_request, headers=self.header, json=data)

        if response.status_code // 100 != 2:
            try:
                print(response.status_code)
                if response.json()[0]['errorCode'] == 'INVALID_SESSION_ID':
                    self.request_access_token()
                    response = self.request(
                        query=query,
                        request_type=request_type,
                        data=data
                    )
            except KeyError:
                pass
            except TypeError:
                pass
            except Exception as e:
                print(response.content)
                raise e

        return response

    def get(self, query, base_url=False):
        return self.request(query, 'get', base_url=base_url)

    def patch(self, query, data):
        return self.request(query, 'patch', data=data)

    def post(self, query, data):
        return self.request(query, 'post', data=data)

    def list_objects(self):
        """
        :return: list of sitetracker objects
        """
        ret = self.get(f'sobjects').json()['sobjects']
        return ret

    def list_records(self, object_id, keys: list = None, filters: list = None):
        if keys is None:
            keys = []
        keys += ['id', 'name']
        keys = sorted(list(set(keys)))

        filter_string = ""
        if filters:
            filter_string = " AND ".join(filters)
            filter_string = "WHERE " + filter_string

        column_string = ",".join(keys)

        ret = self.execute_sql_query(f"select {column_string} from {object_id} {filter_string}")
        ret = ret.json()['records']
        return ret

    def get_record(self, object_id, record_id, keys: list = None):
        if keys is None:
            keys = []
        keys += ['id', 'name']
        keys = sorted(list(set(keys)))

        column_string = ",".join(keys)

        ret = self.execute_sql_query(f"select {column_string} from {object_id} where id = '{record_id}'")

        ret = ret.json()['records'][0]
        return ret

    def list_object_fields(self, object_id):
        """
        :param object_id: api ID of the Salesforce object
        :return: a list of fields
        """
        ret = self.get(f'sobjects/{object_id}/describe').json()['fields']
        return ret

    def execute_sql_query(self, sql_string):
        """
        :param sql_string: string, content of an sql query:
        "select name from account"
        :return:
        """
        sql_string = sql_string.replace(" ", "+")
        query = f"query?q={sql_string}"
        return self.get(query)

    def update_record_values(self, object_id, record_id, data_dict):
        """
        :param object_id: api ID of the Salesforce object
        :param record_id: api ID of the Salesforce object record
        :param data_dict: a dict where the keys are the api IDs of the fields,
        and the values are the new values for those fields on the given record
        :return: a response object
        """
        ret = self.patch(f"sobjects/{object_id}/{record_id}", data=data_dict)
        return ret

    def create_record(self, object_id, data_dict):
        ret = self.post(f'sobjects/{object_id}', data=data_dict)
        return ret.json()

    def async_create_record(self, object_id, data_dict):
        thread = threading.Thread(target=partial(self.create_record, object_id=object_id, data_dict=data_dict))
        thread.start()

    def download_content_document(self, content_document_id, save_path=None):
        """
        :param content_document_id:
        :param save_path:
        :return file path as a string:

        Downloads only the latest version by default.
        """
        keys = ['title', 'fileextension', 'LatestPublishedVersionId']
        key_str = ','.join(keys)
        content_document = self.execute_sql_query(f"SELECT {key_str} FROM ContentDocument WHERE id = '{content_document_id}'").json()['records'][0]

        file_version_id = content_document['LatestPublishedVersionId']
        name = f"{content_document['Title']}.{content_document['FileExtension']}"
        link = f"sobjects/ContentVersion/{file_version_id}/VersionData"
        data = self.get(link, base_url=False)

        if save_path is None:
            save_path = name

        with open(save_path, 'wb') as file:
            file.write(data.content)

        return name

    def download_st_file(self, file_record_id):
        object_id = 'sitetracker__Attachment__c'
        record = self.get_record(
            object_id=object_id,
            record_id=file_record_id,
            keys=['sitetracker__ContentDocumentRecord__c']
        )
        ret = self.download_content_document(record['sitetracker__ContentDocumentRecord__c'])
        return ret

    def list_project_files(self, project_record_id=None):
        object_id = 'sitetracker__Attachment__c'
        keys = [
            'id',
            'name',
            'sitetracker__Proj__c',  # project record ID
            'sitetracker__Content_Type__c',  # word describing file type
            'sitetracker__Url__c',  # download link
            'sitetracker__ContentDocumentRecord__c',
            'sitetracker__External_File_Name__c'
        ]

        column_string = ",".join(keys)

        if project_record_id is None:
            ret = self.execute_sql_query(f"SELECT {column_string} FROM {object_id} WHERE sitetracker__Proj__c != NULL")
        else:
            ret = self.execute_sql_query(f"SELECT {column_string} FROM {object_id} WHERE sitetracker__Proj__c = '{project_record_id}'")

        ret = ret.json()['records']

        return ret


class SiteTrackerExplorer(SiteTrackerDrive):
    def __init__(self):
        """
        A focus on automation of specific tasks, as opposed to simply exposing the API

        """
        super().__init__()

    def find_user_resource(self, name):
        possible_resources = self.list_records(
            object_id='sitetracker__Timesheet_User__c',
            keys=['name'],
            filters=[f'Name = \'{name}\' OR Name = \'{name} - Training\'']
        )
        if len(possible_resources) == 1:
            return possible_resources[0]
        raise KeyError(f"User not determined. {len(possible_resources)} possibilities found.")

    def list_possible_crew_mates(self, user_resource_record_id):
        """
        Looks through every crew the user is a part of and lists all users in those crews.
        This is useful for time tracking as it should list everyone that you might want to log time for.
        :param user_resource_record_id:
        :return list of user resource dictionaries:
        """
        crew_resource_record_ids = self.list_my_resource_ids(user_resource_record_id)
        crew_list_str = ','.join(f"'{i}'" for i in crew_resource_record_ids)

        records = self.list_records(
            'sitetracker__Crew_Resource__c',
            keys=['sitetracker__Resource__r.name', 'sitetracker__Resource__c', 'sitetracker__Crew__c'],
            filters=[f'sitetracker__Crew__c in ({crew_list_str})']
        )
        # names = [record['sitetracker__Resource__r']['Name'] for record in records]
        # names = sorted(list(set(names)))
        return records

    def list_my_projects(self, user_resource_record_id):
        """
        Currently it will only look at what work you are allocated
        Ideally this would eventually include more broad information and allow overwrites
        :return:
        """
        allocations = self.list_my_allocations(user_resource_record_id=user_resource_record_id)
        # my_project_record_ids = sorted(list(set([i['Project__c'] for i in allocations])))
        # nubuild_ids = sorted(list(set([i['Project__r']['NuBuild_Project_ID__c'] for i in allocations])))

        ret = {}
        for allocation in allocations:
            ret[allocation['Project__r']['NuBuild_Project_ID__c']] = allocation['Project__r']

        print(json.dumps(ret, indent=1))

        print(f"Allocations: {len(ret)}")
        return ret

    def list_my_resource_ids(self, user_resource_record_id):
        # include both user resource and crew resources that the user is a part of
        possible_resources = [user_resource_record_id]
        # include any resources that are crews that the user is a part of
        crew_resources = self.list_my_crew_resources(user_resource_record_id)
        possible_resources += [i['sitetracker__Crew__c'] for i in crew_resources]
        print(f"My resources: {possible_resources}")
        return possible_resources

    def list_my_allocations(self, user_resource_record_id, project_record_id=None):
        resource_record_ids = self.list_my_resource_ids(
            user_resource_record_id=user_resource_record_id
        )
        possible_resources_str = ",".join([f"\'{i}\'" for i in resource_record_ids])

        filters = [f"sitetracker__Planned_Resource__c in ({possible_resources_str})"]
        if project_record_id is not None:
            filters.append(f"Project__c = '{project_record_id}'")

        keys = [
            'Project__c',
            'Project__r.Id',
            'Project__r.NuBuild_Project_ID__c',
            'sitetracker__Item__c',
            # 'sitetracker__Item__r.sitetracker__Description__c',
            'sitetracker__Total_Planned_Amount__c',
            'Mobile_Allocation_Summary__c',
            'NB_Non_Rejected_Work_Log_Qty__c',
            'sitetracker__Planned_Resource__c',
            'sitetracker__Production_Plan_Line__c'
        ]

        allocations = self.list_records(
            'sitetracker__Production_Line_Allocation__c',
            keys=keys,
            filters=filters
        )

        return allocations

    def list_my_crew_resources(self, user_resource_record_id: str = None):
        filters = []
        if user_resource_record_id is not None:
            filters.append(f"sitetracker__Resource__c = '{user_resource_record_id}'")
        records = self.list_records(
            'sitetracker__Crew_Resource__c',
            keys=['sitetracker__Crew__r.name', 'sitetracker__Resource__c', 'sitetracker__Crew__c'],
            filters=filters
        )
        return records

    def get_item_info(self, item_id_list):
        keys = ['name']
        possible_items_str = ','.join([f"\'{i}\'" for i in item_id_list])
        filters = [f"Id in ({possible_items_str})"]
        # filters = None
        items = self.list_records(
            'sitetracker__Item__c',
            keys=keys,
            filters=filters
        )
        return items

    def create_time_entry(self, project_id, resource_id, work_start, work_end):
        ret = self.create_record(
            object_id='NuBuild_Time_Entry__c',
            data_dict={
                'Resource__c': resource_id,
                'Project__c': project_id,
                'Work_Start__c': work_start,
                'Work_End__c': work_end,
                'Status__c': "Submitted"
            }
        )

        return ret

    def create_work_log(self, project_id, service_id, resource_id, qty, comments):
        project_id = project_id
        item_id = service_id
        resource_id = resource_id
        qty = qty
        comments = comments

        start_date = self.now(return_string=True)
        end_date = self.now(return_string=True)
        print(start_date)
        print(end_date)

        # get the resource_id for the allocated resource
        my_allocations = self.list_my_allocations(resource_id)
        potential_allocations = [i for i in my_allocations if i['Project__c'] == project_id and i['sitetracker__Item__c'] == item_id]

        if len(potential_allocations) == 0:
            raise IndexError(f"Unable to find an allocation for the given person ({resource_id}), project ({project_id}), and item ({item_id}).")

        # if there are multiple allocation matches, default to the user, if not, pick the first matching crew
        try:
            selected_allocation_record = [i for i in potential_allocations if i['sitetracker__Planned_Resource__c'] == resource_id][0]
        except IndexError:
            selected_allocation_record = potential_allocations[0]

        selected_resource_id = selected_allocation_record['sitetracker__Planned_Resource__c']

        print(f"Allocation: {json.dumps(selected_allocation_record, indent=1)}")

        data_dict = {
                'sitetracker__Actual_Resource__c': selected_resource_id,
                'sitetracker__Item__c': item_id,
                'sitetracker__Project__c': project_id,
                'sitetracker__Comments__c': comments,
                'sitetracker__Quantity__c': qty,
                'sitetracker__Production_Line_Allocation__c': selected_allocation_record['Id'],
                'sitetracker__st_Production_Plan_Line__c': selected_allocation_record['sitetracker__Production_Plan_Line__c'],
                'sitetracker__Start_Date__c': start_date,
                'sitetracker__End_Date__c': end_date,
                'sitetracker__Status__c': 'Submitted'
            }
        print(json.dumps(data_dict, indent=1))
        ret = self.async_create_record(
            object_id='sitetracker__Production_Work_Log__c',
            data_dict=data_dict
        )

        print(f"create_work_log output:")
        print(ret)
        return ret


if __name__ == '__main__':
    pass
