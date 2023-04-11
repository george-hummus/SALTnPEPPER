import time
import pickle
import os
import suds
from suds.client import Client
from lxml import etree


class LTObs():
    """
    LT Observation Class to create and send Observation Groups to the Liverpool telescope
    Using and RTML Payload over a SOAP connection
    """

    def __init__(self, settings):
        """
        Loads Settings and checks for any missing
        information within the settings dict
        """
        self.settings = settings
        self.pickle = settings['PKLFILE'] + '.pkl'
        for k, v in self.settings.items():
            if v == '':
                print('Please enter your: ' + k)
                exit()

    def _build_prolog(self):
        """
        Creates the RTML etree and set the headers
        Returns the Top level etree element for addition by other functions
        """
        LT_XML_NS = 'http://www.rtml.org/v3.1a'
        LT_XSI_NS = 'http://www.w3.org/2001/XMLSchema-instance'
        LT_SCHEMA_LOCATION = 'http://www.rtml.org/v3.1a http://telescope.livjm.ac.uk/rtml/RTML-nightly.xsd'

        namespaces = {
            'xsi': LT_XSI_NS,
        }
        schemaLocation = etree.QName(LT_XSI_NS, 'schemaLocation')
        return etree.Element('RTML',
                             {schemaLocation: LT_SCHEMA_LOCATION},
                             xmlns=LT_XML_NS,
                             mode='request',
                             uid=self.settings['prefix'] + '_' + format(str(int(time.time()))),
                             version='3.1a',
                             nsmap=namespaces)

    def _build_project(self, payload):
        """
        Adds the details of user, proposal to the payload
        """
        project = etree.Element('Project', ProjectID=self.settings['proposal'])
        contact = etree.SubElement(project, 'Contact')
        etree.SubElement(contact, 'Username').text = self.settings['username']
        etree.SubElement(contact, 'Name').text = ''
        payload.append(project)

    def _build_inst_schedule_IOI(self, observation, payload):
        """
        Builds the schedule with the target and constraints attached to be sent to
        the LT for use of the IO:I instrument
        """
        target = observation['target']
        constraints = observation['constraints']
        schedule = etree.Element('Schedule')
        device = etree.SubElement(schedule, 'Device', name="IO:I", type="camera")
        etree.SubElement(device, 'SpectralRegion').text = 'infrared'
        setup = etree.SubElement(device, 'Setup')
        etree.SubElement(setup, 'Filter', type='H')
        detector = etree.SubElement(setup, 'Detector')
        binning = etree.SubElement(detector, 'Binning')
        etree.SubElement(binning, 'X', units='pixels').text = '1'
        etree.SubElement(binning, 'Y', units='pixels').text = '1'
        exposure = etree.SubElement(schedule, 'Exposure', count=observation['exp_count'])
        etree.SubElement(exposure, 'Value', units='seconds').text = observation['exp_time']
        schedule.append(self._build_target(target))
        for const in self._build_constraints(constraints):
            schedule.append(const)
        payload.append(schedule)

    def _build_inst_schedule_Sprat(self, observation, payload):
        """
        Builds the schedule with the target and constraints attached to be sent to
        the LT for use of the Sprat instrument
        """
        target = observation['target']
        constraints = observation['constraints']
        if observation['grating'] == 'red' or observation['grating'] == 'blue':
            pass
        else:
            print('Enter either "red" or "blue" in grating')
            exit()
        schedule = etree.Element('Schedule')
        device = etree.SubElement(schedule, 'Device', name="Sprat", type="spectrograph")
        etree.SubElement(device, 'SpectralRegion').text = 'optical'
        setup = etree.SubElement(device, 'Setup')
        etree.SubElement(setup, 'Grating', name=observation['grating'])
        detector = etree.SubElement(setup, 'Detector')
        binning = etree.SubElement(detector, 'Binning')
        etree.SubElement(binning, 'X', units='pixels').text = '1'
        etree.SubElement(binning, 'Y', units='pixels').text = '1'
        exposure = etree.SubElement(schedule, 'Exposure', count=observation['exp_count'])
        etree.SubElement(exposure, 'Value', units='seconds').text = observation['exp_time']
        schedule.append(self._build_target(target))
        for const in self._build_constraints(constraints):
            schedule.append(const)
        payload.append(schedule)

    def _build_inst_schedule_IOO(self, observation, payload):
        """
        Builds the schedule with the target and constraints attached to be sent to
        the LT for use of the multi-filter IO:O instrument
        """
        self.filters = ['U',
                        'R',
                        'G',
                        'I',
                        'Z',
                        'B',
                        'V',
                        'Halpha6566',
                        'Halpha6634',
                        'Halpha6705',
                        'Halpha6755',
                        'Halpha6822']
        target = observation['target']
        constraints = observation['constraints']
        for filter in observation['filters']:
            if filter in self.filters:
                schedule = etree.Element('Schedule')
                device = etree.SubElement(schedule, 'Device', name=observation['instrument'], type='camera')
                etree.SubElement(device, 'SpectralRegion').text = 'optical'
                setup = etree.SubElement(device, 'Setup')
                etree.SubElement(setup, 'Filter', type=str(filter))
                detector = etree.SubElement(setup, 'Detector')
                binning = etree.SubElement(detector, 'Binning')
                etree.SubElement(binning, 'X', units='pixels').text = observation['binning']
                etree.SubElement(binning, 'Y', units='pixels').text = observation['binning']
                exposure = etree.SubElement(schedule, 'Exposure', count=observation['filters'][filter]['exp_count'])
                etree.SubElement(exposure, 'Value', units='seconds'). text = observation['filters'][filter]['exp_time']
                schedule.append(self._build_target(target))
                for const in self._build_constraints(constraints):
                    schedule.append(const)
                payload.append(schedule)
            else:
                print('selected filter/s not available for IO:O.')
                print('Please select a filter from the provided list.')
                print(self.filters)
                exit()

    def _build_inst_schedule_Moptop(self, observation, payload):
        """
        Builds the schedule with the target and constraints attached to be sent to
        the LT for use of the multi-filter IO:O instrument
        """
        self.filters = ['B',
                        'V',
                        'R',
                        'I',
                        'L']
        target = observation['target']
        constraints = observation['constraints']
        for filter in observation['filters']:
            if filter in self.filters:
                schedule = etree.Element('Schedule')
                device = etree.SubElement(schedule, 'Device', name=observation['instrument'], type='polarimeter')
                etree.SubElement(device, 'SpectralRegion').text = 'optical'
                setup = etree.SubElement(device, 'Setup')
                etree.SubElement(setup, 'Filter', type=str(filter))
                etree.SubElement(setup, 'Device', rotorSpeed=observation['filters'][filter]['rot_speed'], type='half-wave_plate')
                exposure = etree.SubElement(schedule, 'Exposure', count='1')
                etree.SubElement(exposure, 'Value', units='seconds'). text = observation['filters'][filter]['exp_time']
                schedule.append(self._build_target(target))
                for const in self._build_constraints(constraints):
                    schedule.append(const)
                payload.append(schedule)
            else:
                print('selected filter/s not available for IO:O.')
                print('Please select a filter from the provided list.')
                print(self.filters)
                exit()

    def _build_inst_schedule_Frodo(self, observation, payload):
        """
        Builds the schedule with the target and constraints attached to be sent to
        the LT for use of both blue and red arms of the Frodo instrument
        """
        target = observation['target']
        constraints = observation['constraints']
        colours = ('Blue', 'Red')
        for colour in colours:  # builds schedule for each colour arm of Frodo
            res = observation['res_{}'.format(colour)]
            time = observation['exp_time_{}'.format(colour)]
            count = observation['exp_count_{}'.format(colour)]

            schedule = etree.Element('Schedule')
            device = etree.SubElement(schedule, 'Device', name="FrodoSpec-{}".format(colour), type="spectrograph")
            etree.SubElement(device, 'SpectralRegion').text = 'optical'
            setup = etree.SubElement(device, 'Setup')
            etree.SubElement(setup, 'Grating', name=res)
            exposure = etree.SubElement(schedule, 'Exposure', count=count)
            etree.SubElement(exposure, 'Value', units='seconds').text = time
            schedule.append(self._build_target(target))
            for const in self._build_constraints(constraints):
                schedule.append(const)
            payload.append(schedule)

    def _build_target(self, target):
        """
        This provides the target info to the RTML file
        """

        self.target = etree.Element('Target', name=target['name'])
        coordinates = etree.SubElement(self.target, 'Coordinates')

        ra_hour, ra_min, ra_sec = target['RA'].split(":")
        dec_deg, dec_min, dec_sec = target['DEC'].split(":")

        ra = etree.SubElement(coordinates, 'RightAscension')
        etree.SubElement(ra, 'Hours').text = ra_hour
        etree.SubElement(ra, 'Minutes').text = ra_min
        etree.SubElement(ra, 'Seconds').text = ra_sec

        dec = etree.SubElement(coordinates, 'Declination')
        etree.SubElement(dec, 'Degrees').text = dec_deg
        etree.SubElement(dec, 'Arcminutes').text = dec_min
        etree.SubElement(dec, 'Arcseconds').text = dec_sec
        etree.SubElement(coordinates, 'Equinox').text = 'None'
        return self.target

    def _build_constraints(self, constraints):
        """
        This adds the constrainsts of the observation to the Schedule
        """
        if constraints['photometric'] == 'yes':
            photometric = 'clear'
        elif constraints['photometric'] == 'no':
            photometric = 'light'
        else:
            print('Please chose yes or no for photometric')
            exit()
        const = etree.Element('Constraints')
        airmass_const = etree.SubElement(const, 'AirmassConstraint', maximum=str(constraints['air_mass']))

        sky_const = etree.SubElement(const, 'SkyConstraint')
        etree.SubElement(sky_const, 'Flux').text = str(constraints['sky_bright'])
        etree.SubElement(sky_const, 'Units').text = 'magnitudes/square-arcsecond'

        seeing_const = etree.SubElement(const, 'SeeingConstraint',
                                        maximum=(str(constraints['seeing'])),
                                        units='arcseconds')

        photom_const = etree.SubElement(const, 'ExtinctionConstraint')
        etree.SubElement(photom_const, 'Clouds').text = photometric

        date_const = etree.SubElement(const, 'DateTimeConstraint', type='include')
        start = constraints['start_date'] + 'T' + constraints['start_time'] + '+00:00'
        end = constraints['end_date'] + 'T' + constraints['end_time'] + '+00:00'
        etree.SubElement(date_const, 'DateTimeStart', system='UT', value=start)
        etree.SubElement(date_const, 'DateTimeEnd', system='UT', value=end)
        return [airmass_const, sky_const, seeing_const, photom_const, date_const]

    def submit_group(self, observations, constraints):
        """
        send the payload to the telescope and informs the user if it fails or is successful
        """

        for k, v in constraints.items():
            if v == '':
                return ['fail', 'No value for ' + k]

        payload = self._build_prolog()
        self._build_project(payload)

        for observation in observations:
            observation['constraints'] = constraints
            if observation['instrument'] == 'IO:O':
                self._build_inst_schedule_IOO(observation, payload)
            elif observation['instrument'] == 'IO:I':
                self._build_inst_schedule_IOI(observation, payload)
            elif observation['instrument'] == 'Sprat':
                self._build_inst_schedule_Sprat(observation, payload)
            elif observation['instrument'] == 'Frodo':
                self._build_inst_schedule_Frodo(observation, payload)
            elif observation['instrument'] =='Moptop':
                self._build_inst_schedule_Moptop(observation, payload)
            else:
                return ['fail', 'Instrument ' + observation['instrument'] + ' not supported']

        full_payload = etree.tostring(payload, encoding="unicode", pretty_print=True)
        headers = {
            'Username': self.settings['username'],
            'Password': self.settings['rtmlpass']
        }
        url = '{0}://{1}:{2}/node_agent2/node_agent?wsdl'.format('http', self.settings['LT_HOST'], self.settings['LT_PORT'])
        client = Client(url=url, headers=headers)
        try:
            # Send payload, and receive response string, removing the encoding tag which causes issue with lxml parsing
            response = client.service.handle_rtml(full_payload).replace('encoding="ISO-8859-1"', '')
        except suds.WebFault:
            return ['fail', 'Error with connection to telescope']

        response_rtml = etree.fromstring(response)
        mode = response_rtml.get('mode')
        uid = response_rtml.get('uid')
        if self.settings['DEBUG'] is True:
            f = open(uid + '.RTML', "w")
            f.write(full_payload)
            f.write(response)
            f.close()
        if mode == 'reject':
            return ['fail', 'This submission has been rejected']
        elif mode == 'confirm':
            if os.path.exists(self.pickle):
                with open(self.pickle, "rb") as rp:
                    uids = pickle.load(rp)
            else:
                uids = []
            uids.append(uid)
            with open(self.pickle, "wb") as wp:
                pickle.dump(uids, wp)
        return (uid, '')

    def get_uids(self):
        """
        Returns a tuple of uids submitted to the telescope
        """
        with open(self.pickle, "rb") as uids:
            uids = pickle.load(uids)
            return uids

    def cancel_group(self, uid):
        """
        Deletes observation with known uid from the telescope.
        """
        LT_XSI_NS = 'http://www.w3.org/2001/XMLSchema-instance'
        LT_SCHEMA_LOCATION = 'http://www.rtml.org/v3.1a http://telescope.livjm.ac.uk/rtml/RTML-nightly.xsd'

        namespaces = {
            'xsi': LT_XSI_NS,
        }
        schemaLocation = etree.QName(LT_XSI_NS, 'schemaLocation')
        cancel_payload = etree.Element('RTML',
                                       {schemaLocation: LT_SCHEMA_LOCATION},
                                       mode='abort',
                                       uid=uid,
                                       version='3.1a',
                                       nsmap=namespaces
                                       )
        project = etree.SubElement(cancel_payload, 'Project', ProjectID=self.settings['proposal'])
        contact = etree.SubElement(project, 'Contact')
        etree.SubElement(contact, 'Username').text = self.settings['username']
        etree.SubElement(contact, 'Name').text = ''
        etree.SubElement(contact, 'Communication')
        cancel = etree.tostring(cancel_payload, encoding='unicode', pretty_print=True)

        headers = {
            'Username': self.settings['username'],
            'Password': self.settings['rtmlpass']
        }
        url = '{0}://{1}:{2}/node_agent2/node_agent?wsdl'.format('http',
                                                                 self.settings['LT_HOST'], self.settings['LT_PORT'])

        client = Client(url=url, headers=headers)
        # Send cancel_payload, and receive response string, removing the encoding tag which causes issue with lxml parsing
        try:
            response = client.service.handle_rtml(cancel).replace('encoding="ISO-8859-1"', '')
        except suds.WebFault:
            return ['Error with connection to telescope']
        response_rtml = etree.fromstring(response)
        mode = response_rtml.get('mode')
        uid = response_rtml.get('uid')
        if self.settings['DEBUG']:
            f = open(uid + '_cancel.RTML', "w")
            f.write(cancel)
            f.write(response)
            f.close()
        if mode == 'reject':
            return ['Cancel Failed for ' + uid]
        elif mode == 'confirm':
            with open(self.pickle, "rb") as rp:
                all_uids = pickle.load(rp)
            if uid in all_uids:
                all_uids.remove(uid)
                with open(self.pickle, "wb") as cancelled:
                    pickle.dump(all_uids, cancelled)
            return []
