from GraphAPI import MSDrive
import json
from app import generate_gala_qr_code


class GalaEmailer:
    def __init__(self):
        self.GALA_SAVE_NAME = 'gala_save_data.json'

        self.drive = MSDrive()
        self.drive.batch_instructions = False

        self.gala_data = None

    def download_gala_data(self):
        existing_gala_data = self.drive.get(f"01ZWWTLPLOUELMUI5ETRHZCJROLL2W2OU4:/{self.GALA_SAVE_NAME}:/content")
        if isinstance(existing_gala_data, dict) and 'error' not in existing_gala_data:
            with open(f"{self.GALA_SAVE_NAME}", 'w') as file:
                json.dump(existing_gala_data, file, indent=2)
        return existing_gala_data

    def ensure_gala_data(self):
        if self.gala_data is not None:
            return self.gala_data
        return self.download_gala_data()

    def list_attendees(self):
        gala_data = self.ensure_gala_data()
        ret = []
        for table_id, table_members in gala_data.items():
            for name, attendee_data in table_members.items():
                ret.append(attendee_data)
        return ret

    # def list_emails(self):
    #     gala_data = self.ensure_gala_data()
    #     ret = [attendee['email'] for attendee in self.list_attendees()]
    #     ret = sorted(ret)
    #     return ret

    def send_email(self, attendee, pdf_path, subject):

        generate_gala_qr_code(provided_name=attendee['name'], submission_id=attendee['submission_id'])
        attachments = [
            {'name': 'Reminder.png', 'path': pdf_path},
            {'name': 'QRCode.png', 'path': 'label.png'}
        ]

        body = '''<img src='cid:Reminder.png' alt='Reminder Image'/>'''
        body = body.replace('\n', '<br>')
        self.drive.sendMail(
            sender='88b94196-dabe-4d8b-b2f7-d23686f7c95c',  # Alex Russo
            subject=subject,
            recipients=[attendee['email']],
            body=body,
            attachments=attachments
        )

    def send_3_week_reminder(self):
        for attendee in self.list_attendees():
            self.send_email(attendee=attendee, pdf_path='3WeekReminder.png', subject="NuBuild Gala: 3 Weeks to Go!")


if __name__ == '__main__':
    emailer = GalaEmailer()
    emailer.send_3_week_reminder()
