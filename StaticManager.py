'''
=============================
Title: Configuration File Management - EDS Field Control
Author: Benjamin Considine, Brian Mahabir, Aditya Wikara
Started: September 2018
=============================
'''

'''
Config file parameters list (ADD NEW PARAMETERS AS DICTIONARY ENTRIES)
'''

DEFAULT_CONFIG_PARAM = {
    # EDS default testing
    'SCHEDS1': [[1, -3], [1, -2], [1, -1]],
    'SCHEDS2': [[1, -3], [1, -2]],
    'SCHEDS3': [[1, -2]],
    'SCHEDS4': [[2, -2]],
    'SCHEDS5': [[3, -2]],
    'SCHEDS6': [[1, 0]],
    'EDS1': 4,
    'EDS2': 17,
    'EDS3': 6,
    'EDS4': 19,
    'EDS5': 26,
    'EDS6': 27,
    'EDS1PV': 7,
    'EDS2PV': 8,
    'EDS3PV': 12,
    'EDS4PV': 16,
    'EDS5PV': 20,
    'EDS6PV': 21,
    'EDSIDS': [1, 2, 3, 4, 5],
    'CTRL1PV': 15,
    'CTRL2PV': 23,
    'CTRLIDS': [1, 2],
    
    # testing requirements
    'maxTemperatureCelsius': 40,
    'minTemperatureCelsius': 10,
    'maxRelativeHumidity': 60,
    'minRelativeHumidity': 20, # should be 30
    'testDurationSeconds': 30, # should be 1-2 min?
    'testWindowSeconds': 2700,
    
    # indicators/switches
    'outPinLEDGreen': 5,
    'outPinLEDRed': 13,
    'inPinManualActivate': 22,
    'manualEDSNumber': 5, #EDS 3
    'ADC': 25,
    'solarChargerEDSNumber': 6,
    # location data
    'degLongitude': -71.05,
    'offsetGMT': -5,
    }

'''
Static master class
Functionality:
1) Contains and maintains static global values that will remain UNCHANGED
2) Contains default configuration file values for reference
'''

class StaticMaster:
    
    def __init__(self):
        # immutable constants are not put in the dictionary
        self.config_dictionary = DEFAULT_CONFIG_PARAM

    def get_config(self):
        # returns config dictionary for other functions to use
        return self.config_dictionary
