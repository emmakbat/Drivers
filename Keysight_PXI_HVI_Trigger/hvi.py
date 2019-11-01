import sys
sys.path.append('C:\Program Files (x86)\Keysight\SD1\Libraries\Python')
import keysightSD1
import pyhvi
import numpy as np
from datetime import timedelta
import atexit
from awg import AWG
from dig import DIG

"""
test of HVI2 for triggering devices
set slotAWG, slotDIG to correct numbers for AWG setup
in current beta version of HVI, these need to be in the same segment
(i.e., not connected across a bus) or compilation will fail
"""

NANOSECONDS_PER_CYCLE = 10  # M3xxxA PXI modules have a cycle period that lasts 10 ns
ALL_CHANNELS_MASK = 0xF

# modules chassis and slot numbers
chassis = 1
options = "channelNumbering=keysight"
model = ""

# Ext trigger module
chassisNumber = 1
slotNumber = 5
extTrigModule = keysightSD1.SD_AOU()
partNumber = ""

def open_modules(slots, type):
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
                raise InvalidParameterException('Only AWGs and digitizers are supported')
            id_num = module.openWithOptions(model, chassis, slot, options)
            if id_num < 0:
                print("Error opening module in chassis {}, slot {}, opened with ID: {}".format(chassis, slot, id_num))
                print("Press any key to exit...")
                input()
                sys.exit()
            if not module.hvi:
                print("Module in chassis {} and slot {} does not support HVI2.0... exiting".format(awgModule.getChassis(), awgModule.getSlot()))
                sys.exit()
            modules.append(module)
    return modules



def main(wait, dig_wait, awg_slots, dig_slots=None):
    '''
    wait is multiple of 10ns that sets wait time
    dig_wait is extra delay for only digitizers
    awg_slots list of slot numbers corresponding to AWG modules used in program (must have at least one)
    dig_slot (optional) list of slot numbers corresponding to DAQ module if used in program

    the main function connects to hardware, writes a trigger instruction sequence to all hardware,
    then runs triggering until user interrupt
    '''

    # Check experiment parameters values
    timeElapsedJumping = 170
    if wait % 10 != 0: # Validate that we received values that are multiples of 10 ns.
        raise InvalidParameterException('Invalid acquisition_delay. Value must be a multiple of 10 ns.') 
    if wait < timeElapsedJumping:
        raise InvalidParameterException('Invalid wait time. The delay must be at least '+str(timeElapsedJumping+900)+' ns')
    if wait < 2000:
        print("warning: you might get unexpected behavior with wait times less than 2 us")

    wait = wait - timeElapsedJumping - 900
    wait = int(wait / NANOSECONDS_PER_CYCLE)

    status = extTrigModule.openWithSlot(partNumber, chassisNumber, slotNumber)
    if (status < 0):
        print("Invalid Module Name, Chassis or Slot numbers might be invalid! Press enter to quit")
        input()
        sys.exit()

    # create awg and digitizer SD1 interfaces
    awgModules = open_modules(awg_slots, 'awg')
    digModules = open_modules(dig_slots, 'dig')

    # Create HVI instance
    moduleResourceName = "KtHvi"
    hvi = pyhvi.KtHvi(moduleResourceName)

    # Add chassis
    hvi.platform.chassis.add_auto_detect()

    # create awg and digitizer pyhvi interfaces
    index = 0
    awgs = []
    digs = []
    for awgModule in awgModules:
        awg = AWG(hvi, awgModule, index)
        awgs.append(awg)
        index += 1
    for digModule in digModules:
        dig = DIG(hvi, digModule, index)
        digs.append(dig)
        index += 1

    # Add registers
    awgs[0].add_register("wait", wait)
    awgs[0].add_register("true_reg", 1)
    awgs[0].add_register("loop", 0)

    # Write instruction sequences

    # Assign to register "wait" its initial value
    awgs[0].assign_register_value(hvi, "write wait", "wait", wait)

    # Add global synchronized junction
    junctionName = "SJunc1"
    junctionTime_ns = 100 #not sure how long this should be
    hvi.programming.add_junction(junctionName, junctionTime_ns)

    # Add triggers
    awg0 = True
    for awg in awgs:
        awg.trigger_all(hvi)
        if awg0:
            # adds Wait length contained in Wait register
            awgs[0].add_wait("wait for", "wait")
            awgs[0].increment_register_value(hvi, "loop inc", "loop")
            awg0 = False

    for dig in digs:
        dig.trigger_all(hvi)

    # === Conditional jumps =====
    master_seq_name = awgs[0].return_sequence_name()  
    timeElapsedBeforeJump = 200 
    #Internal Loop - Conditional Jump
    jump_destination = "SJunc1"
    sync_conditional = hvi.programming.add_conditional_jump("SCond1", timeElapsedBeforeJump, timeElapsedJumping, jump_destination, master_seq_name)
    # Set up the condition:
    condition = sync_conditional.conditions.add_register_condition("")
    comparison_operator = pyhvi.ComparisonMode.SMALLER
    condition.register_evaluations.add("true", awgs[0].return_register("true_reg"), 10, comparison_operator)

    # === END =====
    # Add global synchronized end to close HVI execution (close all sequences - using hvi-programming interface)
    hvi.programming.add_end("EndOfSequence", 100)

    # Start hardware actions
    print('HVI started')

    # Assign PXI lines as triggers to HVI object to be used for HVI-managed sync, data sharing, etc.
    triggerResources = [pyhvi.TriggerResourceId.PXI_TRIGGER3, pyhvi.TriggerResourceId.PXI_TRIGGER4, pyhvi.TriggerResourceId.PXI_TRIGGER7]
    hvi.platform.sync_resources = triggerResources

    # Assign clock frequences that are outside the set of the clock frequencies of each hvi engine
    nonHVIclocks = [10e6]
    hvi.synchronization.non_hvi_core_clocks = nonHVIclocks

    hvi.compile()
    # Load the HVI to HW: load sequences, config triggers/events/..., lock resources, etc.
    hvi.load_to_hw()

    # Start DAQs to be ready to receive acquisition triggers
    for dig in digs:
        dig.start_all()
    # Run HVI sequences
    exeTime = timedelta(seconds=0)
    hvi.run(exeTime)

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
    print(awgs[0].read_register("loop"))

    print("Exiting...")
    hvi.release_hw()

    # Stop AWG and digitizer
    for awgModule in awgModules:
        awgModule.AWGstopMultiple(ALL_CHANNELS_MASK)
        awgModule.close()

    for digModule in digModules:
        digModule.DAQstopMultiple(ALL_CHANNELS_MASK)
        digModule.close()

def InvalidParameterException(string):
        print(string)
        print("Exiting...")
        exit(-1)

if __name__ == '__main__':
        main(3000, 0, [3, 4], [6])