'''
This is central control.
This file contains the main looping structure for extended-period field testing.
'''

import RPi.GPIO as GPIO
import subprocess
import time
import busio
from board import *
import adafruit_pcf8523
import AM2315

import StaticManager as SM
import DataManager as DM
import RebootManager as RM
import TestingManager as TM

from math import floor, ceil

# process delay (delay loop by X seconds to slow necessary computing)
PROCESS_DELAY = 1

# manual time test limit
MANUAL_TIME_LIMIT = 300
WINDOW_CHECK_INTERVAL = 5

# peripheral i2c bus addresses
RTC_ADD = 0x68

# read config, get constants, etc
print("Initializing...")
static_master = SM.StaticMaster()
usb_master = DM.USBMaster()
test_master = TM.TestingMaster(static_master.get_config())
csv_master = DM.CSVMaster(usb_master.get_USB_path())

# channel setup


# RTC setup
i2c_bus = busio.I2C(SCL, SDA)
rtc = adafruit_pcf8523.PCF8523(i2c_bus)


# set time to current if needed
# time struct: (year, month, month_day, hour, min, sec, week_day, year_day, is_daylightsaving?)
# run this once with the line below uncommented
# rtc.datetime = time.struct_time((2019,3,14,16,11,0,3,73,1))

# weather sensor setup
weather = AM2315.AM2315()

# set up log file
log_master = DM.LogMaster(usb_master.get_USB_path(), rtc.datetime)


# time display functions
def print_time(dt):
    print(str(dt.tm_mon) + '/' + str(dt.tm_mday) + '/' + str(dt.tm_year) + ' ' + str(dt.tm_hour) + ':' + str(dt.tm_min) + ':' + str(dt.tm_sec), end='')

def print_l(dt, phrase):
    print_time(dt)
    print(" " + phrase)
    log_master.write_log(dt, phrase)


# id variables for test coordination
# FIX THIS, MUST FIX CONFIG FILE STUFF (YAML or JSON FORMATS)
eds_ids = test_master.get_pin('EDSIDS')
ctrl_ids = test_master.get_pin('CTRLIDS')


# channel setups
GPIO.setmode(GPIO.BCM)


GPIO.setup(test_master.get_pin('outPinLEDGreen'), GPIO.OUT)
GPIO.setup(test_master.get_pin('outPinLEDRed'), GPIO.OUT)
GPIO.setup(test_master.get_pin('inPinManualActivate'), GPIO.IN)
GPIO.setup(test_master.get_pin('POWER'), GPIO.OUT)

# for each EDS, CTRL id, set up GPIO channel
for eds in eds_ids:
    GPIO.setup(test_master.get_pin('EDS'+str(eds)), GPIO.OUT)
    GPIO.setup(test_master.get_pin('EDS'+str(eds)+'PV'), GPIO.OUT)

# var setup
error_cycle_count = 0
flip_on = True
temp_pass = False
humid_pass = False
schedule_pass = False

# location data for easy use in solar time calculation
gmt_offset = test_master.get_param('offsetGMT')
longitude = test_master.get_param('degLongitude')
latitude = 1 # latitude currently unused

# detect switch event to manually operate EDS
GPIO.add_event_detect(test_master.get_pin('inPinManualActivate'), GPIO.RISING)


'''
~~~CORE LOOP~~~
This loop governs the overall code for the long term remote testing of the field units
1) Checks the time of day
2) Checks the temperature and humidity before testing
3) Runs testing sequence
4) Writes data to log files
5) Alerts in the case of an error
'''


# loop indefinitely
flag = False
stopped = False

while not stopped:
    # set all flags to False
    temp_pass = False
    humid_pass = False
    schedule_pass = False
    weather_pass = False
    
    # switch power supply and EDS relays OFF (make sure this is always off unless testing)
    GPIO.cleanup(test_master.get_pin('POWER'))
    for eds in eds_ids:
        GPIO.cleanup(test_master.get_pin('EDS'+str(eds)))
        GPIO.cleanup(test_master.get_pin('EDS'+str(eds)+'PV'))

    
    # update time of day by getting data from RTC
    # 1) Check if RTC exists
    # 2) If yes, get time data
    print('------------------------------')
    #try:
    #current_time = rtc.datetimebusio.SPI(clock=board.SCK, MISO=board.MISO, MOSI=board.MOSI)
    current_time = rtc.datetime
    print_time(current_time)
    print()
    solar_offset = ceil(DM.get_solar_time(gmt_offset, current_time, longitude, latitude) * 100)/100
    print('Solar offset: ', solar_offset, ' minutes')
    
    csv_master.write_txt_testing_data(rtc.datetime, 1, 2, 3, 4, 5)
    csv_master.write_csv_testing_data(rtc.datetime, 1, 2, 3, 4, 5)
    csv_master.write_txt_noon_data(rtc.datetime, 1, 2, 3, 4, 5)
    csv_master.write_csv_noon_data(rtc.datetime, 1, 2, 3, 4, 5)
    log_master.write_log(rtc.datetime, "I think it's working, and I'm excited.")
    
    # flip indicator GREEN LED to show proper working
    if flip_on:
        GPIO.output(test_master.get_pin('outPinLEDGreen'), 1)
        flip_on = False
    else:
        GPIO.output(test_master.get_pin('outPinLEDGreen'), 0)
        flip_on = True

    # get weather and print values in consol
    w_read = weather.read_humidity_temperature()
    print("Temp: ", w_read[1], "C")
    print("Humid: ", w_read[0], "%")
    

    '''
    --------------------------------------------------------------------------
    BEGIN SOLAR NOON DATA ACQUISITION CODE
    The following code handles the automated data acquisition of SCC values for each EDS and CTRL at solar noon each day
    Code outline:
    1) Check if current time matches solar noon
    2) If yes, then for each EDS and CTRL in sequence, do the following:
        2a) Measure SCC from PV cell
        2b) Write data to CSV/text files
    3) Then activate EDS6 (the battery charger)
    '''
    
    # get current solar time
    curr_dt = rtc.datetime
    solar_time_min = curr_dt.tm_hour * 60 + curr_dt.tm_min + curr_dt.tm_sec / 60 + solar_offset
    
    # if within 30 seconds of solar noon, run measurements
    if abs(720 - solar_time_min) < 0.5:
        # EDS SCC measurements
        for eds in eds_ids:
            eds_scc = test_master.run_measure_EDS(eds)
            print_l(curr_dt, "Solar Noon SCC for EDS" + str(eds) + ": " + str(eds_scc))
            # write data to solar noon csv/txt
            csv_master.write_noon_data(curr_dt, w_read[1], w_read[2], eds, eds_scc, eds_scc)
        
        # CTRL SCC measurements
        for ctrl in ctrl_ids:
            ctrl_scc = test_master.run_measure_CTRL(ctrl)
            print_l(curr_dt, "Solar Noon SCC for CTRL" + str(ctrl) + ": " + str(ctrl_scc))
            # write data to solar noon csv/txt
            csv_master.write_noon_data(curr_dt, w_read[1], w_read[2], ctrl, ctrl_scc, ctrl_scc)
            
        # activate EDS6 for full testing cycle (no measurements taken)
            # turn on GREEN LED for duration of test
        GPIO.output(test_master.get_pin('outPinLEDGreen'), 1)
            # run test
        test_master.run_test(test_master.get_pin('solarChargerEDSNumber'))
            # turn off GREEN LED after test
        GPIO.output(test_master.get_pin('outPinLEDGreen'), 0)

    '''
    END SOLAR NOON DATA ACQUISITION CODE
    --------------------------------------------------------------------------
    '''
    
    
    '''
    --------------------------------------------------------------------------
    BEGIN AUTOMATIC TESTING ACTIVATION CODE
    The following code handles the automated activation of the each EDS as specified by their schedule in config.txt
    Code outline:
    For each EDS in sequence, do the following:
    1) Check if current time matches scheduled activation time for EDS
    2) If yes, check if current weather matches testing weather parameters, within activation window
    3) If yes, run complete testing procedure for that EDS
        3a) Measure [before] SCC for control PV cells
        3b) Measure [before] SCC for EDS PV being tested
        3c) Flip relays to activate EDS for test duration
        3d) Measure [after] SCC for EDS PV being tested
        3e) Measure [after] SCC for control PV cells
        3f) Write data to CSV/txt files
    '''
    
    
    # for each EDS check time against schedule, set time flag if yes
    # put EDS in a queue if multiple are to be activated simultaneously
    eds_testing_queue = []
    
    for eds_num in eds_ids:
        schedule_pass = test_master.check_time(rtc.datetime, solar_offset, eds_num)
        eds_testing_queue.append(eds_num)
    
    for eds in testing_queue:
        # if time check is good, check temp and weather within a set window
        window = 0
        if schedule_pass:
            weather_pass = temp_pass and humid_pass
            while window < test_master.get_param('testWindowSeconds') and not weather_pass:
                # check temp and humidity until they fall within parameter range or max window reached
                w_read = weather.read_humidity_temperature()
                
                temp_pass = test_master.check_temp(w_read[1])
                humid_pass = test_master.check_humid(w_read[0])
                weather_pass = temp_pass and humid_pass
                
                # increment window by 1 sec
                window += 1
                time.sleep(1)
                
                # flip GREEN LED because test not initiated yet
                if flip_on:
                    GPIO.output(test_master.get_pin('outPinLEDGreen'), 1)
                    flip_on = False
                else:
                    GPIO.output(test_master.get_pin('outPinLEDGreen'), 0)
                    flip_on = True
            
            # if out of loop and parameters are met
            if weather_pass:
                # run test if all flags passed
                print_l(rtc.datetime, "Checks passed. Initiating testing procedure for EDS" + str(eds))
                # run testing procedure
                
                curr_dt = rtc.datetime
                
                # 1) get control SCC 'before' values for each control
                for ctrl in ctrl_ids:
                    ctrl_before[ctrl] = test_master.run_measure_CTRL(ctrl)
                    print_l(rtc.datetime, "Pre-test SCC for CTRL" + str(ctrl) + ": " + str(ctrl_before[ctrl]))
                                
                # 2) get SCC 'before' value for EDS being tested
                eds_before = test_master.run_measure_EDS(eds)
                print_l(rtc.datetime, "Pre-test SCC for EDS" + str(eds) + ": " + str(eds_before))
                
                
                # 3) activate EDS for test duration
                
                    # turn on GREEN LED for duration of test
                GPIO.output(test_master.get_pin('outPinLEDGreen'), 1)
                    # run test
                test_master.run_test(eds)
                    # turn off GREEN LED after test
                GPIO.output(test_master.get_pin('outPinLEDGreen'), 0)
                
                # 4) get PV 'after' value for EDS being tested
                eds_after = test_master.run_measure_EDS(eds)
                print_l(rtc.datetime, "Post-test SCC for EDS" + str(eds) + ": " + str(eds_after))
                
                
                # 5) get control SCC 'after' values for each control
                for ctrl in ctrl_ids:
                    ctrl_after[ctrl] = test_master.run_measure_CTRL(ctrl)
                    print_l(rtc.datetime, "Post-test SCC for CTRL" + str(ctrl) + ": " + str(ctrl_after[ctrl]))
                    
                # finish up, write data to CSV and give feedback
                # write data for EDS tested
                csv_master.write_testing_data(curr_dt, w_read[1], w_read[0], eds, eds_before, eds_after)
                
                # write control data
                for ctrl in ctrl_ids:
                    # control pv numbers will show as negative in main data files to differentiate them
                    csv_master.write_testing_data(curr_dt, w_read[1], w_read[0], -1*ctrl, ctrl_before[ctrl], ctrl_after[ctrl])
                
    '''
    END AUTOMATIC TESTING ACTIVATION CODE
    --------------------------------------------------------------------------
    '''

    
    '''
    --------------------------------------------------------------------------
    BEGIN MANUAL ACTIVATION CODE
    The following code handles the manual activation of the specified EDS (in config.txt) by flipping the switch
    Code outline:
    1) Check for changing input on switch pin
    2) If input is changed, and input is high (activate), then begin test
    3) Check SCC on EDS for [before] measurement
    4) Run first half of test, but loop until switched off or max time elapsed
    5) Run second half of test
    6) Check SCC on EDS for [after] measurement
    '''
    
    if GPIO.event_detected(test_master.get_pin('inPinManualActivate')):
        # run EDS test on selected manual EDS
        
        if GPIO.input(test_master.get_pin('inPinManualActivate')):
            # flag for test duration
            man_flag = False
            
            eds_num = test_master.get_pin('manualEDSNumber')
            
            # solid GREEN for duration of manual test
            GPIO.output(test_master.get_pin('outPinLEDGreen'), 1)
            print_l(rtc.datetime, "FORCED. Running EDS" + str(eds_num) + " testing sequence. FLIP SWITCH OFF TO STOP.")
            try:
                # measure PV current before activation
                before_cur = test_master.run_measure_EDS()
                phrase = "EDS" + str(eds_num) + " PV [BEFORE] scC: " + str(before_cur) + " A"
                print_l(rtc.datetime, phrase)
                
        
                # run first half of test
                test_master.run_test_begin(eds_num)
                time_elapsed = 0
                
                # 3) wait for switch to be flipped OFF
                while not man_flag:
                    if GPIO.event_detected(test_master.get_pin('inPinManualActivate')):
                        man_flag = True
                        
                    time_elapsed += 0.1
                    if time_elapsed > MANUAL_TIME_LIMIT:
                        man_flag = True
                    
                    time.sleep(0.1)
                
                # then run second half of test (cleanup phase)
                test_master.run_test_end(eds_num)
                
                after_cur = test_master.run_measure()
                phrase = "EDS" + str(eds_num) + " PV [AFTER] scC: " + str(after_cur) + " A"
                print_l(phrase)
                
            except:
                print_l(rtc.datetime, "MAJOR ERROR. Cannot initiate EDS" + str(eds_num) + " manual testing sequence. Please check.")
        
        
            # either way, turn off GREEN LED indicator
            GPIO.output(test_master.get_pin('outPinLEDGreen'),0)
    
    '''
    END MANUAL ACTIVATION CODE
    --------------------------------------------------------------------------
    '''

    
    # delay to slow down processing
    time.sleep(PROCESS_DELAY)
    
    # END CORE LOOP
    


