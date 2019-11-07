import sys
sys.path.append('C:\Program Files (x86)\Keysight\SD1\Libraries\Python')
import keysightSD1
import pyhvi
import numpy as np
from datetime import timedelta
import atexit
from awg import AWG
from dig import DIG
from BaseDriver import Error

"""
HVI2 for triggering devices
set slotAWG, slotDIG to correct numbers for AWG setup
in current beta version of HVI, these need to be in the same segment
(i.e., not connected across a bus) or compilation will fail
"""

class TriggerLoop():
    '''
    singleton class for managing a loop that triggers every device simultaneously
    '''

    __instance = None

    def __new__(cls, chassis):
        if cls.__instance is None:
            cls.__instance = super(TriggerLoop, cls).__new__(cls)
            cls.__instance.__initialized = False
        return cls.__instance

    def __init__(self, chassis):
        '''
        set up chassis

        the main function connects to hardware, writes a trigger instruction sequence to all hardware,
        then runs triggering until user interrupt
        '''
        # modules chassis and slot numbers
        if self.__initialized: return

        self.__initialized = True
        self.awg_slots = []
        self.dig_slots = []
        self.slot_free = [True]*18

        # Ext trigger module (TODO: not sure if these values might ever change)
        self.chassis = chassis
        slotNumber = 6
        partNumber = ""

        extTrigModule = keysightSD1.SD_AOU()
        status = extTrigModule.openWithSlot(partNumber, self.chassis, slotNumber)
        if (status < 0):
            raise Error("Invalid external trigger module. Name, Chassis or Slot numbers might be invalid!")

        # Create HVI instance
        moduleResourceName = "KtHvi"
        self.hvi = pyhvi.KtHvi(moduleResourceName)

        # Add chassis
        self.hvi.platform.chassis.add_auto_detect()

        # initialize lists for clarity
        self.awgs = []
        self.digs = []
        # ensure that when program quits, the hardware resources will be released
        atexit.register(self.close)

    def set_slots(self, awg_slots, dig_slots, slot_free):
        ''' reset hw interface with new slots 
        (everything must be redone, unless we make other code more sophisticated.
        just trying to get it working for now)

        returns log string and status for awg and digitizer as tuples
        '''
        close_log = self.close()

        self.awg_slots = awg_slots
        self.dig_slots = dig_slots
        self.slot_free = slot_free

        awg_info, dig_info = self.init_hw()
        return close_log, awg_info, dig_info

    def init_hw(self):
        ''' initialize hardware interfaces. should never be called
        except on initialization or by the reset function, else competing
        for hardware resources

        returns log string and status for awg and digitizer as tuples
        '''
        awgModules, awg_log, awg_status = self.open_modules(self.awg_slots, 'awg')
        digModules, dig_log, dig_status = self.open_modules(self.dig_slots, 'dig')

        if self.__initialized == False:
            self.hvi = pyhvi.KtHvi("KtHvi")
            self.hvi.platform.chassis.add_auto_detect()
        index = 0
        for awgModule in awgModules:
            awg = AWG(self.hvi, awgModule, index)
            self.awgs.append(awg)
            index += 1
        for digModule in digModules:
            dig = DIG(self.hvi, digModule, index)
            self.digs.append(dig)
            index += 1
        return (awg_log, awg_status), (dig_log, dig_status)

    def open_modules(self, slots, type):
        ''' 
        slots = list of slot numbers of device
        type = string 'awg' to open awg modules, 'dig' to
        open digitizer modules
        open_modules creates and returns a list keysightSD1 module objects
        '''
        log_string = ""
        log_status = 20
        options = "channelNumbering=keysight"
        model = ""
        modules = []
        if slots:
            for slot in slots:
                if type == 'awg':
                    module = keysightSD1.SD_AOU()
                elif type == 'dig':
                    module = keysightSD1.SD_AIN()
                else:
                    raise Error('Only AWGs and digitizers are supported')

                # check that we haven't already assigned module to this slot
                if self.slot_free[slot-1] == True:
                    id_num = module.openWithOptions(model, self.chassis, slot, options)
                    if id_num < 0:
                        raise Error("Error opening module in chassis {}, slot {}, opened with ID: {}".format(self.chassis, slot, id_num))
                    if not module.hvi:
                        raise Error("Module in chassis {} and slot {} does not support HVI2.0... exiting".format(awgModule.getChassis(), awgModule.getSlot()))
                    modules.append(module)
                    self.slot_free[slot-1] = False
                    log_string +='slots status: '+str(self.slot_free)+'\n'
                else:
                    log_string +='slot taken, check behavior'+'\n'
                    log_status = 30
        return modules, log_string, log_status

    def close_modules(self):
        ''' close awgs and digitizers but not chassis
        '''
        log_string = ''
        for awg in self.awgs:
            is_open = awg.close()
            log_string += 'awg open status: '+is_open+'\n'
        for dig in self.digs:
            dig.close()
        # prevent weird behavior if this gets called twice in a row
        self.awgs = []
        self.digs = []
        self.slot_free = [True]*18
        return log_string

    def write_instructions(self, wait, dig_wait=0):
        ''' creates instruction sequences for all devices
        wait = global AWG wait time
        dig_wait = (optional) digitizer wait time

        both need to be multiples of 10 
        '''

        NANOSECONDS_PER_CYCLE = 10 
        # Check experiment parameters values
        timeElapsedJumping = 170
        if wait % 10 != 0: # Validate that we received values that are multiples of 10 ns.
            raise Error('Invalid wait time. Value must be a multiple of 10 ns.') 
        if wait < timeElapsedJumping:
            raise Error('Invalid wait time. The delay must be at least '+str(timeElapsedJumping+900)+' ns')
        if wait < 2000:
            raise Error("warning: you might get unexpected behavior with wait times less than 2 us")

        if dig_wait % 10 != 0:
            raise Error('Invalid digitizer wait time. Value must be a multiple of 10 ns')

        wait = wait - timeElapsedJumping - 900
        wait = int(wait / NANOSECONDS_PER_CYCLE)

        dig_wait = int(dig_wait / NANOSECONDS_PER_CYCLE)
        # Add registers
        self.awgs[0].add_register("wait", wait)
        self.awgs[0].add_register("true_reg", 1)
        self.awgs[0].add_register("loop", 0)

        if dig_wait > 0:
            self.digs[0].add_register("dig_wait", wait)
            self.digs[0].assign_register_value(self.hvi, "write dig wait", "dig_wait", dig_wait)

        # Write instruction sequences

        # Assign to register "wait" its initial value
        self.awgs[0].assign_register_value(self.hvi, "write wait", "wait", wait)

        # Add global synchronized junction
        junctionName = "SJunc1"
        junctionTime_ns = 100 #not sure how long this should be
        self.hvi.programming.add_junction(junctionName, junctionTime_ns)

        # Add triggers
        awg0 = True
        for awg in self.awgs:
            awg.trigger_all(self.hvi)
            if awg0:
                # adds Wait length contained in Wait register
                self.awgs[0].add_wait("wait for", "wait")
                self.awgs[0].increment_register_value(self.hvi, "loop inc", "loop")
                awg0 = False

        dig0 = True
        for dig in self.digs:
            dig.trigger_all(self.hvi)
            if dig_wait > 0 and dig0:
                self.digs[0].add_wait("dig wait for", "dig_wait")
                dig0 = False

        # === Conditional jumps =====
        master_seq_name = self.awgs[0].return_sequence_name()  
        timeElapsedBeforeJump = 200 
        #Internal Loop - Conditional Jump
        jump_destination = "SJunc1"
        sync_conditional = self.hvi.programming.add_conditional_jump("SCond1", timeElapsedBeforeJump, timeElapsedJumping, jump_destination, master_seq_name)
        # Set up the condition:
        condition = sync_conditional.conditions.add_register_condition("")
        comparison_operator = pyhvi.ComparisonMode.SMALLER
        condition.register_evaluations.add("true", self.awgs[0].return_register("true_reg"), 10, comparison_operator)

        # === END =====
        # Add global synchronized end to close HVI execution (close all sequences - using hvi-programming interface)
        self.hvi.programming.add_end("EndOfSequence", 100)

    def prepare_hw(self):
        # Assign PXI lines as triggers to HVI object to be used for HVI-managed sync, data sharing, etc.
        triggerResources = [pyhvi.TriggerResourceId.PXI_TRIGGER3, pyhvi.TriggerResourceId.PXI_TRIGGER4, pyhvi.TriggerResourceId.PXI_TRIGGER7]
        self.hvi.platform.sync_resources = triggerResources

        # Assign clock frequences that are outside the set of the clock frequencies of each hvi engine
        nonHVIclocks = [10e6]
        self.hvi.synchronization.non_hvi_core_clocks = nonHVIclocks

        self.hvi.compile()
        self.hvi.load_to_hw()

    def run(self):
        # Start hardware actions

        # Start DAQs to be ready to receive acquisition triggers
        for dig in self.digs:
            dig.start_all()

        # Run HVI sequences
        exeTime = timedelta(seconds=0)
        self.hvi.run(exeTime)

    def close(self):
        '''
        release all hardware resources
        '''
        self.hvi.release_hw()
        mod_closed = self.close_modules()
        self.__initialized = False
        return mod_closed