import datetime
from google_util import GoogleController
from utils import parse_date, parse_time, extract_keywords, DAYS

class PlanningController(object):
    def __init__(self, address):
        self.ADDRESS = address
        self.googleControl = GoogleController()
        self.googleControl.authenticate_google_calendar()

    def check_calendar(self, text):
        date, date_str = parse_date(text)
        if date is None:
            return f'I didnt catch the date {self.ADDRESS}'
        #print(date, date_str)
        events = self.googleControl.get_events(date)
        #print(events)
        if not events:
            return f'You have nothing planned for {date_str}'
        
        if 'how many' in text:
            ext = 's' if len(events) > 1 else ''
            return f'You have {len(events)} event{ext} planned for {date_str}'

        response = date_str
        for i, event in enumerate(events):
            if i == 0:
                response += ' you have '
            elif i > 0 and i < len(events)-1:
                response += ', followed by '
            else:
                response += ', and finally you have '
            
            event_time = ''
            start = datetime.datetime.strptime(event['start']['dateTime'][:-7],'%Y-%m-%dT%H:%M:%S').strftime('%I:%M %p')  if 'dateTime' in event['start'] else ''
            end = datetime.datetime.strptime(event['end']['dateTime'][:-7], '%Y-%m-%dT%H:%M:%S').strftime('%I:%M %p') if 'dateTime' in event['end'] else ''
            if not start and not end:
                event_time = 'all day'
            elif not start:
                event_time = f'from the start of the day until {end}'
            elif not end:
                event_time = f'from {start} until the end of the day'
            else:
                event_time = f'from {start} to {end}'

            event_summary = event['summary'].lower()
            response += f'{event_summary} {event_time}'
        return response

    def set_reminder(self, text):
        #todo

        subject = ''
        date = None
        date_string = ''
        times = []
        keywords = extract_keywords(text)
        print(keywords)
        for keyword in list(keywords):
            ext_date, date_str = parse_date(keyword)
            if ext_date:
                date = ext_date
                date_string = date_str
                keywords.remove(keyword)
                break
            
        for keyword in list(keywords):
            time_packet = parse_time(keyword)
            if time_packet[1]:
                times.append(time_packet)
                keywords.remove(keyword)
        
        print(date, date_string, times)
        print(keywords)
        subject = keywords[0]
        print(subject)

        r_type = ''
        subject_string = ' '

        if 'remind' in text:
            r_type = 'a reminder'
            subject_string = f' that you have {subject} '
        elif 'alarm' in text or 'wake' in text:
            r_type = 'an alarm'

        final_date_string = f'on {date_string}'
        for day in DAYS:
            if day in date_string:
                final_date_string = f'{date_string}'
        if 'today' in date_string or 'tomorrow' in date_string:
            final_date_string = f'{date_string}'
        
        times = sorted(times, key = lambda x: x[0]) 
        if len(times) == 0:
            return f'I didnt catch the time that you wanted me to set {r_type} for'
        elif len(times) == 1:
            if date:
                return f'Setting {r_type}{subject_string}{final_date_string} at {times[0][2]}'
            else:
                return f'Setting {r_type}{subject_string}at {times[0][2]}'
        else:
            r_type = 'a reminder'
            subject_string = f' that you have {subject} '
            if date:
                return f'Setting {r_type}{subject_string}{final_date_string} from {times[0][2]} to {times[1][2]}'
            else:
                return f'Setting {r_type}{subject_string}from {times[0][2]} to {times[1][2]}'
        
        return f'I didnt understand that {self.ADDRESS}'