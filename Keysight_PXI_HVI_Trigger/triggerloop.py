import sys
sys.path.append(r'C:\Program Files (x86)\Keysight\SD1\Libraries\Python')
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

class TriggerLoop:
    '''
    class for managing a loop that triggers every device simultaneously
    '''

    def __init__(self, awg_slots, chassis, dig_slots=None):
        '''
        set up chassis and initialize awg and digitizer modules

        wait is multiple of 10ns that sets wait time
        dig_wait is extra delay for only digitizers
        awg_slots list of slot numbers corresponding to AWG modules used in program (must have at least one)
        dig_slot (optional) list of slot numbers corresponding to DAQ module if used in program

        the main function connects to hardware, writes a trigger instruction sequence to all hardware,
        then runs triggering until user interrupt

        note that both the pyhvi and Module interfaces for devices must persist and be 
        kept track of until you close the loop, but you should only need to interact with DIG and AWG
        class objects once those are created
        '''
        NANOSECONDS_PER_CYCLE = 10  # M3xxxA PXI modules have a cycle period that lasts 10 ns
        ALL_CHANNELS_MASK = 0xF

        # modules chassis and slot numbers
        options = "channelNumbering=keysight"
        model = ""

        # Check experiment parameters values
        timeElapsedJumping = 170
        if wait % 10 != 0: # Validate that we received values that are multiples of 10 ns.
            raise Error('Invalid acquisition_delay. Value must be a multiple of 10 ns.') 
        if wait < timeElapsedJumping:
            raise Error('Invalid wait time. The delay must be at least '+str(timeElapsedJumping+900)+' ns')
        if wait < 2000:
            raise Error("warning: you might get unexpected behavior with wait times less than 2 us")

        wait = wait - timeElapsedJumping - 900
        wait = int(wait / NANOSECONDS_PER_CYCLE)

        # Ext trigger module (TODO: not sure if these values might ever change)
        chassisNumber = chassis
        slotNumber = 5
        partNumber = ""

        extTrigModule = keysightSD1.SD_AOU()
        status = extTrigModule.openWithSlot(partNumber, chassisNumber, slotNumber)
        if (status < 0):
            print("Invalid Module Name, Chassis or Slot numbers might be invalid! Press enter to quit")
            input()
            sys.exit()

        # create awg and digitizer SD1 interfaces
        self.awgModules = open_modules(awg_slots, 'awg')
        self.digModules = open_modules(dig_slots, 'dig')

        # Create HVI instance
        moduleResourceName = "KtHvi"
        self.hvi = pyhvi.KtHvi(moduleResourceName)

        # Add chassis
        self.hvi.platform.chassis.add_auto_detect()

        # create awg and digitizer pyhvi interfaces
        index = 0
        self.awgs = []
        self.digs = []
        for awgModule in self.awgModules:
            awg = AWG(hvi, awgModule, index)
            self.awgs.append(awg)
            index += 1
        for digModule in self.digModules:
            dig = DIG(hvi, digModule, index)
            self.digs.append(dig)
            index += 1

    def open_modules(self, slots, type):
        modules = []
        if slots:
            for slot in slots:
                print(slot)
                print(type)
                if type == 'awg':
                    module = keysightSD1.SD_AOU()
                elif type == 'dig':
                    module = keysightSD1.SD_AIN()
                else:
                    raise Error('Only AWGs and digitizers are supported')
                id_num = module.openWithOptions(model, chassis, slot, options)
                if id_num < 0:
                    raise Error("Error opening module in chassis {}, slot {}, opened with ID: {}".format(chassis, slot, id_num))
                if not module.hvi:
                    raise Error("Module in chassis {} and slot {} does not support HVI2.0... exiting".format(awgModule.getChassis(), awgModule.getSlot()))
                modules.append(module)
        return modules

    def write_instructions(self, wait, dig_wait=0):
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


    def main_loop(self):

        # Start hardware actions

        # Assign PXI lines as triggers to HVI object to be used for HVI-managed sync, data sharing, etc.
        triggerResources = [pyhvi.TriggerResourceId.PXI_TRIGGER3, pyhvi.TriggerResourceId.PXI_TRIGGER4, pyhvi.TriggerResourceId.PXI_TRIGGER7]
        self.hvi.platform.sync_resources = triggerResources

        # Assign clock frequences that are outside the set of the clock frequencies of each hvi engine
        nonHVIclocks = [10e6]
        self.hvi.synchronization.non_hvi_core_clocks = nonHVIclocks

        self.hvi.compile()
        self.hvi.load_to_hw()

        # Start DAQs to be ready to receive acquisition triggers
        for dig in self.digs:
            dig.start_all()

        # Run HVI sequences
        exeTime = timedelta(seconds=0)
        self.hvi.run(exeTime)

        '''
        atexit(digModule.close)
        atexit(digModule.DAQstopMultiple, mask=ALL_CHANNELS_MASK)
        for awgModule in awgModules:
            atexit(awgModule.close)
            atext(awgModule.AWGstopMultiple(mask=ALL_CHANNELS_MASK))
        atexit(hvi.release_hw)'''

        print("Press enter to stop HVI")
        input()

        print("loops:")
        print(self.awgs[0].read_register("loop"))

        print("Exiting...")
        hvi.release_hw()

        # Stop AWG and digitizer
        for awgModule in self.awgModules:
            awgModule.AWGstopMultiple(ALL_CHANNELS_MASK)
            awgModule.close()

        for digModule in self.digModules:
            digModule.DAQstopMultiple(ALL_CHANNELS_MASK)
            digModule.close()