__author__ = 'isha'

import json
import dateutil.parser
import datetime
import pytz
import re
import os
import pandas as pd
from sklearn.feature_extraction.text import TfidfTransformer

class EnronEmailParser:
    '''
    Parser for the emails included in the Enron E    mail Dataset available at
    http://bailando.sims.berkeley.edu/enron/enron_with_categories.tar.gz
    '''
    EMAIL_REGEX = re.compile(r"^[^@]+@[^@]+\.[^@]+$")
    EPOCH = datetime.datetime.utcfromtimestamp(0).replace(tzinfo=pytz.utc)

    def __init__(self, filename, verbose=False):
        self.filename = filename
        self.dt = None
        self.ts = None
        self.tz = None
        self.sender = None
        self.subject = None
        self.tos = None
        self.ccs = None
        self.bccs = None
        self.num_tos = None
        self.num_ccs = None
        self.num_bccs = None
        self.num_recipients = None
        self.num_lines_in_msg = None
        self.str_repr = None
        self.parse()
        if verbose:
            print self.__str__()

    def __str__(self):
        if not self.str_repr:
            self.str_repr = json.dumps({
                'filename': self.filename,
                'ts': self.ts,
                'sender': self.sender,
                'tos': list(self.tos),
                'ccs': list(self.ccs),
                'bccs': list(self.bccs),
                'subject': self.subject,
                'num_lines_in_msg': self.num_lines_in_msg
            })
        return self.str_repr

    def check_prefix(self, line, prefix):
        '''
        Make sure the line starts with the given prefix and strip the prefix and return the rest
        '''
        if not line.startswith(prefix):
            raise ValueError('Line invalid in {}, needs prefix "{}": {}'.format(self.filename, prefix, line))
        return line[len(prefix)+1:].strip()

    def parse_recipients(self, filehandle, prefix, recipient_set, line=None):
        '''
        Parse the recipient email addresses (To: Cc: and Bcc:)

        Including cases in which the data spans multiple lines
        '''
        if not line:
            line = filehandle.readline().strip()
        if not line.startswith(prefix):
            return line
        line = self.check_prefix(line, prefix)
        while (line):
            for recipient in [address.strip() for address in line.split(',') if address]:
                if not self.EMAIL_REGEX.match(recipient):
                    raise ValueError('Invalid recipient address {} found in: "{}"'.format(recipient, line))
                recipient = recipient.strip()
                if recipient != self.sender:
                    recipient_set.add(recipient.strip())
            line = filehandle.readline().strip() if line.endswith(',') else None
        return None

    def parse(self):
        '''
        Parse the file a line at a time according to expected format.
        '''
        with open(self.filename, 'r') as f:
            # Ignore Message-ID
            line = f.readline()
            self.check_prefix(line, 'Message-ID')

            # Read date and time
            self.dt = dateutil.parser.parse(self.check_prefix(f.readline().strip(), "Date:"))
            self.ts = (self.dt - self.EPOCH).total_seconds()
            self.tz = self.dt.tzinfo

            # Read sender
            self.sender = self.check_prefix(f.readline().strip(), "From:")
            if not self.EMAIL_REGEX.match(self.sender):
                raise ValueError('Invalid sender address found: {}'.format(self.sender))

            # To addresses, if any
            self.tos = set()
            unprocessed_line = self.parse_recipients(f, "To:", self.tos)

            # Subject, also handle case for multi-line subject
            subjectline = unprocessed_line if unprocessed_line else f.readline().strip()
            self.subject = self.check_prefix(subjectline, "Subject:")
            line = f.readline().strip()
            while not line.startswith('Cc:') and not line.startswith('Mime-Version'):
                self.subject = self.subject + line
                line = f.readline().strip()

            # Cc addreses, if any
            self.ccs = set()
            unprocessed_line = self.parse_recipients(f, "Cc:", self.ccs, line)

            # Mime version - ignore
            line = unprocessed_line if unprocessed_line else f.readline()
            self.check_prefix(line, 'Mime-Version')

            # Content type - ignore
            line = f.readline()
            self.check_prefix(line, 'Content-Type')

            # Content-Transfer-Encoding - ignore
            line = f.readline()
            self.check_prefix(line, 'Content-Transfer-Encoding')

            # Bcc addresses, if any
            self.bccs = set()
            unprocessed_line = self.parse_recipients(f, "Bcc:", self.bccs)

            # Total number of recipients
            self.ccs = self.ccs - self.tos
            self.bccs = self.bccs - self.ccs - self.tos
            self.num_tos = len(self.tos)
            self.num_ccs = len(self.ccs)
            self.num_bccs = len(self.bccs)
            self.num_recipients = self.num_tos + self.num_ccs + self.num_bccs

            # Read till the header is done, no need to do verification of X- fields at this point
            line = unprocessed_line if unprocessed_line else f.readline().strip()
            while line:
                line = f.readline().strip()

            # All that is left is the message body
            self.num_lines_in_msg = 0
            for _ in f:
                self.num_lines_in_msg += 1



class EnronEmailDataset:
    '''
    Data handler for the Enron Email Dataset

    Relies on the EnronEmailParser class to do the actual email parsing.
    Uses pandas dataframes as the data storage objects.
    '''

    def __init__(self, data_dir):
        if not data_dir or not os.path.isdir(data_dir):
            raise ValueError(data_dir + " needs to be a valid directory")
        self.data_dir = data_dir
        self.email_files = []
        self.emails = None
        self.recipients = None
        self.corpus = []
        self.survey()
        self.parse()
        self.find_responses()

    def survey(self):
        '''
        Walk through the data directory making a note of all the email files
        '''
        if self.email_files:
            return
        for subdir in os.walk(self.data_dir).next()[1]:
            subdir = os.path.join(self.data_dir, subdir)
            for email_file in os.walk(subdir).next()[2]:
                if email_file.endswith('.txt'):
                    self.email_files.append(os.path.join(subdir, email_file))
        print 'Surveyed {} email files'.format(self.email_files.__len__())

    def parse(self):
        '''
        Parse all the emails surveyed and store the resulting data fiels in the pandas dataframes
        '''
        if self.emails:
            return
        emails = {}
        recipients = []
        for email_file in self.email_files:
            parsed_email = EnronEmailParser(email_file)
            emails[parsed_email.filename]=(
                parsed_email.filename,
                parsed_email.dt,
                parsed_email.ts,
                parsed_email.tz,
                parsed_email.sender,
                parsed_email.num_tos,
                parsed_email.num_ccs,
                parsed_email.num_bccs,
                parsed_email.num_recipients,
                parsed_email.subject,
                parsed_email.num_lines_in_msg
            )
            for recipient in parsed_email.tos:
                recipients.append((parsed_email.filename, recipient, 'to'))
            for recipient in parsed_email.ccs:
                recipients.append((parsed_email.filename, recipient, 'cc'))
            for recipient in parsed_email.bccs:
                recipients.append((parsed_email.filename, recipient, 'bcc'))
        self.emails = pd.DataFrame.from_dict(emails, orient='index')
        self.emails.index.name = 'email_id'
        self.emails.columns = ['email_id', 'datetime', 'ts', 'tz', 'sender', 'num_tos', 'num_ccs', 'num_bccs', 'num_recipients', 'subject', 'num_lines_in_msg']
        self.recipients = pd.DataFrame.from_records(recipients)
        self.recipients.columns = ['email_id', 'recipient', 'type']
        print 'Parsed {} emails'.format(len(emails))

    def find_responses(self):
        # Nested joins to find all emails to which an email can be a potential response
        intermediate = pd.merge(
            self.emails,
            self.recipients,
            left_on='sender',
            right_on='recipient',
            suffixes=['_response', '_original']
        )
        intermediate = intermediate.rename(columns={'type':'recipient_type_in_original_message'})
        del intermediate['recipient']

        self.responses = pd.merge(
            intermediate,
            self.emails,
            left_on='email_id_original',
            right_index=True,
            suffixes=['_response', '']
        )
        del self.responses['email_id_original']

        # Apply conditions
        self.responses['lowercase_subject'] = self.responses.subject.apply(lambda value: value.lower())
        self.responses['response_time_in_secs'] = self.responses['ts_response'] - self.responses['ts']
        self.responses = self.responses[
            (self.responses.lowercase_subject != '')
            & (self.responses.lowercase_subject != 're:')
            & (self.responses.lowercase_subject != 'fwd:')
            & (self.responses.response_time_in_secs > 0)]
        self.responses = self.responses[self.responses.apply(lambda row: row['subject'] in row['subject_response'], axis=1)]
        del self.responses['lowercase_subject']

        # Pick the shortest response time for each email
        self.responses = self.responses.sort_values(by=['response_time_in_secs'], ascending=[1])
        self.responses = self.responses.groupby(['email_id_response'], as_index=False).first().sort_values(by='response_time_in_secs', ascending=[1])
        print "Found {} responses".format(len(self.responses))
