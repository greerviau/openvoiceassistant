from __future__ import print_function
import datetime
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
import pytz
import datetime

class GoogleController(object):

    def __init__(self):
        # If modifying these scopes, delete the file token.json.
        self.SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']


    def authenticate_google_calendar(self):
        """Shows basic usage of the Google Calendar API.
        Prints the start and name of the next 10 events on the user's calendar.
        """
        creds = None
        # The file token.json stores the user's access and refresh tokens, and is
        # created automatically when the authorization flow completes for the first
        # time.
        if os.path.exists('token.json'):
            creds = Credentials.from_authorized_user_file('token.json', self.SCOPES)
        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    'credentials.json', self.SCOPES)
                creds = flow.run_local_server(port=0)
            # Save the credentials for the next run
            with open('token.json', 'w') as token:
                token.write(creds.to_json())

        self.calendar_service = build('calendar', 'v3', credentials=creds)

    def get_events(self, day):
        date = datetime.datetime.combine(day, datetime.datetime.min.time())
        end = datetime.datetime.combine(day, datetime.datetime.max.time())
        utc = pytz.UTC
        date = date.astimezone(utc)
        end = end.astimezone(utc)
        events_result = self.calendar_service.events().list(calendarId='primary', timeMin=date.isoformat(), timeMax=end.isoformat(),
                                            singleEvents=True,
                                            orderBy='startTime').execute()
        events = events_result.get('items', [])

        return events

    