__author__ = 'isha'

import json
import dateutil.parser
import datetime
import pytz
import re
import os
import pandas as pd

class EnronEmailParser:
    '''
    Parser for the emails included in the Enron Email Dataset available at
    http://bailando.sims.berkeley.edu/enron/enron_with_categories.tar.gz
    '''
    EMAIL_REGEX = re.compile(r"^[^@]+@[^@]+\.[^@]+$")
    EPOCH = datetime.datetime.utcfromtimestamp(0).replace(tzinfo = pytz.utc)

    def __init__(self, filename, verbose=False):
        self.filename = filename
        self.ts = None
        self.dt = None
        self.sender = None
        self.recipients = None
        self.subject = None
        self.num_recipients = None
        self.num_lines_in_msg = None
        self.json_repr = None
        self.parse()
        if verbose:
            print self.__str__()

    def to_json(self):
        if not self.json_repr:
            self.json_repr = {
                'filename' : self.filename,
                'ts': self.ts,
                'sender': self.sender,
                'recipients': list(self.recipients),
                'subject': self.subject,
                'num_lines_in_msg': self.num_lines_in_msg
            }
        return self.json_repr

    def __str__(self):
        return json.dumps(self.to_json())

    def check_prefix(self, line, prefix):
        '''
        Make sure the line starts with the given prefix and strip the prefix and return the rest
        '''
        if not line.startswith(prefix):
            raise ValueError('Line invalid in {}, needs prefix "{}": {}'.format(self.filename, prefix, line))
        return line[len(prefix)+1:].strip()

    def parse_recipients(self, filehandle, prefix, line=None):
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
                    self.recipients.add(recipient.strip())
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

            # Read sender
            self.sender = self.check_prefix(f.readline().strip(), "From:")
            if not self.EMAIL_REGEX.match(self.sender):
                raise ValueError('Invalid sender address found: {}'.format(self.sender))

            # Assume all recipients in the to:, cc:, bcc: lists are equivalent.
            self.recipients = set()

            # To addresses, if any
            unprocessed_line = self.parse_recipients(f, "To:")

            # Subject
            subjectline = unprocessed_line if unprocessed_line else f.readline().strip()
            self.subject = self.check_prefix(subjectline, "Subject:")

            # Handle case for mulitiline subject
            line = f.readline().strip()
            while not line.startswith('Cc:') and not line.startswith('Mime-Version'):
                self.subject = self.subject + line
                line = f.readline().strip()

            # Cc addreses, if any
            unprocessed_line = self.parse_recipients(f, "Cc:", line)

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
            unprocessed_line = self.parse_recipients(f, "Bcc:")

            # Total number of recipients
            self.num_recipients = len(self.recipients)

            # Read till the header is done, no need to do verification of X- fields at this point
            line = unprocessed_line if unprocessed_line else f.readline().strip()
            while line:
                line = f.readline().strip()

            # All that is left is the message body
            self.num_lines_in_msg = 0
            for _ in f:
                self.num_lines_in_msg += 1

            # Not saving it for the time being
            #message = '\n'.join([line.strip() for line in f])


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
        self.survey()
        self.parse()

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
            emails[parsed_email.filename]=(parsed_email.ts,
                                           parsed_email.dt,
                                           parsed_email.sender,
                                           parsed_email.num_recipients,
                                           parsed_email.subject,
                                           parsed_email.num_lines_in_msg)
            for recipient in parsed_email.recipients:
                recipients.append((parsed_email.filename, recipient))
        self.emails = pd.DataFrame.from_dict(emails, orient='index')
        self.emails.index.name = 'email_id'
        self.emails.columns = ['ts', 'datetime', 'sender', 'num_recipients', 'subject', 'num_lines_in_msg']
        self.recipients = pd.DataFrame.from_records(recipients)
        self.recipients.columns = ['email_id', 'recipient']
        print 'Parsed {} emails'.format(len(emails))