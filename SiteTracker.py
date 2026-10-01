import json
import requests
from datetime import datetime, timedelta, timezone


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
            return datetime_obj.isoformat()
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

    def download_content_document(self, content_document_id):
        """
        :param content_document_id:
        :return file path as a string:

        Downloads only the latest version by default.
        """
        keys = ['title', 'fileextension', 'LatestPublishedVersionId']
        key_str = ','.join(keys)
        content_document = self.execute_sql_query(f"SELECT {key_str} FROM ContentDocument WHERE id = '{content_document_id}'").json()['records'][0]

        file_version_id = content_document['LatestPublishedVersionId']
        name = f"{content_document['Title']}.{content_document['FileExtension']}",
        link = f"sobjects/ContentVersion/{file_version_id}/VersionData"

        data = self.get(link, base_url=False)
        with open(name, 'wb') as file:
            file.write(data.content)

        return name

    def download_st_file(self, file_record_id):
        object_id = 'sitetracker__Attachment__c'
        record = self.get_record(
            object_id=object_id,
            record_id=file_record_id,
            keys=['sitetracker__ContentDocumentRecord__c']
        )
        self.download_content_document(record['sitetracker__ContentDocumentRecord__c'])

    def list_project_files(self, project_record_id=None):
        object_id = 'sitetracker__Attachment__c'
        keys = [
            'id',
            'name',
            'sitetracker__Proj__c',  # project record ID
            'sitetracker__Content_Type__c',  # word describing file type
            'sitetracker__Url__c',  # download link
            'sitetracker__ContentDocumentRecord__c'
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
            filters=[f'Name = \'{name}\'']
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
        my_project_record_ids = sorted(list(set([i['Project__c'] for i in allocations])))
        nubuild_ids = sorted(list(set([i['Project__r']['NuBuild_Project_ID__c'] for i in allocations])))
        for i in nubuild_ids:
            print(i)

        ret = {}
        for allocation in allocations:
            ret[allocation['Project__r']['NuBuild_Project_ID__c']] = allocation['Project__r']

        return ret

    def list_my_resource_ids(self, user_resource_record_id):
        # include both user resource and crew resources that the user is a part of
        possible_resources = [user_resource_record_id]
        # include any resources that are crews that the user is a part of
        crew_resources = self.list_my_crew_resources(user_resource_record_id)
        possible_resources += [i['sitetracker__Crew__c'] for i in crew_resources]
        return possible_resources

    def list_my_allocations(self, user_resource_record_id, project_record_id=None):
        resource_record_ids = self.list_my_resource_ids(
            user_resource_record_id=user_resource_record_id
        )
        possible_resources_str = ",".join([f"\'{i}\'" for i in resource_record_ids])

        filters = [f"sitetracker__Planned_Resource__c in ({possible_resources_str})"]
        if project_record_id is not None:
            filters.append(f"Project__c = '{project_record_id}'")

        allocations = self.list_records(
            'sitetracker__Production_Line_Allocation__c',
            keys=['Project__c', 'Project__r.NuBuild_Project_ID__c'],
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


if __name__ == '__main__':
    pass
