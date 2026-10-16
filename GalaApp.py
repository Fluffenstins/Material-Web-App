from GraphAPI import MSDrive
import json
import os
from LabelGen import CustomLabel
import openpyxl
import requests
import threading
from functools import partial
from datetime import datetime, timedelta


GRAPH_DRIVE = MSDrive()
GRAPH_DRIVE.batch_instructions = False
GALA_SAVE_NAME = 'gala_save_data.json'

MOST_RECENT_GALA_DATA = None
UPLOADING_GALA_DATA = False
LAST_DOWNLOAD = None
UPLOAD_TOTAL = 0


def smart_load_submissions():
    global MOST_RECENT_GALA_DATA
    global LAST_DOWNLOAD
    if LAST_DOWNLOAD is None or datetime.now() - timedelta(minutes=2) > LAST_DOWNLOAD:
        print("Refreshing gala download")
        ret = download_gala_data()
        LAST_DOWNLOAD = datetime.now()
        MOST_RECENT_GALA_DATA = ret
        return ret
    return MOST_RECENT_GALA_DATA


def download_gala_data():
    existing_gala_data = GRAPH_DRIVE.get(f"01ZWWTLPLOUELMUI5ETRHZCJROLL2W2OU4:/{GALA_SAVE_NAME}:/content")
    if isinstance(existing_gala_data, dict) and 'error' not in existing_gala_data:
        with open(f"{GALA_SAVE_NAME}", 'w') as file:
            json.dump(existing_gala_data, file, indent=2)
    return existing_gala_data


def async_upload_gala_data(gala_data):
    global MOST_RECENT_GALA_DATA
    global UPLOADING_GALA_DATA
    MOST_RECENT_GALA_DATA = gala_data
    if not UPLOADING_GALA_DATA:
        save_thread = threading.Thread(target=partial(_async_upload_gala_data, gala_data))
        save_thread.start()


def _async_upload_gala_data(gala_data):
    global MOST_RECENT_GALA_DATA
    global UPLOADING_GALA_DATA
    global UPLOAD_TOTAL
    UPLOADING_GALA_DATA = True
    with open(f"{GALA_SAVE_NAME}", 'w') as file:
        json.dump(gala_data, file, indent=2)

    UPLOAD_TOTAL += 1
    ret = GRAPH_DRIVE.upload(
        pref='01ZWWTLPLOUELMUI5ETRHZCJROLL2W2OU4',
        name=GALA_SAVE_NAME,
        path=f"{GALA_SAVE_NAME}"
    )
    print(f"Upload total: {UPLOAD_TOTAL}")

    UPLOADING_GALA_DATA = False
    global MOST_RECENT_GALA_DATA
    if gala_data != MOST_RECENT_GALA_DATA:
        print("It doesn't match")
        return _async_upload_gala_data(MOST_RECENT_GALA_DATA)
    else:
        print("It matches for some reason?")
    return ret


def upload_gala_data(gala_data):
    with open(f"{GALA_SAVE_NAME}", 'w') as file:
        json.dump(gala_data, file, indent=2)

    ret = GRAPH_DRIVE.upload(
        pref='01ZWWTLPLOUELMUI5ETRHZCJROLL2W2OU4',
        name=GALA_SAVE_NAME,
        path=f"{GALA_SAVE_NAME}"
    )

    return ret


download_gala_data()


def load_gala_data():
    try:
        with open(f"{GALA_SAVE_NAME}", 'r') as file:
            truth_dict = json.load(file)
    except FileNotFoundError:
        truth_dict = {}
    return truth_dict


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

    def send_email(self, attendee, subject, pdf_path=None):

        # generate_gala_qr_code(provided_name=attendee['name'], submission_id=attendee['submission_id'])
        attachments = [
            # {'name': 'Reminder.png', 'path': pdf_path},
            # {'name': 'QRCode.png', 'path': 'label.png'}
            {'name': 'QRCode.png', 'path': 'image (9).png', 'isInline': True}
        ]
        body = '''<p><strong>NuBuild 10th Anniversary Gala and Silent Auction</strong><br /> In support of ALS Society of Canada</p>
<p>Bidding is open as of today. Every bid helps support ALS Society of Canada.</p>
<p><strong>Bidding opens:</strong> Today, Wednesday, October 14<br /><strong>Bidding closes:</strong> Friday, October 16 at 10:00 PM (at the Gala)</p>
<hr />
<h3>How to Bid (3 Easy Steps)</h3>
<p>&nbsp;</p>
<p><strong>1. Open the auction</strong><br /><a title="https://mobilbid.co/o/1242/user/magic_links/new" href="https://mobilbid.co/o/1242/user/magic_links/new" target="_blank" rel="noreferrer noopener"><strong>Click Here to Access the Silent Auction</strong></a><br /> or scan the QR code below with your phone&rsquo;s camera</p>
<img src='cid:QRCode.png' alt='Reminder Image'/>
<p><strong>2. Register</strong><br /> Enter your first name, last name, cell number and email.<br /><strong>Use your personal cell and personal email</strong>, not your work email. Company firewalls can block access.</p>
<p><strong>3. Bid!</strong><br /> Browse the items and place your bids anytime until Friday at 10:00 PM.</p>
<hr />
<h3>Good to Know</h3>
<p><strong>Closed the page?</strong> No problem. Click the link in this email again to get back in.</p>
<p><strong>Having trouble getting in?</strong> Save <strong>833-442-1402</strong> to your phone contacts. This is our bidding platform&rsquo;s number, and saving it helps get around phone or security settings that may be blocking you.</p>
<p><strong>Won an item?</strong> Pick it up from the silent auction table at the Gala. Please show your invoice at pickup. All sales are final.</p>
<p><strong>Can&rsquo;t pick up at the Gala?</strong> Contact Alex Russo at <strong>647-802-0330</strong> or <a title="mailto:arusso@nubuildinc.ca" href="mailto:arusso@nubuildinc.ca" target="_blank" rel="noreferrer noopener">arusso@nubuildinc.ca</a> to arrange another pickup.</p>
<p>Thank you for your support, and happy bidding!</p>'''
        # body = '''<img src='cid:Reminder.png' alt='Reminder Image'/>'''
        # body = body.replace('\n', '<br>')
        ret = self.drive.sendMail(
            sender='88b94196-dabe-4d8b-b2f7-d23686f7c95c',  # Alex Russo
            subject=subject,
            recipients=[attendee['email']],
            body=body,
            attachments=attachments
        )
        return ret

    def send_silent_auction_invite(self):
        for attendee in self.list_attendees():
            self.send_email(
                attendee=attendee,
                subject="The Silent Auction Is Now Live!"
            )

    def send_3_week_reminder(self):
        gala_data = self.ensure_gala_data()
        print(self.send_email(attendee=attendee, pdf_path='3WeekReminder.png', subject="NuBuild Gala: 3 Weeks to Go!"))


def generate_gala_qr_code(submission_id, provided_name, save_path="label"):
    link_url = f"nubuildapp.ca/gala/entry?id={submission_id}"
    label = CustomLabel(provided_name, link_url)
    label.save(path=save_path)
    return f"{save_path}.png"


def get_table_qr_codes(table_id='BORING SOLUTIONS'):
    try:
        os.mkdir("Table QR Codes")
    except FileExistsError:
        pass
    truth_dict = load_gala_data()
    for name, submission_data in truth_dict[table_id].items():
        generate_gala_qr_code(provided_name=name, submission_id=submission_data['submission_id'], save_path=f"Table QR Codes/{name}")


def export_gala_as_xlsx():
    gala_data = download_gala_data()

    book = openpyxl.Workbook()
    sheet = book.active

    pointer = 2
    for _, attendee_list in gala_data.items():
        for name, attendee_dict in attendee_list.items():
            attendee_data = [
                name,
                attendee_dict['table'],
                attendee_dict['plus_one_name'],
                attendee_dict['email'],
                attendee_dict['paid'],
                attendee_dict['submission_id'],
                ]
            for x, val in enumerate(attendee_data, start=1):
                sheet.cell(pointer, x).value = val

            pointer += 1

    book.save("GalaExport.xlsx")
    book.close()

    print(gala_data)


def test_email():
    emailer = GalaEmailer()
    emailer.send_email(
        attendee={'email': 'arusso@nubuildinc.ca'},
        subject="The Silent Auction Is Now Live!"
    )


def update_has_plus_ones():
    submission_ids = '''6654361375526617885
6652983842842655314
6652938622841497527
6652890534028992164
6652848332847418176
6652797016232478312
6652477754217896250
6652405289015409512
6652396420221335020
6652385543028727120
6652345779428291928
6652248044561044830
6652242086918365402
6652241620122808805
6652241562841820823
6652241238433061712
6649613242849880042
6649565962846909290
6649420232845101766
6647730162847289080
6677162052846340849
6677161712846447207
6677161462844477066
6677161112845522406
6677160702844143391
6677114902844083242
6677114512849454105
6677113972845560620
6677113462843176648
6677112912847297213
6672919014911900811
6672861906312094237
6672849302459871345
6672848852459426067
6672848552457166715
6672796042453365456
6672792122459513519
6669655000912103161
6666818662848762211
6665143863122543612
6664338022842497395
6664337642846917765
6664337192846530803
6664336842846799545
6664336392849816150
6664323024014796916
6664284242842656429
6664283862848905263
6664283522849741915
6664266864111364487
6661861306139215475
6661819250898589595
6661752907319506448
6661752417319559356
6661752177312948276
6661751637315414037
6661679692841067723
6661667752842695326
6661651457027040378
6661650758711055798
6661646715645815027
6661632084173171676
6661598112843940887
6661597682846656938
6661594672848409636
6661593822842309989
6661106655747481524
6660804581913791032
6660720472511791676
6660219175706946673
6660070621822675794
6659907885627448310
6659894866022596914
6659860885818499794
6659858376372457008
6659849842846769301
6659840042849845627
6659829215673449854
6659813922847401301
6659178001329512775
6658925042841537843
6658371692633187311
6658218689612806248
6656690072315024710
6656410191899337390
6655795338452544068
6655788956011267811
6655748132516114653
6655621872848294567
6655503462842348807
6655502942847700505
6655502472849304151
6655501842847658946
6655501142849461452
6654800962842840309
6654791482841690561
6654755061523915633
6654731909511518812
6654701259124171582
6654685585341031224
6654639140561202154
6654619511667330477
6654612063397723420
6654610782848561157
'''.split('\n')
    submission_ids = [i.strip() for i in submission_ids]

    for submission_id in submission_ids:
        ret = requests.patch('http://192.168.2.71:5000/api/galaEntryUpdate', json={'submission_id': submission_id, 'data': {'has_plus_one': True}})
        print(ret.content)
        if ret.status_code - ret.status_code % 100 == 400:
            print(f"Issue with {submission_id}")


def set_all_statuses():
    gala_dict = download_gala_data()

    for table_id, submissions in gala_dict.items():
        for name, submission in submissions.items():
            data = {'status': 'Submitted'}
            if 'has_plus_one' not in submission:
                data['has_plus_ones'] = False
            ret = requests.patch('https://nubuildapp.ca/api/galaEntryUpdate',
                                 json={'submission_id': submission['submission_id'], 'data': data})
            print(ret.content)

def set_one_statuses():
    data = {'status': 'Submitted'}
    ret = requests.patch('https://nubuildapp.ca/api/galaEntryUpdate',
                         json={'submission_id': '6647926422842720960', 'data': data})
    print(ret.content)


if __name__ == '__main__':
    set_all_statuses()
