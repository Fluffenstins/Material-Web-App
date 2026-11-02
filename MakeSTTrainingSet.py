from SiteTracker import SiteTrackerExplorer
import json


ST_EXPLORER = SiteTrackerExplorer()


def make_example_project():
    quote = make_quote()
    add_blended_line(quote['id'])
    add_quote_line(quote['id'], 'a1EOH000003AkJB2A0', 15)
    add_quote_line(quote['id'], 'a1EOH000003AjAE2A0', 30)


def make_quote():
    # make a basic quote
    data_dict = {
        'Company__c': 'Construction',
        'Account__c': '001au00000LGIoEAAX',  # account
        'Rate_Card__c': 'a3wOH000004zKHFYA2',  # customer rate card
        'Contact__c': '003au00000Ex38NAAR',  # customer rep
        'Internal_Notes__c': 'Training Example'
    }
    ret = ST_EXPLORER.create_record(
        object_id='NuBuild_Quote__c',
        data_dict=data_dict
    )

    quote_id = ret['id']
    print(f"Quote: {ret}")
    return ret


def make_project(quote_id):
    data_dict = {
        'sitetracker__ProjectTemplate__c': 'a20OH000005bOYNYA2',
        'NuBuild_Account__c': '001au00000LGIoEAAX',  # account
        'NuBuild_Rate_Card__c': 'a3wOH000004zKHFYA2',  # customer rate card
        'NuBuild_Contact__c': '003au00000Ex38NAAR',  # customer rep
        'Hierarchy_Type__c': 'Standalone',
        'Project_Name__c': "Standalone Example - Training"
    }
    ret = ST_EXPLORER.create_record(
        object_id='sitetracker__Project__c',
        data_dict=data_dict
    )

    data_dict = {
        'Project__c': ret['id'],
        'Quote__c': quote_id
    }
    ret = ST_EXPLORER.create_record(
        object_id='Project_Quote__c',
        data_dict=data_dict
    )
    print(f"Project: {ret}")


def add_blended_line(quote_id):
    qty = 1000
    data_dict = {
        'Item__c': 'a1EOH0000035AD72AM',
        'Quantity__c': qty,
        'Quote__c': quote_id,
        'NB_Composite_Role__c': 'Blended Parent',
        "NB_Work_Classification__c": "BBDT4S-L - 100mm blended bore installation",
    }
    ret = ST_EXPLORER.create_record(
        object_id='NuBuild_Quote_Line_Item__c',
        data_dict=data_dict
    )
    print(f"Blended: {ret}")
    for item_id in ['a1EOH0000038ARt2AM', 'a1EOH0000038AV72AM', 'a1EOH0000038AN32AM']:
        data_dict = {
            'Quantity__c': qty,
            'Quote__c': quote_id,
            "Item__c": item_id,
            "NB_Composite_Role__c": "Work Method",
            "NB_Work_Classification__c": "BBDT4S-L - 100mm blended bore installation",
        }
        ret = ST_EXPLORER.create_record(
            object_id='NuBuild_Quote_Line_Item__c',
            data_dict=data_dict
        )
        print(f"Work Line: {ret}")


def query_record(record_id):
    ret = ST_EXPLORER.execute_sql_query(f"SELECT FIELDS(ALL) FROM sitetracker__Project__c WHERE Id = '{record_id}' LIMIT 200")
    data = ret.json()
    print(json.dumps(data, indent=1))


def add_quote_line(quote_id, item_id, qty):
    data_dict = {
        'Item__c': item_id,
        'Quantity__c': qty,
        'Quote__c': quote_id
    }
    ret = ST_EXPLORER.create_record(
        object_id='NuBuild_Quote_Line_Item__c',
        data_dict=data_dict
    )
    print(F"Regular quote line: {ret}")
    return ret


if __name__ == '__main__':
    make_project('a47OH00000MXgDVYA1')
    # query_record('a21OH000000fgZZYAY')
