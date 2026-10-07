from SiteTracker import SiteTrackerExplorer
from MaterialContainer import CoreMaterialManager


def ensure_st_projects():
    st_explorer = SiteTrackerExplorer()
    mt_container = CoreMaterialManager()
    mt_container.save_after_action = False
    mt_container.load_json()

    projects = st_explorer.list_records(
        'sitetracker__Project__c',
        keys=[
            'sitetracker__Project_Status__c',
            'Customer_Project_ID__c',
            'NuBuild_Project_ID__c',
            'Parent_Project__c',
            'Location__c',
            'Project_Name__c'
        ]
    )

    for project in projects:
        nb_id = project['NuBuild_Project_ID__c']
        status = project['sitetracker__Project_Status__c']
        customer_id = project['Customer_Project_ID__c']
        location = project['Location__c']
        parent_project_st_id = project['Parent_Project__c']
        st_id = project['Id']

        if customer_id is None:
            customer_id = project['Project_Name__c']

        existing_project = mt_container.find_project(nb_id)
        if existing_project is None:
            mt_container.create_project(
                status=status,
                customer_id=customer_id,
                nb_id=nb_id,
                st_id=st_id,
                location=location
            )
        else:
            # need to patch the existing project
            pass

    mt_container.save_json()


if __name__ == '__main__':
    ensure_st_projects()
